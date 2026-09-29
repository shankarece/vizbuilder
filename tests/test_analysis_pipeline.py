"""
Tests for reading saved reports: layouts written by vizbuilder AND by Power BI
Desktop / other tools, the optional pbixray model reader, and lineage.

These cover bugs found by running the analysis on a file that was not written by
vizbuilder (which is what a report looks like after you File -> Save in Desktop).

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
import zipfile
from unittest import mock

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

import lint  # noqa: E402
import pbix_analyzer  # noqa: E402
from data_lineage import DataLineageAnalyzer, _parse_query_ref  # noqa: E402
from layout_builder import (  # noqa: E402
    add_title,
    add_visual,
    container_id,
    container_position,
    set_container_position,
)


def write_pbix(path: str, sections: list, datamodel: bytes = b"\x00model\xff" * 16) -> None:
    layout = {"id": 0, "sections": sections, "config": "{}"}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Version", "1.28".encode("utf-16-le"))
        z.writestr("DataModel", datamodel, compress_type=zipfile.ZIP_STORED)
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))


def section(name: str, containers: list) -> dict:
    return {"id": 0, "name": name.replace(" ", ""), "displayName": name,
            "filters": "[]", "ordinal": 0, "visualContainers": containers,
            "config": "{}", "displayOption": 1, "width": 1280, "height": 720}


def desktop_style_container(name, x, y, w, h, visual_type="card", query_ref=None):
    """A container shaped like Power BI Desktop writes it: no "id", no "position",
    x/y/width/height on the container itself."""
    single = {"visualType": visual_type, "projections": {}}
    if query_ref:
        single["projections"] = {"Values": [{"queryRef": query_ref}]}
    config = {"name": name, "layouts": [{"id": 0, "position": {
        "x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0}}],
        "singleVisual": single}
    return {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0,
            "config": json.dumps(config), "filters": "[]"}


class ContainerHelpersTest(unittest.TestCase):

    def test_position_from_nested_form(self):
        vc = {"position": {"x": 1, "y": 2, "width": 3, "height": 4}}
        self.assertEqual(container_position(vc)["width"], 3)

    def test_position_from_desktop_style_top_level_fields(self):
        vc = desktop_style_container("v1", 10, 20, 300, 120)
        pos = container_position(vc)
        self.assertEqual((pos["x"], pos["y"], pos["width"], pos["height"]),
                         (10, 20, 300, 120))

    def test_position_falls_back_to_config_layout(self):
        config = {"layouts": [{"id": 0, "position": {"x": 5, "y": 6, "width": 7, "height": 8}}]}
        self.assertEqual(container_position({"config": json.dumps(config)})["x"], 5)

    def test_position_empty_when_nothing_is_stored(self):
        self.assertEqual(container_position({"config": "not json"}), {})

    def test_position_is_a_copy(self):
        vc = {"position": {"x": 1, "y": 2, "width": 3, "height": 4}}
        container_position(vc)["x"] = 999
        self.assertEqual(vc["position"]["x"], 1)

    def test_set_position_updates_desktop_style_container_in_place(self):
        vc = desktop_style_container("v1", 10, 20, 300, 120)
        set_container_position(vc, {"x": 30, "y": 40, "z": 0, "width": 300, "height": 120})
        self.assertEqual((vc["x"], vc["y"]), (30, 40))
        self.assertNotIn("position", vc)  # don't bolt a foreign key onto Desktop's shape

    def test_set_position_updates_both_forms_of_a_vizbuilder_container(self):
        vc = add_visual("card", {"value": "T[V]"}, x=10, y=20, w=200, h=100, vid=1)
        set_container_position(vc, {"x": 50, "y": 60, "z": 0, "width": 200, "height": 100,
                                    "tabOrder": 0})
        self.assertEqual(vc["position"]["x"], 50)
        self.assertEqual(vc["x"], 50)

    def test_id_prefers_explicit_id_then_config_name_then_index(self):
        self.assertEqual(container_id({"id": 7}), 7)
        self.assertEqual(container_id({"id": 0}), 0)
        self.assertEqual(container_id(desktop_style_container("abc123", 0, 0, 1, 1)), "abc123")
        self.assertEqual(container_id({"config": "{}"}, 4), "#4")


class VizbuilderOutputShapeTest(unittest.TestCase):

    def test_containers_carry_standard_top_level_position_fields(self):
        vc = add_visual("bar", {"category": "T[C]", "value": "T[V]"},
                        x=20, y=60, w=600, h=290, vid=1, tab_order=3)
        for key in ("x", "y", "z", "width", "height", "tabOrder"):
            self.assertEqual(vc[key], vc["position"][key], key)
        self.assertEqual((vc["x"], vc["y"], vc["width"], vc["height"]), (20, 60, 600, 290))

    def test_title_container_carries_them_too(self):
        vc = add_title("Sales")
        self.assertEqual(vc["width"], 1280)
        self.assertEqual(vc["z"], vc["position"]["z"])


class AnalyzerOnSavedReportsTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "r.pbix")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _layout_meta(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return pbix_analyzer._extract_layout_metadata(self.path)

    def test_reads_bindings_from_legacy_projections(self):
        write_pbix(self.path, [section("P1", [
            add_visual("bar", {"category": "Orders[Region]", "value": "Orders[Sales]"},
                       vid=1, title="t"),
            add_visual("card", {"value": "Orders[[Profit Ratio]]"}, vid=2, title="m"),
        ])])
        visuals = self._layout_meta()["pages"][0]["visuals"]
        refs = {b["query_ref"] for v in visuals for b in v["bindings"]}
        self.assertEqual(refs, {"Orders.Region", "Sum(Orders.Sales)", "Orders.Profit Ratio"})

    def test_desktop_style_containers_get_positions_and_unique_ids(self):
        write_pbix(self.path, [section("P1", [
            desktop_style_container("aaa", 20, 60, 290, 100, query_ref="Orders.Sales"),
            desktop_style_container("bbb", 330, 60, 290, 100, query_ref="Orders.Sales"),
        ])])
        visuals = self._layout_meta()["pages"][0]["visuals"]
        self.assertEqual([v["id"] for v in visuals], ["aaa", "bbb"])
        self.assertEqual(visuals[0]["position"], {"x": 20, "y": 60, "w": 290, "h": 100})

    def test_lint_sees_real_sizes_on_desktop_style_containers(self):
        write_pbix(self.path, [section("P1", [
            desktop_style_container("aaa", 20, 60, 290, 100),
        ])])
        with contextlib.redirect_stdout(io.StringIO()):
            issues, visuals, _ = lint.lint(self.path)
        self.assertEqual((visuals[0]["w"], visuals[0]["h"]), (290, 100))
        self.assertFalse([i for i in issues if "very small" in i.message])

    def test_lint_fix_moves_desktop_style_containers_without_breaking_them(self):
        write_pbix(self.path, [section("P1", [
            desktop_style_container("aaa", 23, 61, 290, 100, visual_type="card"),
            desktop_style_container("bbb", 331, 59, 290, 100, visual_type="card"),
        ])])
        layout = lint.read_layout(self.path)
        fixed, fixes = lint.auto_fix(layout)
        self.assertTrue(fixes)
        for vc in fixed["sections"][0]["visualContainers"]:
            self.assertEqual(vc["x"] % 10, 0)          # top-level fields were updated
            self.assertNotIn("position", vc)
            cfg = json.loads(vc["config"])
            self.assertEqual(cfg["layouts"][0]["position"]["x"], vc["x"])


class QueryRefParsingTest(unittest.TestCase):

    def test_every_shape_a_saved_report_uses(self):
        cases = {
            "Orders.Region": ("Orders", "Region"),
            "Sum(Orders.Revenue)": ("Orders", "Revenue"),
            "Orders.Total Revenue": ("Orders", "Total Revenue"),
            "Orders[Sales]": ("Orders", "Sales"),
            "Avg(Orders.Discount)": ("Orders", "Discount"),
        }
        for ref, expected in cases.items():
            with self.subTest(ref=ref):
                self.assertEqual(_parse_query_ref(ref), expected)

    def test_unparseable_returns_none(self):
        self.assertIsNone(_parse_query_ref(""))
        self.assertIsNone(_parse_query_ref("justaname"))


class LineageTest(unittest.TestCase):

    def _metadata(self, page_name="Page 1"):
        return {
            "datamodel": {"tables": [
                {"name": "Orders", "hidden": False,
                 "columns": [{"name": "Region"}, {"name": "Sales"}, {"name": "OrderID"}],
                 "measures": [{"name": "Profit Ratio", "expression": "DIVIDE(1,2)"},
                              {"name": "Unused Measure", "expression": "1"}]},
                {"name": "Staging", "hidden": False,
                 "columns": [{"name": "Junk"}], "measures": []},
            ]},
            "report": {"pages": [{"name": page_name, "visuals": [
                {"id": "aaa", "type": "barChart", "bindings": [
                    {"role": "Category", "query_ref": "Orders.Region"},
                    {"role": "Y", "query_ref": "Sum(Orders.Sales)"}]},
                {"id": 2, "type": "card", "bindings": [
                    {"role": "Values", "query_ref": "Orders.Profit Ratio"}]},
            ]}]},
        }

    def _run(self, metadata):
        return DataLineageAnalyzer(metadata).analyze()

    def test_matches_saved_query_refs_to_model_fields(self):
        result = self._run(self._metadata())
        self.assertEqual(result["fields_used"], 3)

    def test_finds_orphaned_table_column_and_measure(self):
        orphaned = self._run(self._metadata())["orphaned_objects"]
        self.assertEqual([t["name"] for t in orphaned["tables"]], ["Staging"])
        self.assertEqual([m["measure"] for m in orphaned["measures"]], ["Unused Measure"])
        self.assertIn("OrderID", [c["column"] for c in orphaned["columns"]])
        self.assertNotIn("Sales", [c["column"] for c in orphaned["columns"]])

    def test_impact_summary_runs_and_counts_correctly(self):
        summary = self._run(self._metadata())["impact_summary"]
        self.assertEqual(summary["tables_with_usage"], 1)
        self.assertEqual(summary["tables_unused"], 1)
        self.assertEqual(summary["measures_with_usage"], 1)
        self.assertEqual(summary["measures_unused"], 1)
        self.assertEqual(summary["visuals_connected"], 2)

    def test_string_ids_and_page_names_containing_colons(self):
        result = self._run(self._metadata(page_name="Sales: Overview"))
        self.assertEqual(result["fields_used"], 3)


class PbixrayOptionalTest(unittest.TestCase):
    """pbixray is optional; without it the analyzer must behave as before."""

    class Frame:
        def __init__(self, rows):
            self.rows = rows
            self.empty = not rows

        def to_dict(self, orient):
            assert orient == "records"
            return list(self.rows)

    def _fake_module(self, fail=False):
        Frame = self.Frame

        class FakePBIXRay:
            def __init__(self, path):
                if fail:
                    raise RuntimeError("cannot decode")
                self.tables = ["Orders", "Regions"]
                self.schema = Frame([
                    {"TableName": "Orders", "ColumnName": "Sales", "PandasDataType": "Int64"},
                    {"TableName": "Orders", "ColumnName": "Region", "PandasDataType": "string"},
                    {"TableName": "Regions", "ColumnName": "Name", "PandasDataType": "string"}])
                self.dax_measures = Frame([
                    {"TableName": "Orders", "Name": "Total Sales",
                     "Expression": "SUM(Orders[Sales])", "DisplayFolder": None}])
                self.dax_columns = Frame([
                    {"TableName": "Orders", "ColumnName": "Region", "Expression": "RELATED(Regions[Name])"}])
                self.relationships = Frame([
                    {"FromTableName": "Orders", "FromColumnName": "Region",
                     "ToTableName": "Regions", "ToColumnName": "Name",
                     "Cardinality": "M:1", "CrossFilteringBehavior": "Both", "IsActive": 1}])

        return types.SimpleNamespace(PBIXRay=FakePBIXRay)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "m.pbix")
        write_pbix(self.path, [section("P1", [])])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _datamodel(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return pbix_analyzer._extract_datamodel_metadata(self.path)

    def test_uses_pbixray_when_installed(self):
        with mock.patch.dict(sys.modules, {"pbixray": self._fake_module()}):
            model = self._datamodel()
        self.assertEqual(model["source"], "pbixray")
        self.assertEqual((model["total_tables"], model["total_columns"], model["total_measures"]),
                         (2, 3, 1))
        orders = model["tables"][0]
        self.assertEqual([c["type"] for c in orders["columns"]], ["int64", "string"])
        self.assertEqual(orders["columns"][1]["expression"], "RELATED(Regions[Name])")
        self.assertEqual(orders["measures"][0]["name"], "Total Sales")

    def test_relationship_fields_match_what_the_validator_expects(self):
        with mock.patch.dict(sys.modules, {"pbixray": self._fake_module()}):
            rel = self._datamodel()["relationships"][0]
        self.assertEqual(rel["cross_filter"], "both")  # pbrs_validator compares to "both"
        self.assertEqual((rel["from_table"], rel["to_table"], rel["cardinality"]),
                         ("Orders", "Regions", "M:1"))
        self.assertTrue(rel["active"])

    def test_missing_pbixray_falls_back_and_says_how_to_get_it(self):
        with mock.patch.dict(sys.modules, {"pbixray": None}):
            model = self._datamodel()
        self.assertEqual(model["source"], "none")
        self.assertEqual(model["tables"], [])
        self.assertIn("pip install pbixray", model["notes"])

    def test_pbixray_failure_falls_back_instead_of_crashing(self):
        with mock.patch.dict(sys.modules, {"pbixray": self._fake_module(fail=True)}):
            model = self._datamodel()
        self.assertEqual(model["source"], "none")


if __name__ == "__main__":
    unittest.main()
