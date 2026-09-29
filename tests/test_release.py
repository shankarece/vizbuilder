"""
Tests for make_release.py and build.py's --config / --version.

The strongest check unpacks the finished zip somewhere else and runs that
copy's own test suite, so a release can't ship missing a file it needs.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from unittest import mock

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))

import build as build_module  # noqa: E402
import make_release  # noqa: E402
from test_pbrs import make_pbix  # noqa: E402

# The extracted copy runs this same file; stop it building a release again.
IN_RELEASE_SELFTEST = os.environ.get("VIZBUILDER_RELEASE_SELFTEST") == "1"


class CollectFilesTest(unittest.TestCase):

    def setUp(self):
        self.files = make_release.collect_files()

    def test_includes_what_a_colleague_needs(self):
        for needed in ("build.py", "build.bat", "lint.py", "analyze.py",
                       "visuals_config.py", "install_skill.py", "desktop.py",
                       "README.md", "AGENTS.md", "CHANGELOG.md", "VERSION",
                       "skills/vizbuilder-modeling/SKILL.md",
                       "tests/test_skills.py"):
            with self.subTest(file=needed):
                self.assertIn(needed, self.files)

    def test_every_skill_folder_is_included(self):
        skills_dir = os.path.join(REPO_DIR, "skills")
        for name in os.listdir(skills_dir):
            with self.subTest(skill=name):
                self.assertIn(f"skills/{name}/SKILL.md", self.files)

    def test_leaves_out_working_files(self):
        for path in self.files:
            with self.subTest(path=path):
                self.assertNotIn("__pycache__", path)
                self.assertFalse(path.endswith((".pyc", ".pbix", ".pbit")))
                self.assertFalse(path.startswith(("dist/", ".git")))
                self.assertNotIn(path, make_release.EXCLUDED_FILES)
        self.assertNotIn("REVIEW_SUMMARY.md", self.files)


class BuildReleaseTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build(self):
        return make_release.build_release(self.tmp, run_tests=False)

    def test_zip_has_one_versioned_root_folder(self):
        zip_path = self._build()
        version = make_release.read_version()
        self.assertEqual(os.path.basename(zip_path), f"vizbuilder-{version}.zip")
        with zipfile.ZipFile(zip_path) as z:
            roots = {name.split("/")[0] for name in z.namelist()}
            self.assertEqual(roots, {f"vizbuilder-{version}"})
            self.assertIsNone(z.testzip())

    def test_sha256_file_matches_zip(self):
        zip_path = self._build()
        with open(zip_path + ".sha256", encoding="utf-8") as f:
            recorded, name = f.read().split()
        with open(zip_path, "rb") as f:
            self.assertEqual(recorded, hashlib.sha256(f.read()).hexdigest())
        self.assertEqual(name, os.path.basename(zip_path))

    def test_failing_tests_block_the_release(self):
        failed = subprocess.CompletedProcess([], 1, "", "boom")
        with mock.patch("make_release.subprocess.run", return_value=failed), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                make_release.build_release(self.tmp, run_tests=True)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_empty_version_rejected(self):
        fake_repo = os.path.join(self.tmp, "repo")
        os.makedirs(fake_repo)
        with open(os.path.join(fake_repo, "VERSION"), "w") as f:
            f.write("\n")
        with self.assertRaises(ValueError):
            make_release.read_version(fake_repo)

    @unittest.skipIf(IN_RELEASE_SELFTEST, "already running inside a release")
    def test_unpacked_release_passes_its_own_tests(self):
        zip_path = self._build()
        extract_dir = os.path.join(self.tmp, "unpacked")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(extract_dir)
        root = os.path.join(extract_dir, os.listdir(extract_dir)[0])

        env = dict(os.environ, VIZBUILDER_RELEASE_SELFTEST="1", PYTHONPATH="")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "tests"],
            cwd=root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])


class ConfigAndVersionTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "in.pbix")
        self.out = os.path.join(self.tmp, "out.pbix")
        make_pbix(self.src)
        self.config = os.path.join(self.tmp, "my_dashboard.py")
        with open(self.config, "w", encoding="utf-8") as f:
            f.write(
                "from layout_builder import add_visual\n"
                "PAGE_NAME = 'From My Config'\n"
                "DASHBOARD_TITLE = 'Mine'\n"
                "def build_visuals():\n"
                "    return [add_visual('card', {'value': 'Sales[Revenue]'},\n"
                "                       vid=1, title='Revenue')]\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, argv):
        with mock.patch.dict(sys.modules), contextlib.redirect_stdout(io.StringIO()) as out:
            build_module.main(argv)
        return out.getvalue()

    def test_config_file_outside_the_tool_folder_is_used(self):
        from layout_builder import read_layout
        self._run([self.src, self.out, "--config", self.config])
        layout = read_layout(self.out)
        self.assertEqual(layout["sections"][0]["displayName"], "From My Config")

    def test_missing_config_is_a_clear_error(self):
        with self.assertRaises(SystemExit):
            self._run([self.src, self.out, "--config", os.path.join(self.tmp, "nope.py")])
        self.assertFalse(os.path.exists(self.out))

    def test_config_flag_without_value_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._run([self.src, self.out, "--config"])

    def test_version_flag_prints_version_file(self):
        output = self._run(["--version"])
        self.assertEqual(output.strip(), f"vizbuilder {make_release.read_version()}")

    def test_banner_shows_version(self):
        output = self._run([self.src, self.out, "--config", self.config])
        self.assertIn(f"v{make_release.read_version()}", output)


if __name__ == "__main__":
    unittest.main()
