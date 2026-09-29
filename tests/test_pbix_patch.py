"""
Tests for pbix_patch.py: strips SecurityBindings, replaces Report/Layout,
and copies everything else unchanged.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest
import zipfile

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

from pbix_patch import patch_pbix  # noqa: E402


class PatchPbixTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.input_path = os.path.join(self.tmp, "in.pbix")
        self.layout_path = os.path.join(self.tmp, "new.layout")
        self.output_path = os.path.join(self.tmp, "out.pbix")

        with open(self.layout_path, "wb") as f:
            f.write("{\"sections\":[]}".encode("utf-16-le"))

        with zipfile.ZipFile(self.input_path, "w") as z:
            z.writestr("Report/Layout", "old layout".encode("utf-16-le"),
                       compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("DataModel", b"\x00binary-model-data\xff" * 32,
                       compress_type=zipfile.ZIP_STORED)
            z.writestr("Version", "1.28".encode("utf-16-le"))
            z.writestr("SecurityBindings", b"\x01dpapi-blob\x02")

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def _patch_quietly(self):
        with contextlib.redirect_stdout(io.StringIO()):
            patch_pbix(self.input_path, self.layout_path, self.output_path)

    def test_security_bindings_removed(self):
        self._patch_quietly()
        with zipfile.ZipFile(self.output_path) as z:
            self.assertNotIn("SecurityBindings", z.namelist())

    def test_report_layout_replaced(self):
        self._patch_quietly()
        with zipfile.ZipFile(self.output_path) as z:
            with open(self.layout_path, "rb") as f:
                expected = f.read()
            self.assertEqual(z.read("Report/Layout"), expected)

    def test_datamodel_kept_uncompressed_and_unchanged(self):
        self._patch_quietly()
        with zipfile.ZipFile(self.input_path) as src, \
             zipfile.ZipFile(self.output_path) as out:
            self.assertEqual(out.read("DataModel"), src.read("DataModel"))
            self.assertEqual(out.getinfo("DataModel").compress_type, zipfile.ZIP_STORED)

    def test_other_entries_copied_unchanged(self):
        self._patch_quietly()
        with zipfile.ZipFile(self.input_path) as src, \
             zipfile.ZipFile(self.output_path) as out:
            self.assertEqual(out.read("Version"), src.read("Version"))

    def test_output_only_missing_security_bindings(self):
        self._patch_quietly()
        with zipfile.ZipFile(self.input_path) as src, \
             zipfile.ZipFile(self.output_path) as out:
            self.assertEqual(set(out.namelist()),
                              set(src.namelist()) - {"SecurityBindings"})
            self.assertIsNone(out.testzip())

    def test_missing_input_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            with contextlib.redirect_stdout(io.StringIO()):
                patch_pbix(os.path.join(self.tmp, "nope.pbix"),
                           self.layout_path, self.output_path)

    def test_missing_layout_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            with contextlib.redirect_stdout(io.StringIO()):
                patch_pbix(self.input_path, os.path.join(self.tmp, "nope.layout"),
                           self.output_path)

    def test_empty_zip_raises_value_error(self):
        empty_path = os.path.join(self.tmp, "empty.pbix")
        with zipfile.ZipFile(empty_path, "w"):
            pass
        with self.assertRaises(ValueError):
            with contextlib.redirect_stdout(io.StringIO()):
                patch_pbix(empty_path, self.layout_path, self.output_path)


if __name__ == "__main__":
    unittest.main()
