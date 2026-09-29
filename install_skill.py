"""
install_skill.py
----------------
Installs the vizbuilder Claude Code skills so Windsurf/Claude Code can
understand natural-language prompts like "add a bar chart showing Sales
by Region to my PBRS report".

Skills are split by task (same layout as pbi-cli): each folder in skills/
holds one SKILL.md and is copied to ~/.claude/skills/<name>/SKILL.md.
A marker-delimited block listing the skills is added to ~/.claude/CLAUDE.md.

Usage:
    python install_skill.py                          install all skills
    python install_skill.py install --skill vizbuilder-visuals
    python install_skill.py install --force          overwrite existing
    python install_skill.py install --with-pbi-cli   also install pbi-cli's model-side skills
    python install_skill.py list                     show install status
    python install_skill.py uninstall                remove all skills
    python install_skill.py uninstall --skill vizbuilder-layout
"""

import argparse
import os
import shutil
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_SRC_DIR = os.path.join(REPO_DIR, "skills")

CLAUDE_DIR = os.path.join(os.path.expanduser("~"), ".claude")
SKILLS_TARGET_DIR = os.path.join(CLAUDE_DIR, "skills")
CLAUDE_MD = os.path.join(CLAUDE_DIR, "CLAUDE.md")

# Single skill installed by earlier versions; replaced by the split skills.
LEGACY_SKILL_NAME = "vizbuilder"
LEGACY_CLAUDE_MD_ENTRY = """
**PBRS Report Visuals (no connection needed):**
- **vizbuilder** -- add visuals to PBRS .pbix files (bar, line, card, combo, etc.)
"""

# pbi-cli (https://github.com/MinaSaad1/pbi-cli) is a separate, Windows-only tool
# that edits the live data model. Only its model-side skills are installed:
# its report-layer skills (report/visuals/pages/themes/filters/custom-visuals)
# write PBIR, which is not the legacy .pbix format Report Server uses.
PBI_CLI_MODEL_SKILLS = (
    "power-bi-modeling",
    "power-bi-dax",
    "power-bi-partitions",
    "power-bi-security",
    "power-bi-deployment",
)
PBI_CLI_INSTALL_HELP = (
    "  pbi-cli not found. Install it (Windows, Python 3.10+), then re-run:\n"
    "    pipx install pbi-cli-tool\n"
    "    python install_skill.py install --with-pbi-cli"
)

MARKER_START = "<!-- vizbuilder:start -->"
MARKER_END = "<!-- vizbuilder:end -->"

CLAUDE_MD_SNIPPET = (
    "\n"
    "<!-- vizbuilder:start -->\n"
    "# PBRS Report Builder (vizbuilder)\n"
    "\n"
    "When working with Power BI Report Server (PBRS) .pbix files, invoke the\n"
    "relevant vizbuilder skill before responding (offline, no connection needed):\n"
    "\n"
    "**Data model (needs a live Desktop connection, e.g. pbi-cli or a Power BI/Fabric MCP):**\n"
    "- **vizbuilder-modeling** -- handoff: build the model live first, then vizbuilder offline\n"
    "\n"
    "**Build:**\n"
    "- **vizbuilder-report** -- end-to-end build workflow, PBIX format, SecurityBindings\n"
    "- **vizbuilder-visuals** -- add visuals, visual types, Table[Column] bindings\n"
    "- **vizbuilder-pages** -- multi-page dashboards, tabs, page titles, layouts\n"
    "- **vizbuilder-layout** -- lint and auto-fix alignment, overlap, sizing\n"
    "\n"
    "**Analyze and ship:**\n"
    "- **vizbuilder-analysis** -- metadata, lineage, orphaned fields, consistency\n"
    "- **vizbuilder-docs** -- data dictionary, measure catalog, HTML audit report\n"
    "- **vizbuilder-deployment** -- PBRS compatibility validation, deploy checklist\n"
    "- **vizbuilder-diagnostics** -- errors and troubleshooting\n"
    "\n"
    "Critical: edit only visuals_config.py, then run build.py / build.bat.\n"
    "For a .pbix, never use pbi-cli's report-layer commands or skills (pbi report,\n"
    "visual, filters, bookmarks, format; power-bi-report/visuals/pages/themes/filters):\n"
    "they write PBIR, not .pbix. pbi-cli is for the data model only.\n"
    "Open the output in Desktop and File -> Save before deploying.\n"
    "<!-- vizbuilder:end -->\n"
)


# ── Skill discovery ──────────────────────────────────────────────────────────

def get_bundled_skills() -> dict:
    """Return {skill-name: path to SKILL.md} for each bundled skill."""
    result = {}
    if not os.path.isdir(SKILLS_SRC_DIR):
        return result
    for name in sorted(os.listdir(SKILLS_SRC_DIR)):
        skill_md = os.path.join(SKILLS_SRC_DIR, name, "SKILL.md")
        if os.path.isfile(skill_md):
            result[name] = skill_md
    return result


def is_installed(name: str) -> bool:
    return os.path.isfile(os.path.join(SKILLS_TARGET_DIR, name, "SKILL.md"))


# ── CLAUDE.md snippet ────────────────────────────────────────────────────────

