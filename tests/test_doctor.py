"""
Tests for doctor.py (the environment check) and the "works offline" promise.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import ast
import contextlib
import glob
import io
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
import zipfile

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))

import doctor  # noqa: E402
from test_pbrs import make_pbix  # noqa: E402

NETWORK_MODULES = {
    "socket", "ssl", "http", "urllib", "urllib3", "ftplib", "smtplib", "poplib",
    "imaplib", "telnetlib", "socketserver", "xmlrpc", "asyncio", "requests",
    "httpx", "aiohttp", "paramiko", "webbrowser",
}
OPTIONAL_THIRD_PARTY = {"pbixray"}


def statuses(checks):
    return {c.name: c.status for c in checks}


class MachineChecksTest(unittest.TestCase):

    def test_a_working_checkout_has_nothing_to_fix(self):
        with contextlib.redirect_stdout(io.StringIO()):
            checks = doctor.run_checks()
        failing = [(c.name, c.detail) for c in checks if c.status == doctor.FAIL]
        self.assertEqual(failing, [])

    def test_self_test_builds_and_reads_a_report(self):
        with contextlib.redirect_stdout(io.StringIO()):
            check = doctor.check_self_test()
        self.assertEqual(check.status, doctor.OK, check.detail)

    def test_self_test_does_not_leak_its_config_module(self):
        before = sys.modules.get("visuals_config")
        with contextlib.redirect_stdout(io.StringIO()):
            doctor.check_self_test()
        self.assertIs(sys.modules.get("visuals_config"), before)

    def test_old_python_is_reported_as_a_failure(self):
        with unittest.mock.patch.object(sys, "version_info", (3, 6, 0, "final", 0)):
            self.assertEqual(doctor.check_python().status, doctor.FAIL)

    def test_missing_desktop_is_a_note_not_a_failure(self):
        with unittest.mock.patch("desktop.find_desktop", return_value=("", "")):
            check = doctor.check_desktop()
        self.assertEqual(check.status, doctor.WARN)
        self.assertIn("PBI_DESKTOP_PATH", check.fix)

    def test_report_server_desktop_found_is_ok(self):
        with unittest.mock.patch("desktop.find_desktop", return_value=("C:/x/PBIDesktop.exe", "RS")):
            self.assertEqual(doctor.check_desktop().status, doctor.OK)


class ReportFileChecksTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_file(self):
        checks = doctor.check_report_file(os.path.join(self.tmp, "nope.pbix"))
        self.assertEqual(checks[0].status, doctor.FAIL)

    def test_not_a_zip(self):
        path = os.path.join(self.tmp, "bad.pbix")
        with open(path, "w") as f:
            f.write("not a zip")
        self.assertIn(doctor.FAIL, statuses(doctor.check_report_file(path)).values())

    def test_zip_without_layout_is_not_a_classic_pbix(self):
        path = os.path.join(self.tmp, "pbip.pbix")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("definition/report.json", "{}")
        result = statuses(doctor.check_report_file(path))
        self.assertEqual(result["Report contents"], doctor.FAIL)

    def test_valid_report(self):
        path = os.path.join(self.tmp, "ok.pbix")
        make_pbix(path)
        result = doctor.check_report_file(path)
        self.assertNotIn(doctor.FAIL, [c.status for c in result])
        self.assertEqual(statuses(result)["Report location"], doctor.OK)
        self.assertIn("1 page", next(c.detail for c in result if c.name == "Pages"))

    def test_synced_folder_is_warned_about(self):
        folder = os.path.join(self.tmp, "OneDrive - Some Company")
        os.makedirs(folder)
        path = os.path.join(folder, "r.pbix")
        make_pbix(path)
        self.assertEqual(statuses(doctor.check_report_file(path))["Report location"],
                         doctor.WARN)

    def test_saved_in_desktop_note_only_when_bindings_missing(self):
        path = os.path.join(self.tmp, "r.pbix")
        make_pbix(path)  # has SecurityBindings
        self.assertNotIn("Saved in Desktop?", statuses(doctor.check_report_file(path)))
        stripped = os.path.join(self.tmp, "stripped.pbix")
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(stripped, "w") as dst:
            for item in src.infolist():
                if item.filename != "SecurityBindings":
                    dst.writestr(item, src.read(item.filename))
        self.assertEqual(statuses(doctor.check_report_file(stripped))["Saved in Desktop?"],
                         doctor.WARN)


class ExitCodeTest(unittest.TestCase):

    def _run(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = doctor.main(argv)
        return code, out.getvalue()

    def test_zero_when_nothing_to_fix(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("vizbuilder environment check", out)

    def test_one_when_the_report_file_is_missing(self):
        code, out = self._run(["definitely-not-here.pbix"])
        self.assertEqual(code, 1)
        self.assertIn("[XX]", out)


class OfflineGuaranteeTest(unittest.TestCase):
    """The README, doctor and AGENTS.md all promise no network access."""

    def _scripts(self):
        return sorted(glob.glob(os.path.join(REPO_DIR, "*.py")))

    def test_no_program_file_imports_a_network_library(self):
        offenders = []
        for path in self._scripts():
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    if module.split(".")[0] in NETWORK_MODULES:
                        offenders.append(f"{os.path.basename(path)}: {module}")
        self.assertEqual(offenders, [])

    def test_only_pbixray_is_third_party_and_it_is_optional(self):
        local = {os.path.basename(p)[:-3] for p in self._scripts()}
        stdlib = set(getattr(sys, "stdlib_module_names", ()))
        for path in self._scripts():
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            guarded = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Try) and any(
                        getattr(h.type, "id", "") == "ImportError" for h in node.handlers):
                    guarded.update(id(child) for stmt in node.body for child in ast.walk(stmt))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    module = node.module.split(".")[0]
                elif isinstance(node, ast.Import):
                    module = node.names[0].name.split(".")[0]
                else:
                    continue
                if module in OPTIONAL_THIRD_PARTY:
                    self.assertIn(id(node), guarded,
                                  f"{os.path.basename(path)} imports {module} without try/except ImportError")
                elif stdlib and module not in stdlib and module not in local:
                    self.fail(f"{os.path.basename(path)} imports third-party module {module}")


if __name__ == "__main__":
    unittest.main()
