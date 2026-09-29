"""
Tests that protect the demo: the sample dashboards must build cleanly, use only
visuals that are safe on Report Server, and every document must point at files
that exist.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))

import build as build_module  # noqa: E402
import lint  # noqa: E402
from layout_builder import read_layout  # noqa: E402
from test_pbrs import make_pbix  # noqa: E402
from visual_types import PBRS_VISUAL_NOTES  # noqa: E402

DEMO_DIR = os.path.join(REPO_DIR, "demo")

# Visuals whose data roles are consistent across every source we checked.
SAFE_TYPES = {"textbox", "card", "slicer", "clusteredColumnChart", "clusteredBarChart",
              "barChart", "donutChart", "tableEx", "pivotTable"}

# Files users create themselves; docs may name them without them existing here.
USER_OWNED = {"my_dashboard.py"}


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(DEMO_DIR, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuiltDemo:
    """Build a demo config onto a fresh sample report and read the result."""

    def __init__(self, config_name, **overrides):
        self.tmp = tempfile.mkdtemp()
        self.source = os.path.join(self.tmp, "in.pbix")
        self.output = os.path.join(self.tmp, "out.pbix")
        make_pbix(self.source)
        self.config_path = os.path.join(DEMO_DIR, config_name + ".py")
        with mock.patch.dict(sys.modules), contextlib.redirect_stdout(io.StringIO()) as log:
            if overrides:
                module = load_module(config_name)
                for key, value in overrides.items():
                    setattr(module, key, value)
                sys.modules["visuals_config"] = module
                from layout_builder import build_layout
                from pbix_patch import patch_pbix
                layout_file = os.path.join(self.tmp, "l.bin")
                build_layout(self.source, layout_file)
                patch_pbix(self.source, layout_file, self.output)
            else:
                build_module.build(self.source, self.output, config_path=self.config_path)
        self.log = log.getvalue()
        self.layout = read_layout(self.output)
        with contextlib.redirect_stdout(io.StringIO()):
            self.issues, self.visuals, _ = lint.lint(self.output)

    def containers(self):
        for page in self.layout["sections"]:
            for vc in page["visualContainers"]:
                yield page["displayName"], vc, json.loads(vc["config"])["singleVisual"]

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class SuperstoreDemoTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.built = BuiltDemo("superstore_dashboard")

    @classmethod
    def tearDownClass(cls):
        cls.built.close()

    def test_two_pages_with_the_expected_visuals(self):
        pages = {p["displayName"]: len(p["visualContainers"]) for p in self.built.layout["sections"]}
        self.assertEqual(pages, {"Executive Summary": 11, "Region and Product Detail": 4})

    def test_layout_is_clean(self):
        problems = [(i.severity, i.message) for i in self.built.issues]
        self.assertEqual(problems, [])

    def test_only_report_server_safe_visuals(self):
        used = {sv["visualType"] for _, _, sv in self.built.containers()}
        self.assertLessEqual(used, SAFE_TYPES)
        self.assertFalse(used & set(PBRS_VISUAL_NOTES))

    def test_no_report_server_compatibility_warning(self):
        self.assertNotIn("compatibility warnings", self.built.log)

    def test_every_visual_has_a_title(self):
        for page, vc, sv in self.built.containers():
            if sv["visualType"] == "textbox":
                continue
            self.assertTrue(sv["vcObjects"].get("title"), f"{page}: {sv['visualType']}")

    def test_slicers_are_plain_columns(self):
        slicers = [json.loads(vc["query"]) for _, vc, sv in self.built.containers()
                   if sv["visualType"] == "slicer"]
        self.assertEqual(len(slicers), 2)
        for query in slicers:
            self.assertNotIn("Aggregation", query["Select"][0])

    def test_tables_mix_plain_columns_and_sums(self):
        for _, vc, sv in self.built.containers():
            if sv["visualType"] == "tableEx":
                kinds = ["Aggregation" in s for s in json.loads(vc["query"])["Select"]]
                self.assertIn(True, kinds)
                self.assertIn(False, kinds)

    def test_projections_match_the_query_everywhere(self):
        for page, vc, sv in self.built.containers():
            names = {s["Name"] for s in json.loads(vc["query"] or "{}").get("Select", [])}
            refs = {p["queryRef"] for plist in sv.get("projections", {}).values() for p in plist}
            self.assertEqual(refs, names, f"{page}: {sv['visualType']}")

    def test_fourth_card_is_average_discount_by_default(self):
        cards = [json.loads(vc["query"]) for _, vc, sv in self.built.containers()
                 if sv["visualType"] == "card"]
        self.assertEqual(cards[3]["Select"][0]["Name"], "Avg(Orders.Discount)")

    def test_a_model_measure_replaces_it_when_configured(self):
        built = BuiltDemo("superstore_dashboard", MARGIN_MEASURE="Profit Ratio")
        try:
            cards = [json.loads(vc["query"]) for _, vc, sv in built.containers()
                     if sv["visualType"] == "card"]
            self.assertEqual(cards[3]["Select"][0]["Measure"]["Property"], "Profit Ratio")
        finally:
            built.close()


class NorthwindCheckTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.built = BuiltDemo("northwind_check")

    @classmethod
    def tearDownClass(cls):
        cls.built.close()

    def test_three_pages(self):
        self.assertEqual([p["displayName"] for p in self.built.layout["sections"]],
                         ["1 Safe visuals", "2 Legend and combo", "3 KPI gauge scatter"])

    def test_layout_is_clean(self):
        self.assertEqual([i.message for i in self.built.issues if i.severity == "error"], [])

    def test_a_b_pairs_use_different_role_names(self):
        by_title = {}
        for _, _, sv in self.built.containers():
            if sv["visualType"] == "textbox":
                continue
            title = sv["vcObjects"]["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"]
            by_title[title.strip("'")] = set(sv["projections"])
        column_a = next(v for t, v in by_title.items() if t.startswith("A  column"))
        column_b = next(v for t, v in by_title.items() if t.startswith("B  column"))
        self.assertIn("Legend", column_a)
        self.assertIn("Series", column_b)
        combo_a = next(v for t, v in by_title.items() if t.startswith("A  combo"))
        combo_b = next(v for t, v in by_title.items() if t.startswith("B  combo"))
        self.assertTrue({"ColumnY", "LineY"} <= combo_a)
        self.assertTrue({"Y", "Y2"} <= combo_b)

    def test_model_measures_are_bound_as_measures(self):
        measures = [json.loads(vc["query"])["Select"][0] for _, vc, sv in self.built.containers()
                    if sv["visualType"] == "card"]
        names = [m["Measure"]["Property"] for m in measures if "Measure" in m]
        self.assertEqual(names, ["Avg Order Value", "Order Count"])

    def test_raw_second_axis_role_is_aggregated(self):
        for _, vc, sv in self.built.containers():
            if "Y2" in sv.get("projections", {}):
                self.assertIn("Aggregation", json.loads(vc["query"])["Select"][2])


class DocumentReferencesTest(unittest.TestCase):

    DOCS = ["START_HERE.md", "README.md", "AGENTS.md", "CHANGELOG.md",
            "demo/USER_GUIDE.md", "demo/DEMO_SCRIPT.md", "demo/PROMPTS.md",
            "demo/VERIFY_IN_DESKTOP.md"]

    def test_documents_exist(self):
        for doc in self.DOCS:
            with self.subTest(doc=doc):
                self.assertTrue(os.path.isfile(os.path.join(REPO_DIR, doc)))

    def test_every_named_file_exists(self):
        pattern = re.compile(r"`([\w\\/.\-]+\.(?:py|bat|md))`")
        for doc in ("START_HERE.md", "demo/USER_GUIDE.md", "demo/DEMO_SCRIPT.md",
                    "demo/PROMPTS.md", "demo/VERIFY_IN_DESKTOP.md"):
            with open(os.path.join(REPO_DIR, doc), encoding="utf-8") as f:
                text = f.read()
            for name in set(pattern.findall(text)):
                if name in USER_OWNED or name.startswith(("C:", "skills")) or "<" in name:
                    continue
                relative = name.replace("\\", "/")
                candidates = [os.path.join(REPO_DIR, relative),
                              os.path.join(REPO_DIR, "demo", relative)]
                with self.subTest(doc=doc, file=name):
                    self.assertTrue(any(os.path.isfile(c) for c in candidates),
                                    f"{doc} mentions {name}, which does not exist")

    def test_skill_paths_named_in_start_here_exist(self):
        with open(os.path.join(REPO_DIR, "START_HERE.md"), encoding="utf-8") as f:
            text = f.read()
        for path in set(re.findall(r"`(skills\\[\w\-]+\\SKILL\.md)`", text)):
            with self.subTest(path=path):
                self.assertTrue(os.path.isfile(os.path.join(REPO_DIR, path.replace("\\", "/"))))

    def test_prompts_and_script_use_the_same_dashboard_prompt_terms(self):
        with open(os.path.join(DEMO_DIR, "PROMPTS.md"), encoding="utf-8") as f:
            prompts = f.read()
        self.assertIn("executive dashboard", prompts)
        with open(os.path.join(DEMO_DIR, "DEMO_SCRIPT.md"), encoding="utf-8") as f:
            script = f.read()
        self.assertIn("executive dashboard", script)


if __name__ == "__main__":
    unittest.main()
