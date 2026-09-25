"""
Power BI Report Server (PBRS) Desktop compatibility tests.

Builds a synthetic legacy .pbix (the format PBRS Desktop saves), runs the
real build pipeline on it, and checks the output is something PBRS Desktop
can open: SecurityBindings removed, DataModel/Version untouched, Layout in
UTF-16 LE, and warnings for visual types PBRS releases may lack.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
import zipfile
from unittest import mock

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

import desktop  # noqa: E402
import pbix_analyzer  # noqa: E402
import pbrs_validator  # noqa: E402
from build import build  # noqa: E402
from layout_builder import add_visual, pbrs_visual_warnings, read_layout  # noqa: E402
from visual_types import PBRS_VISUAL_NOTES, SUPPORTED_VISUAL_TYPES  # noqa: E402

DATAMODEL_BYTES = b"\x00XPRESS9-fake-model\xff" * 64
VERSION_BYTES = "1.28".encode("utf-16-le")


def make_pbix(path: str) -> None:
    """Write a minimal legacy PBIX shaped like a PBRS Desktop save."""
    layout = {
        "id": 0,
        "sections": [{
            "id": 0, "name": "ReportSection", "displayName": "Page 1",
            "filters": "[]", "ordinal": 0, "visualContainers": [],
            "config": "{}", "displayOption": 1, "width": 1280, "height": 720,
        }],
        "config": "{\"version\":\"5.43\"}",
        "layoutOptimization": 0,
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Version", VERSION_BYTES)
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("DataModel", DATAMODEL_BYTES, compress_type=zipfile.ZIP_STORED)
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"),
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("Settings", "{}".encode("utf-16-le"))
        z.writestr("Metadata", "{}".encode("utf-16-le"))
        z.writestr("SecurityBindings", b"\x01\x02dpapi-blob")


def fake_config(visuals_fn) -> types.ModuleType:
    mod = types.ModuleType("visuals_config")
    mod.PAGE_NAME = "Overview"
    mod.DASHBOARD_TITLE = "Test Dashboard"
    mod.build_visuals = visuals_fn
    return mod


class BuildForPBRSTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "in.pbix")
        self.out = os.path.join(self.tmp, "out.pbix")
        make_pbix(self.src)

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def _build(self, visuals_fn) -> str:
        buf = io.StringIO()
        with mock.patch.dict(sys.modules, {"visuals_config": fake_config(visuals_fn)}), \
             contextlib.redirect_stdout(buf):
            build(self.src, self.out)
        return buf.getvalue()

    def test_output_is_openable_by_pbrs_desktop(self):
        self._build(lambda: [
            add_visual("bar", {"category": "Geo[Region]", "value": "Sales[Revenue]"},
                       x=20, y=60, vid=1, title="Revenue by Region"),
            add_visual("card", {"value": "Sales[Revenue]"},
                       x=660, y=60, vid=2, title="Total Revenue"),
        ])
        with zipfile.ZipFile(self.src) as src, zipfile.ZipFile(self.out) as out:
            names = out.namelist()
            self.assertNotIn("SecurityBindings", names)
            self.assertEqual(set(names), set(src.namelist()) - {"SecurityBindings"})
            # Everything except the layout is carried over byte-for-byte
            for name in names:
                if name != "Report/Layout":
                    self.assertEqual(out.read(name), src.read(name), name)
            self.assertEqual(out.getinfo("DataModel").compress_type, zipfile.ZIP_STORED)
            self.assertIsNone(out.testzip())

            raw = out.read("Report/Layout")
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "must not be UTF-8")
            json.loads(raw.decode("utf-16-le"))  # valid UTF-16 LE JSON

        layout = read_layout(self.out)
        sec = layout["sections"][0]
        self.assertEqual(sec["displayName"], "Overview")
        self.assertEqual(len(sec["visualContainers"]), 3)  # title + 2 visuals
        # Report-level settings from the PBRS-saved input are preserved
        self.assertEqual(layout["config"], "{\"version\":\"5.43\"}")
        for vc in sec["visualContainers"]:
            cfg = json.loads(vc["config"])
            self.assertIn(cfg["singleVisual"]["visualType"], SUPPORTED_VISUAL_TYPES)

    def test_warns_on_visuals_pbrs_may_lack(self):
        output = self._build(lambda: [
            add_visual("map", {"category": "Geo[City]", "size": "Sales[Revenue]"},
                       vid=1, title="Map"),
            add_visual("text_slicer", {"field": "Geo[Region]"}, vid=2, title="Region"),
            add_visual("card", {"value": "Sales[Revenue]"}, vid=3, title="Revenue"),
        ])
        self.assertIn("PBRS Desktop compatibility warnings", output)
        self.assertIn("azureMap", output)
        self.assertIn("textSlicer", output)
        self.assertEqual(len(pbrs_visual_warnings(read_layout(self.out))), 2)

    def test_no_warnings_for_standard_visuals(self):
        output = self._build(lambda: [
            add_visual("clustered_column", {"category": "Geo[Region]",
                                            "value": "Sales[Revenue]"}, vid=1, title="A"),
            add_visual("slicer", {"field": "Geo[Region]"}, vid=2, title="B"),
        ])
        self.assertNotIn("compatibility warnings", output)

    def test_refuses_to_overwrite_input(self):
        with mock.patch.dict(sys.modules, {"visuals_config": fake_config(lambda: [])}), \
             contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit):
            build(self.src, self.src)

    def test_analyzer_reads_utf16_version(self):
        self.assertEqual(pbix_analyzer._extract_pbix_version(self.src), "1.28")

    def test_validator_uses_shared_visual_list(self):
        self.assertEqual(pbrs_validator.PBRS_UNSUPPORTED_VISUALS, frozenset(PBRS_VISUAL_NOTES))
        self.assertTrue(set(PBRS_VISUAL_NOTES) <= SUPPORTED_VISUAL_TYPES)
        metadata = {"report": {"pages": [{"name": "P1", "visuals": [
            {"type": "azureMap", "id": "v1"}, {"type": "barChart", "id": "v2"}]}]}}
        issues = pbrs_validator._check_visual_types(metadata)
        self.assertEqual(len(issues), 1)
        self.assertIn("azureMap", issues[0].message)


class DesktopFinderTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pf = os.path.join(self.tmp, "Program Files")
        self.env = mock.patch.dict(os.environ, {
            "ProgramFiles": self.pf, "ProgramFiles(x86)": "",
            "LOCALAPPDATA": "", "PBI_DESKTOP_PATH": "",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        for root, dirs, files in os.walk(self.tmp, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        os.rmdir(self.tmp)

    def _install(self, folder: str) -> str:
        path = os.path.join(self.pf, folder, "bin", "PBIDesktop.exe")
        os.makedirs(os.path.dirname(path))
        open(path, "w").close()
        return path

    def test_prefers_report_server_edition(self):
        regular = self._install("Microsoft Power BI Desktop")
        rs = self._install("Microsoft Power BI Desktop RS")
        self.assertEqual(desktop.find_desktop()[0], rs)
        self.assertEqual(desktop.find_desktop(desktop.RS)[0], rs)
        self.assertEqual(desktop.find_desktop(desktop.REGULAR)[0], regular)

    def test_falls_back_to_regular(self):
        regular = self._install("Microsoft Power BI Desktop")
        self.assertEqual(desktop.find_desktop()[0], regular)
        self.assertEqual(desktop.find_desktop(desktop.RS), ("", ""))

    def test_env_override(self):
        exe = os.path.join(self.tmp, "custom.exe")
        open(exe, "w").close()
        with mock.patch.dict(os.environ, {"PBI_DESKTOP_PATH": exe}):
            self.assertEqual(desktop.find_desktop(desktop.RS)[0], exe)

    def test_flags(self):
        self.assertEqual(desktop.prefer_from_flags(["--open", "--rs"]), desktop.RS)
        self.assertEqual(desktop.prefer_from_flags(["--regular"]), desktop.REGULAR)
        self.assertEqual(desktop.prefer_from_flags(["--open"]), desktop.AUTO)

    def test_rs_only_does_not_fall_back(self):
        self._install("Microsoft Power BI Desktop")
        with mock.patch("subprocess.Popen") as popen, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(desktop.open_in_desktop("x.pbix", desktop.RS))
        popen.assert_not_called()

    def test_opens_rs_edition(self):
        rs = self._install("Microsoft Power BI Desktop RS")
        with mock.patch("subprocess.Popen") as popen, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(desktop.open_in_desktop("x.pbix"))
        self.assertEqual(popen.call_args[0][0][0], rs)


if __name__ == "__main__":
    unittest.main()
