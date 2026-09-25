"""
Tests for the bundled Claude Code skills and install_skill.py.

Run from the repo root (standard library only):
    python -m unittest discover tests
    python tests/test_skills.py --triggers     print the trigger table
"""

import os
import re
import shutil
import sys
import tempfile
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

import install_skill  # noqa: E402

SKILLS_DIR = os.path.join(REPO_DIR, "skills")


# ── Frontmatter parsing (no pyyaml) ──────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fm = match.group(1)
    result = {}
    for key in ("name", "tools"):
        m = re.search(rf"^{key}:\s*(.+)$", fm, re.MULTILINE)
        if m:
            result[key] = m.group(1).strip()
    multi = re.search(r"^description:\s*>\s*\n((?:[ \t]+.*\n?)+)", fm, re.MULTILINE)
    single = re.search(r"^description:\s*([^>\s].*)$", fm, re.MULTILINE)
    if multi:
        result["description"] = " ".join(
            line.strip() for line in multi.group(1).splitlines() if line.strip())
    elif single:
        result["description"] = single.group(1).strip()
    return result


def load_skills() -> dict:
    skills = {}
    for name, path in install_skill.get_bundled_skills().items():
        with open(path, encoding="utf-8") as f:
            skills[name] = parse_frontmatter(f.read())
    return skills


# ── Trigger evaluation (keyword overlap, same approach as pbi-cli) ───────────

def _score(prompt: str, description: str) -> int:
    prompt_words = set(re.findall(r"[a-z]+", prompt.lower()))
    desc_words = set(re.findall(r"[a-z]+", description.lower()))
    score = 0
    for word in prompt_words & desc_words:
        if len(word) >= 5:
            score += 3
        elif len(word) >= 3:
            score += 1
    return score


def best_skill(prompt: str, skills: dict) -> str:
    scores = {n: _score(prompt, s.get("description", "")) for n, s in skills.items()}
    return max(scores, key=lambda n: scores[n])


TRIGGER_CASES = [
    # vizbuilder-visuals
    ("Add a bar chart showing sales by region", "vizbuilder-visuals"),
    ("Bind Sales[Revenue] to the value of the KPI visual", "vizbuilder-visuals"),
    ("What visual types are supported? I need a scatter chart", "vizbuilder-visuals"),
    ("Add a combo chart with revenue columns and a profit line", "vizbuilder-visuals"),
    # vizbuilder-pages
    ("Add a new tab called Regional Detail", "vizbuilder-pages"),
    ("Convert my dashboard to multiple pages with a page title on each", "vizbuilder-pages"),
    ("Lay out a banking dashboard with a KPI row and executive summary page", "vizbuilder-pages"),
    # vizbuilder-layout
    ("Fix the alignment and overlapping visuals in my dashboard", "vizbuilder-layout"),
    ("Snap everything to the grid and even out the spacing", "vizbuilder-layout"),
    # vizbuilder-analysis
    ("Find unused columns and orphaned measures in this pbix", "vizbuilder-analysis"),
    ("Show the data lineage: which visuals use which fields", "vizbuilder-analysis"),
    ("Run a consistency check on naming conventions", "vizbuilder-analysis"),
    # vizbuilder-docs
    ("Generate a data dictionary and measure catalog", "vizbuilder-docs"),
    ("Create an HTML audit report with a health score for stakeholders", "vizbuilder-docs"),
    # vizbuilder-deployment
    ("Validate this file for PBRS compatibility before I deploy", "vizbuilder-deployment"),
    ("Publish to report server: what is the release checklist", "vizbuilder-deployment"),
    # vizbuilder-diagnostics
    ("I get MashupValidationError when opening the file", "vizbuilder-diagnostics"),
    ("Visual says Can't display visual after the build failed", "vizbuilder-diagnostics"),
    # vizbuilder-report
    ("How does vizbuilder work end to end, from pbix file to build.bat", "vizbuilder-report"),
    ("Explain SecurityBindings and the legacy report layout", "vizbuilder-report"),
    ("Open the built report in RS Desktop instead of regular Power BI Desktop",
     "vizbuilder-report"),
]

EXPECTED_SKILLS = {
    "vizbuilder-report", "vizbuilder-visuals", "vizbuilder-pages",
    "vizbuilder-layout", "vizbuilder-analysis", "vizbuilder-docs",
    "vizbuilder-deployment", "vizbuilder-diagnostics",
}


