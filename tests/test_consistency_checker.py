"""
Tests for consistency_checker.py: the Violation class, each individual
checker function, and ConsistencyAnalyzer.analyze's summary/sorting.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import os
import sys
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

from consistency_checker import (  # noqa: E402
    ConsistencyAnalyzer,
    Violation,
    _check_alignment,
    _check_data_types,
    _check_hidden_objects,
    _check_measure_consistency,
    _check_naming_conventions,
    _check_title_presence,
    _check_unused_objects,
    _check_visual_sizing,
)


def _visual(vid, vtype="barChart", x=0, y=0, w=400, h=300, has_title=True):
    return {"id": vid, "type": vtype, "has_title": has_title,
            "position": {"x": x, "y": y, "w": w, "h": h}}


def _page(name, visuals):
    return {"name": name, "visuals": visuals}


class ViolationTest(unittest.TestCase):

    def test_to_dict_includes_all_fields(self):
        v = Violation("warning", "sizing", "message", objects=["1", "2"],
                      suggestion="fix it")
        self.assertEqual(v.to_dict(), {
            "severity": "warning", "category": "sizing", "message": "message",
            "objects": ["1", "2"], "suggestion": "fix it",
        })

    def test_defaults_for_optional_fields(self):
        v = Violation("info", "cat", "msg")
        self.assertEqual(v.objects, [])
        self.assertIsNone(v.suggestion)


class TitlePresenceTest(unittest.TestCase):

    def test_flags_visual_without_title(self):
        metadata = {"report": {"pages": [
            _page("Overview", [_visual(1, has_title=False)])
        ]}}
        violations = _check_title_presence(metadata)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "warning")
        self.assertEqual(violations[0].category, "missing_title")

    def test_does_not_flag_visual_with_title(self):
        metadata = {"report": {"pages": [
            _page("Overview", [_visual(1, has_title=True)])
        ]}}
        self.assertEqual(_check_title_presence(metadata), [])

    def test_skips_decorative_types(self):
        metadata = {"report": {"pages": [
            _page("Overview", [_visual(1, vtype="textbox", has_title=False)])
        ]}}
        self.assertEqual(_check_title_presence(metadata), [])


class VisualSizingTest(unittest.TestCase):

    def test_flags_large_size_variance_within_same_type(self):
        metadata = {"report": {"pages": [_page("P1", [
            _visual(1, vtype="card", w=200, h=120),
            _visual(2, vtype="card", w=300, h=200),
        ])]}}
        violations = _check_visual_sizing(metadata)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "sizing_inconsistency")

    def test_small_variance_under_threshold_not_flagged(self):
        metadata = {"report": {"pages": [_page("P1", [
            _visual(1, vtype="card", w=200, h=120),
            _visual(2, vtype="card", w=210, h=125),
        ])]}}
        self.assertEqual(_check_visual_sizing(metadata), [])

    def test_single_visual_of_a_type_not_flagged(self):
        metadata = {"report": {"pages": [_page("P1", [_visual(1, vtype="card")])]}}
        self.assertEqual(_check_visual_sizing(metadata), [])


class AlignmentTest(unittest.TestCase):

    def test_flags_multiple_off_grid_visuals(self):
        metadata = {"report": {"pages": [_page("P1", [
            _visual(1, x=13, y=27), _visual(2, x=5, y=5),
        ])]}}
        violations = _check_alignment(metadata)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "alignment")
        self.assertEqual(len(violations[0].objects), 2)

    def test_single_off_grid_visual_not_flagged(self):
        # Checker only flags when more than one visual is off-grid.
        metadata = {"report": {"pages": [_page("P1", [_visual(1, x=13, y=27)])]}}
        self.assertEqual(_check_alignment(metadata), [])

    def test_on_grid_visuals_not_flagged(self):
        metadata = {"report": {"pages": [_page("P1", [
            _visual(1, x=10, y=20), _visual(2, x=30, y=40),
        ])]}}
        self.assertEqual(_check_alignment(metadata), [])

    def test_textbox_skipped(self):
        metadata = {"report": {"pages": [_page("P1", [
            _visual(1, vtype="textbox", x=13, y=27),
            _visual(2, x=17, y=29),
        ])]}}
        # Only one non-textbox visual is off-grid -> not flagged (needs > 1)
        self.assertEqual(_check_alignment(metadata), [])


class HiddenObjectsTest(unittest.TestCase):

    def test_flags_when_over_30_percent_hidden(self):
        metadata = {"datamodel": {"tables": [{"columns": [
            {"hidden": True}, {"hidden": True}, {"hidden": False}, {"hidden": False},
        ]}]}}
        violations = _check_hidden_objects(metadata)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "excessive_hidden")

    def test_not_flagged_under_threshold(self):
        metadata = {"datamodel": {"tables": [{"columns": [
            {"hidden": True}] + [{"hidden": False}] * 9}]}}
        self.assertEqual(_check_hidden_objects(metadata), [])

    def test_no_columns_not_flagged(self):
        self.assertEqual(_check_hidden_objects({"datamodel": {"tables": []}}), [])


class MeasureConsistencyTest(unittest.TestCase):

    def test_flags_no_measures(self):
        metadata = {"datamodel": {"tables": [{"measures": []}]}}
        violations = _check_measure_consistency(metadata)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "no_measures")

    def test_not_flagged_when_measures_exist(self):
        metadata = {"datamodel": {"tables": [{"measures": [{"name": "Total"}]}]}}
        self.assertEqual(_check_measure_consistency(metadata), [])


class NamingConventionsTest(unittest.TestCase):

    def test_flags_mixed_case_table_name(self):
        metadata = {"datamodel": {"tables": [{"name": "Fact_Sales_Data"}]}}
        violations = _check_naming_conventions(metadata)
        self.assertTrue(any(v.category == "naming_convention" for v in violations))

    def test_flags_lowercase_measure_name(self):
        metadata = {"datamodel": {"tables": [
            {"name": "Sales", "measures": [{"name": "total revenue"}]}
        ]}}
        violations = _check_naming_conventions(metadata)
        self.assertTrue(any("total revenue" in v.message for v in violations))

    def test_clean_names_not_flagged(self):
        metadata = {"datamodel": {"tables": [
            {"name": "Sales", "measures": [{"name": "Total Revenue"}]}
        ]}}
        violations = _check_naming_conventions(metadata)
        self.assertEqual(violations, [])


class DataTypesTest(unittest.TestCase):

    def test_flags_string_heavy_model(self):
        metadata = {"datamodel": {"tables": [{"columns": [
            {"type": "string"}] * 5 + [{"type": "int64"}]}]}}
        violations = _check_data_types(metadata)
        self.assertEqual(len(violations), 1)

    def test_balanced_model_not_flagged(self):
        metadata = {"datamodel": {"tables": [{"columns": [
            {"type": "string"}, {"type": "int64"}, {"type": "int64"}]}]}}
        self.assertEqual(_check_data_types(metadata), [])


class UnusedObjectsTest(unittest.TestCase):

    def test_no_lineage_returns_empty(self):
        self.assertEqual(_check_unused_objects({}, None), [])

    def test_flags_orphaned_tables_and_measures(self):
        lineage = {"orphaned_objects": {
            "tables": [{"name": "OldStaging"}],
            "measures": [{"table": "Sales", "measure": "Unused Measure"}],
        }}
        violations = _check_unused_objects({}, lineage)
        self.assertEqual(len(violations), 2)
        categories = {v.category for v in violations}
        self.assertEqual(categories, {"unused_objects"})


class ConsistencyAnalyzerTest(unittest.TestCase):

    def test_analyze_summarizes_and_sorts_by_severity(self):
        metadata = {
            "report": {"pages": [_page("P1", [
                _visual(1, vtype="card", w=200, h=120, has_title=False),
                _visual(2, vtype="card", w=400, h=300, has_title=False),
            ])]},
            "datamodel": {"tables": [{
                "name": "Sales", "measures": [], "columns": [],
            }]},
        }
        result = ConsistencyAnalyzer(metadata).analyze()

        self.assertEqual(result["summary"]["total_violations"], len(result["violations"]))
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertGreater(result["summary"]["warnings"], 0)

        # Sorted so errors come before warnings before info everywhere present
        severity_order = {"error": 0, "warning": 1, "info": 2}
        ranks = [severity_order[v["severity"]] for v in result["violations"]]
        self.assertEqual(ranks, sorted(ranks))

    def test_analyze_with_no_issues_returns_empty_violations(self):
        metadata = {
            "report": {"pages": [_page("P1", [
                _visual(1, x=10, y=20, has_title=True),
            ])]},
            "datamodel": {"tables": [{
                "name": "Sales",
                "measures": [{"name": "Total Revenue"}],
                "columns": [{"hidden": False, "type": "int64"}],
            }]},
        }
        result = ConsistencyAnalyzer(metadata).analyze()
        self.assertEqual(result["summary"]["total_violations"], 0)
        self.assertEqual(result["violations"], [])


if __name__ == "__main__":
    unittest.main()