def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def ensure_claude_md_snippet() -> None:
    """Add the vizbuilder block to CLAUDE.md, replacing the legacy entry."""
    if os.path.exists(CLAUDE_MD):
        existing = _read(CLAUDE_MD)
    else:
        os.makedirs(CLAUDE_DIR, exist_ok=True)
        existing = ""

    cleaned = existing.replace(LEGACY_CLAUDE_MD_ENTRY.strip(), "").rstrip()
    if MARKER_START in cleaned:
        if cleaned != existing.rstrip():
            _write(CLAUDE_MD, cleaned + "\n")
            print(f"  Removed legacy vizbuilder entry from {CLAUDE_MD}")
        return

    _write(CLAUDE_MD, cleaned + CLAUDE_MD_SNIPPET)
    print(f"  Added vizbuilder section to {CLAUDE_MD}")


def remove_claude_md_snippet() -> None:
    """Remove the vizbuilder block from CLAUDE.md if present."""
    if not os.path.exists(CLAUDE_MD):
        return
    content = _read(CLAUDE_MD)
    if MARKER_START not in content or MARKER_END not in content:
        return

    start = content.index(MARKER_START)
    end = content.index(MARKER_END) + len(MARKER_END)
    before = content[:start].rstrip()
    after = content[end:].lstrip("\n")

    cleaned = before + "\n\n" + after if after else before
    cleaned = cleaned.rstrip() + "\n" if cleaned.strip() else ""
    _write(CLAUDE_MD, cleaned)
    print(f"  Removed vizbuilder section from {CLAUDE_MD}")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_list(_args) -> int:
    bundled = get_bundled_skills()
    if not bundled:
        print("  No bundled skills found.")
        return 1
    print("  Available vizbuilder skills:\n")
    for name in bundled:
        status = "installed" if is_installed(name) else "not installed"
        print(f"    {name:<28} [{status}]")
    print(f"\n  Target directory: {SKILLS_TARGET_DIR}")
    return 0


def install_pbi_cli_model_skills(force: bool = False) -> int:
    """Install pbi-cli's model-side skills via its own installer.

    Returns 0 on success (or when pbi-cli is absent, after printing how to
    install it), 1 if any pbi-cli install command fails.
    """
    exe = shutil.which("pbi-cli")
    if not exe:
        print(PBI_CLI_INSTALL_HELP)
        return 0

    failed = 0
    print("\n  Installing pbi-cli model-side skills "
          "(report-layer skills are skipped on purpose):")
    for name in PBI_CLI_MODEL_SKILLS:
        cmd = [exe, "skills", "install", "--skill", name, "--yes"]
        if force:
            cmd.append("--force")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    {name}: ok")
        else:
            failed += 1
            detail = (result.stderr or result.stdout).strip().splitlines()
            print(f"    {name}: FAILED ({detail[-1] if detail else 'no output'})")
    return 1 if failed else 0


def cmd_install(args) -> int:
    bundled = get_bundled_skills()
    if not bundled:
        print("  No bundled skills found.")
        return 1
    if args.skill and args.skill not in bundled:
        print(f"  Unknown skill '{args.skill}'. Available: {', '.join(bundled)}")
        return 1

    to_install = {args.skill: bundled[args.skill]} if args.skill else bundled

    installed = 0
    for name, src in to_install.items():
        dest_dir = os.path.join(SKILLS_TARGET_DIR, name)
        if is_installed(name) and not args.force:
            print(f"  {name}: already installed (use --force to overwrite)")
            continue
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dest_dir, "SKILL.md"))
        installed += 1
        print(f"  {name}: installed")

    # The old single skill overlaps every new one; remove it.
    legacy_dir = os.path.join(SKILLS_TARGET_DIR, LEGACY_SKILL_NAME)
    if os.path.isdir(legacy_dir):
        shutil.rmtree(legacy_dir)
        print(f"  {LEGACY_SKILL_NAME}: removed legacy single skill")

    ensure_claude_md_snippet()

    print(f"\n  {installed} skill(s) installed to {SKILLS_TARGET_DIR}")

    status = 0
    if getattr(args, "with_pbi_cli", False):
        status = install_pbi_cli_model_skills(force=args.force)

    if installed:
        print("  Restart Windsurf/Claude Code to activate the skills.")
        print('  Then say: "add a bar chart showing Sales by Region to my PBRS report"')
    return status


def cmd_uninstall(args) -> int:
    bundled = get_bundled_skills()
    names = [args.skill] if args.skill else list(bundled)

    removed = 0
    for name in names:
        target = os.path.join(SKILLS_TARGET_DIR, name)
        if not os.path.isdir(target):
            print(f"  {name}: not installed")
            continue
        shutil.rmtree(target)
        removed += 1
        print(f"  {name}: removed")

    print(f"\n  {removed} skill(s) removed.")
    if not args.skill:
        remove_claude_md_snippet()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage vizbuilder Claude Code / Windsurf skills.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List available and installed skills")

    p_install = sub.add_parser("install", help="Install skills (default)")
    p_install.add_argument("--skill", help="Install a single skill")
    p_install.add_argument("--force", action="store_true",
                           help="Overwrite existing installations")
    p_install.add_argument("--with-pbi-cli", action="store_true",
                           help="Also install pbi-cli's model-side skills (needs pbi-cli)")

    p_uninstall = sub.add_parser("uninstall", help="Remove installed skills")
    p_uninstall.add_argument("--skill", help="Remove a single skill")

    args = parser.parse_args(argv)
    if args.command is None:
        # Plain `python install_skill.py` keeps working: install everything.
        args = parser.parse_args(["install", "--force"])

    handlers = {"list": cmd_list, "install": cmd_install, "uninstall": cmd_uninstall}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