class SkillFilesTest(unittest.TestCase):

    def setUp(self):
        self.skills = load_skills()

    def test_expected_skills_bundled(self):
        self.assertEqual(set(self.skills), EXPECTED_SKILLS)

    def test_frontmatter_complete(self):
        for name, fm in self.skills.items():
            with self.subTest(skill=name):
                self.assertTrue(fm.get("name"), "missing name")
                self.assertTrue(fm.get("description"), "missing description")
                self.assertEqual(fm.get("tools"), "vizbuilder")
                self.assertIn("invoke this skill", fm["description"].lower())
                self.assertLessEqual(len(fm["description"]), 1024)

    def test_referenced_scripts_exist(self):
        for name, path in install_skill.get_bundled_skills().items():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for script in set(re.findall(r"\b([a-z_]+\.(?:py|bat))\b", text)):
                with self.subTest(skill=name, script=script):
                    self.assertTrue(os.path.isfile(os.path.join(REPO_DIR, script)),
                                    f"{script} referenced but not in repo")

    def test_referenced_skills_exist(self):
        for name, path in install_skill.get_bundled_skills().items():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for ref in set(re.findall(r"\bvizbuilder-[a-z]+\b", text)):
                with self.subTest(skill=name, ref=ref):
                    self.assertIn(ref, EXPECTED_SKILLS)

    def test_visual_aliases_documented(self):
        from visual_types import VISUAL_TYPE_ALIASES
        with open(os.path.join(SKILLS_DIR, "vizbuilder-visuals", "SKILL.md"),
                  encoding="utf-8") as f:
            text = f.read()
        for alias in VISUAL_TYPE_ALIASES:
            if alias.endswith("_chart"):
                continue  # long-form aliases are implied by the short ones
            with self.subTest(alias=alias):
                self.assertIn(f"`{alias}`", text)

    def test_trigger_cases(self):
        for prompt, expected in TRIGGER_CASES:
            with self.subTest(prompt=prompt):
                self.assertEqual(best_skill(prompt, self.skills), expected)


class InstallerTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = (install_skill.CLAUDE_DIR, install_skill.SKILLS_TARGET_DIR,
                       install_skill.CLAUDE_MD)
        install_skill.CLAUDE_DIR = self.tmp
        install_skill.SKILLS_TARGET_DIR = os.path.join(self.tmp, "skills")
        install_skill.CLAUDE_MD = os.path.join(self.tmp, "CLAUDE.md")
        self._stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self._stdout
        (install_skill.CLAUDE_DIR, install_skill.SKILLS_TARGET_DIR,
         install_skill.CLAUDE_MD) = self._saved
        shutil.rmtree(self.tmp)

    def _claude_md(self) -> str:
        with open(install_skill.CLAUDE_MD, encoding="utf-8") as f:
            return f.read()

    def test_install_all_and_uninstall(self):
        self.assertEqual(install_skill.main([]), 0)
        for name in EXPECTED_SKILLS:
            self.assertTrue(install_skill.is_installed(name), name)
        self.assertEqual(self._claude_md().count(install_skill.MARKER_START), 1)

        install_skill.main(["install", "--force"])  # idempotent
        self.assertEqual(self._claude_md().count(install_skill.MARKER_START), 1)

        install_skill.main(["uninstall"])
        for name in EXPECTED_SKILLS:
            self.assertFalse(install_skill.is_installed(name), name)
        self.assertNotIn(install_skill.MARKER_START, self._claude_md())

    def test_install_single_skill(self):
        install_skill.main(["install", "--skill", "vizbuilder-layout"])
        self.assertTrue(install_skill.is_installed("vizbuilder-layout"))
        self.assertFalse(install_skill.is_installed("vizbuilder-visuals"))

    def test_unknown_skill_rejected(self):
        self.assertEqual(install_skill.main(["install", "--skill", "nope"]), 1)

    def test_migrates_legacy_install_and_keeps_user_content(self):
        legacy = os.path.join(install_skill.SKILLS_TARGET_DIR, "vizbuilder")
        os.makedirs(legacy)
        with open(os.path.join(legacy, "SKILL.md"), "w") as f:
            f.write("old")
        with open(install_skill.CLAUDE_MD, "w", encoding="utf-8") as f:
            f.write("# My notes\n" + install_skill.LEGACY_CLAUDE_MD_ENTRY)

        install_skill.main(["install"])
        self.assertFalse(os.path.isdir(legacy))
        content = self._claude_md()
        self.assertIn("# My notes", content)
        self.assertNotIn("add visuals to PBRS .pbix files", content)
        self.assertIn(install_skill.MARKER_START, content)

        install_skill.main(["uninstall"])
        self.assertEqual(self._claude_md(), "# My notes\n")


def print_trigger_table() -> None:
    skills = load_skills()
    passed = 0
    print(f"Testing {len(TRIGGER_CASES)} prompts against {len(skills)} skills\n")
    for i, (prompt, expected) in enumerate(TRIGGER_CASES, 1):
        got = best_skill(prompt, skills)
        ok = got == expected
        passed += ok
        short = prompt[:45] + "..." if len(prompt) > 45 else prompt
        print(f"{i:<3} {'PASS' if ok else 'FAIL':<5} {expected:<24} {got:<24} {short}")
    print(f"\n{passed}/{len(TRIGGER_CASES)} passed")


if __name__ == "__main__":
    if "--triggers" in sys.argv:
        print_trigger_table()
    else:
        unittest.main()
