"""
Tests for layout_builder.py: field-ref parsing, add_visual/add_title output
structure, and the UTF-16 LE read_layout/write_layout round trip.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import json
import os
import sys
import tempfile
import unittest
import zipfile

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

from layout_builder import (  # noqa: E402
    add_title,
    add_visual,
    parse_binding,
    parse_field,
    parse_field_ref,
    read_layout,
    write_layout,
)


class ParseFieldRefTest(unittest.TestCase):

    def test_simple_reference(self):
        self.assertEqual(parse_field_ref("Orders[Sales]"), ("Orders", "Sales"))

    def test_reference_with_spaces(self):
        self.assertEqual(parse_field_ref("Orders[Order Date]"), ("Orders", "Order Date"))

    def test_strips_whitespace_inside_brackets(self):
        # The ref must still end with "]" (no trailing whitespace), but
        # table/column names are trimmed.
        self.assertEqual(parse_field_ref("Orders [ Sales ]"), ("Orders", "Sales"))

    def test_missing_bracket_raises(self):
        with self.assertRaises(ValueError):
            parse_field_ref("Orders.Sales")

    def test_unclosed_bracket_raises(self):
        with self.assertRaises(ValueError):
            parse_field_ref("Orders[Sales")


class ParseFieldTest(unittest.TestCase):

    def test_column(self):
        self.assertEqual(parse_field("Orders[Sales]"), ("Orders", "Sales", False))

    def test_measure_uses_double_brackets(self):
        self.assertEqual(parse_field("Orders[[Total Sales]]"),
                         ("Orders", "Total Sales", True))

    def test_measure_name_may_contain_spaces_and_symbols(self):
        self.assertEqual(parse_field("Orders[[Profit %  (YTD)]]"),
                         ("Orders", "Profit %  (YTD)", True))

    def test_empty_names_rejected(self):
        for bad in ("Orders[]", "Orders[[]]", "[Sales]", "[[Sales]]"):
            with self.subTest(ref=bad):
                with self.assertRaises(ValueError):
                    parse_field(bad)

    def test_error_message_explains_both_forms(self):
        with self.assertRaises(ValueError) as ctx:
            parse_field("Orders.Sales")
        self.assertIn("Table[[Measure]]", str(ctx.exception))

    def test_parse_field_ref_still_returns_table_and_column(self):
        self.assertEqual(parse_field_ref("Orders[Sales]"), ("Orders", "Sales"))


class MeasureBindingTest(unittest.TestCase):
    """Table[[Measure]] must reference the model measure, not Sum() a column."""

    def _visual(self, **bindings):
        vc = add_visual("bar", bindings, vid=1, title="t")
        return (json.loads(vc["config"])["singleVisual"], json.loads(vc["query"]),
                json.loads(vc["dataTransforms"]))

    def test_measure_select_item_matches_classic_layout_shape(self):
        _, query, _ = self._visual(category="Orders[Region]",
                                   value="Orders[[Profit Ratio]]")
        measure = query["Select"][1]
        self.assertEqual(measure["Measure"]["Property"], "Profit Ratio")
        self.assertEqual(measure["Measure"]["Expression"]["SourceRef"]["Source"], "a")
        self.assertEqual(measure["Name"], "Orders.Profit Ratio")
        self.assertEqual(measure["NativeReferenceName"], "Profit Ratio")
        self.assertNotIn("Aggregation", measure)

    def test_projection_query_ref_equals_select_name(self):
        sv, query, _ = self._visual(category="Orders[Region]",
                                    value="Orders[[Profit Ratio]]")
        self.assertEqual(sv["projections"]["Y"], [{"queryRef": "Orders.Profit Ratio"}])
        self.assertEqual(query["Select"][1]["Name"], "Orders.Profit Ratio")

    def test_order_by_targets_the_measure(self):
        _, query, _ = self._visual(category="Orders[Region]",
                                   value="Orders[[Profit Ratio]]")
        expr = query["OrderBy"][0]["Expression"]
        self.assertIn("Measure", expr)
        self.assertNotIn("Aggregation", expr)
        self.assertEqual(expr["Measure"]["Property"], "Profit Ratio")

    def test_plain_column_in_value_role_is_still_summed(self):
        sv, query, _ = self._visual(category="Orders[Region]", value="Orders[Sales]")
        self.assertIn("Aggregation", query["Select"][1])
        self.assertEqual(sv["projections"]["Y"], [{"queryRef": "Sum(Orders.Sales)"}])

    def test_selection_metadata_uses_measure_name(self):
        _, _, transforms = self._visual(value="Orders[[Profit Ratio]]")
        selection = transforms["selectionMetadata"]["selections"][0]
        self.assertEqual(selection["queryName"], "Orders.Profit Ratio")
        self.assertEqual(selection["displayName"], "Profit Ratio")

    def test_measure_can_live_in_a_different_table_from_the_category(self):
        _, query, _ = self._visual(category="Customers[Segment]",
                                   value="Metrics[[Total Sales]]")
        entities = {f["Entity"] for f in query["From"]}
        self.assertEqual(entities, {"Customers", "Metrics"})

    def test_auto_title_mentions_the_measure(self):
        vc = add_visual("card", {"value": "Orders[[Profit Ratio]]"}, vid=2)
        title = json.loads(vc["config"])["singleVisual"]["vcObjects"]["title"][0] \
            ["properties"]["text"]["expr"]["Literal"]["Value"]
        self.assertIn("Profit Ratio", title)

    def test_query_ref_equals_select_name_for_every_kind_and_visual(self):
        """A mismatch renders a blank visual, so guard it everywhere."""
        cases = {
            "bar": {"category": "T[C]", "value": "T[V]"},
            "bar ": {"category": "T[C]", "value": "T[[M]]"},
            "donut": {"category": "T[C]", "value": "T[[M]]"},
            "card": {"value": "T[[M]]"},
            "table": {"value": "T[C]"},
            "matrix": {"row": "T[C]", "value": "T[[M]]"},
            "slicer": {"field": "T[C]"},
            " table": {"value": ["T[C]", "Sum(T[V])", "Avg(T[V])", "Count(T[V])", "T[[M]]"]},
            "  matrix": {"row": "T[C]", "column": "T[D]", "value": ["T[V]", "Sum(T[W])"]},
        }
        for vtype, bindings in cases.items():
            with self.subTest(vtype=vtype.strip(), bindings=bindings):
                vc = add_visual(vtype.strip(), bindings, vid=1, title="t")
                sv = json.loads(vc["config"])["singleVisual"]
                names = {sel["Name"] for sel in json.loads(vc["query"])["Select"]}
                refs = {p["queryRef"] for plist in sv["projections"].values()
                        for p in plist}
                self.assertEqual(refs, names)


class ParseBindingTest(unittest.TestCase):

    def test_plain_column(self):
        self.assertEqual(parse_binding("Orders[Region]"),
                         {"table": "Orders", "name": "Region", "measure": False, "function": None})

    def test_explicit_aggregations(self):
        for text, function in (("Sum(Orders[Sales])", "sum"), ("AVG(Orders[Sales])", "avg"),
                               ("Average(Orders[Sales])", "average"), ("Count(Orders[Sales])", "count")):
            with self.subTest(text=text):
                parsed = parse_binding(text)
                self.assertEqual((parsed["table"], parsed["name"], parsed["function"]),
                                 ("Orders", "Sales", function))

    def test_measure(self):
        self.assertTrue(parse_binding("Orders[[Profit Ratio]]")["measure"])

    def test_aggregating_a_measure_is_an_error_that_says_what_to_do(self):
        with self.assertRaises(ValueError) as ctx:
            parse_binding("Sum(Orders[[Profit Ratio]])")
        self.assertIn("already aggregated", str(ctx.exception))

    def test_unknown_function_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            parse_binding("Median(Orders[Sales])")


class ColumnRolesTest(unittest.TestCase):
    """Slicers and tables list columns; only value axes are aggregated."""

    def _query(self, vtype, bindings):
        vc = add_visual(vtype, bindings, vid=1, title="t")
        return (json.loads(vc["query"]),
                json.loads(vc["config"])["singleVisual"]["projections"])

    def test_slicer_is_a_plain_column_never_summed(self):
        query, projections = self._query("slicer", {"field": "Orders[Region]"})
        self.assertEqual(query["Select"][0]["Name"], "Orders.Region")
        self.assertNotIn("Aggregation", query["Select"][0])
        self.assertNotIn("OrderBy", query)
        self.assertEqual(projections["Values"][0]["queryRef"], "Orders.Region")

    def test_every_slicer_flavour_is_plain(self):
        for vtype in ("slicer", "text_slicer", "list_slicer", "advanced_slicer"):
            with self.subTest(vtype=vtype):
                query, _ = self._query(vtype, {"field": "Orders[Region]"})
                self.assertNotIn("Aggregation", query["Select"][0])

    def test_table_takes_a_list_of_fields_in_order(self):
        query, projections = self._query("table", {"value": [
            "Orders[Region]", "Orders[Category]", "Sum(Orders[Sales])", "Avg(Orders[Discount])"]})
        self.assertEqual([s["Name"] for s in query["Select"]],
                         ["Orders.Region", "Orders.Category", "Sum(Orders.Sales)",
                          "Avg(Orders.Discount)"])
        self.assertEqual([p["queryRef"] for p in projections["Values"]],
                         [s["Name"] for s in query["Select"]])

    def test_table_plain_columns_are_not_aggregated_but_marked_fields_are(self):
        query, _ = self._query("table", {"value": ["Orders[Region]", "Sum(Orders[Sales])"]})
        self.assertNotIn("Aggregation", query["Select"][0])
        self.assertEqual(query["Select"][1]["Aggregation"]["Function"], 0)
        self.assertEqual(len(query["OrderBy"]), 1)  # only the aggregated field sorts

    def test_average_and_count_use_their_function_codes(self):
        query, _ = self._query("table", {"value": ["Avg(Orders[Discount])",
                                                   "Count(Orders[Order ID])"]})
        self.assertEqual(query["Select"][0]["Aggregation"]["Function"], 1)
        self.assertEqual(query["Select"][1]["Aggregation"]["Function"], 5)
        self.assertEqual(query["Select"][1]["Name"], "CountNonNull(Orders.Order ID)")

    def test_matrix_groups_by_plain_rows_and_columns_and_sums_values(self):
        query, projections = self._query("matrix", {
            "row": "Orders[Region]", "column": "Orders[Category]",
            "value": ["Orders[Sales]", "Sum(Orders[Profit])"]})
        names = [s["Name"] for s in query["Select"]]
        self.assertEqual(names, ["Orders.Region", "Orders.Category",
                                 "Sum(Orders.Sales)", "Sum(Orders.Profit)"])
        self.assertEqual(set(projections), {"Rows", "Columns", "Values"})

    def test_card_still_sums_a_bare_numeric_column(self):
        query, _ = self._query("card", {"value": "Orders[Sales]"})
        self.assertEqual(query["Select"][0]["Name"], "Sum(Orders.Sales)")

    def test_explicit_average_on_a_chart_axis(self):
        query, projections = self._query("bar", {"category": "Orders[Region]",
                                                  "value": "Avg(Orders[Discount])"})
        self.assertEqual(projections["Y"][0]["queryRef"], "Avg(Orders.Discount)")
        self.assertEqual(query["OrderBy"][0]["Expression"]["Aggregation"]["Function"], 1)

    def test_measures_can_mix_into_a_table(self):
        query, _ = self._query("table", {"value": ["Orders[Region]", "Orders[[Profit Ratio]]"]})
        self.assertIn("Measure", query["Select"][1])


class AddVisualTest(unittest.TestCase):

    def test_single_table_category_value(self):
        vc = add_visual("bar", {"category": "Orders[Region]", "value": "Orders[Sales]"},
                         x=20, y=60, w=600, h=290, vid=1, title="Sales by Region")
        self.assertEqual(vc["id"], 1)
        self.assertEqual(vc["position"], {"x": 20, "y": 60, "z": 0,
                                           "width": 600, "height": 290, "tabOrder": 0})

        config = json.loads(vc["config"])
        sv = config["singleVisual"]
        self.assertEqual(sv["visualType"], "barChart")
        self.assertEqual(sv["vcObjects"]["title"][0]["properties"]["text"]["expr"]
                          ["Literal"]["Value"], "'Sales by Region'")

        query = json.loads(vc["query"])
        self.assertEqual(query["Version"], 2)
        self.assertEqual(len(query["From"]), 1)
        self.assertEqual(query["From"][0]["Entity"], "Orders")
        self.assertEqual(len(query["Select"]), 2)

        # Category is a plain column, value is aggregated (Y is a measure role)
        by_name = {s["Name"]: s for s in query["Select"]}
        self.assertIn("Orders.Region", by_name)
        self.assertNotIn("Aggregation", by_name["Orders.Region"])
        self.assertIn("Sum(Orders.Sales)", by_name)
        self.assertIn("Aggregation", by_name["Sum(Orders.Sales)"])

        # Only the aggregated field gets an OrderBy entry
        self.assertEqual(len(query.get("OrderBy", [])), 1)

        # projections keyed by PBIR role name
        self.assertIn("Category", sv["projections"])
        self.assertIn("Y", sv["projections"])

    def test_multi_table_bindings_get_distinct_source_aliases(self):
        vc = add_visual("scatter", {
            "x": "Products[Price]",
            "y": "Products[Quantity]",
            "detail": "Customers[Name]",
        }, vid=2)
        query = json.loads(vc["query"])
        sources = {f["Name"]: f["Entity"] for f in query["From"]}
        self.assertEqual(len(sources), 2)
        self.assertEqual(set(sources.values()), {"Products", "Customers"})
        # aliases are single letters assigned in first-seen order: a, b
        self.assertEqual(sorted(sources.keys()), ["a", "b"])

    def test_title_auto_generated_when_omitted(self):
        vc = add_visual("card", {"value": "Sales[Revenue]"}, vid=3)
        config = json.loads(vc["config"])
        title_text = config["singleVisual"]["vcObjects"]["title"][0]["properties"]["text"] \
            ["expr"]["Literal"]["Value"]
        self.assertEqual(title_text, "'Total Revenue'")

    def test_no_title_block_when_title_is_empty_string(self):
        vc = add_visual("textbox", {}, vid=4, title="")
        config = json.loads(vc["config"])
        self.assertEqual(config["singleVisual"]["vcObjects"], {})

    def test_default_size_used_when_omitted(self):
        vc = add_visual("card", {"value": "Sales[Revenue]"}, vid=5)
        self.assertEqual((vc["position"]["width"], vc["position"]["height"]), (200, 120))

    def test_show_labels_flag_reaches_formatting_objects(self):
        vc_off = add_visual("bar", {"category": "T[C]", "value": "T[V]"}, vid=6)
        vc_on = add_visual("bar", {"category": "T[C]", "value": "T[V]"}, vid=7, show_labels=True)
        off_show = json.loads(vc_off["config"])["singleVisual"]["objects"]["labels"][0] \
            ["properties"]["show"]["expr"]["Literal"]["Value"]
        on_show = json.loads(vc_on["config"])["singleVisual"]["objects"]["labels"][0] \
            ["properties"]["show"]["expr"]["Literal"]["Value"]
        self.assertEqual(off_show, "false")
        self.assertEqual(on_show, "true")

    def test_unknown_visual_type_raises(self):
        with self.assertRaises(ValueError):
            add_visual("not_a_type", {}, vid=8)


class AddTitleTest(unittest.TestCase):

    def test_defaults_span_full_width(self):
        vc = add_title("My Dashboard")
        self.assertEqual(vc["position"]["width"], 1280)
        self.assertEqual(vc["id"], 9000)
        config = json.loads(vc["config"])
        self.assertEqual(config["singleVisual"]["visualType"], "textbox")
        run = config["singleVisual"]["objects"]["general"][0]["properties"] \
            ["paragraphs"][0]["textRuns"][0]
        self.assertEqual(run["value"], "My Dashboard")
        self.assertEqual(run["textStyle"]["fontWeight"], "bold")

    def test_custom_vid_and_font_size(self):
        vc = add_title("Page 2", vid=9001, font_size=28)
        self.assertEqual(vc["id"], 9001)
        config = json.loads(vc["config"])
        run = config["singleVisual"]["objects"]["general"][0]["properties"] \
            ["paragraphs"][0]["textRuns"][0]
        self.assertEqual(run["textStyle"]["fontSize"], "28px")


class LayoutRoundTripTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def test_write_then_read_round_trips_utf16_and_non_ascii(self):
        layout = {
            "sections": [{
                "displayName": "Résumé — 概要",
                "visualContainers": [add_visual("card", {"value": "T[V]"}, vid=1,
                                                title="Café Sales €")],
            }]
        }
        layout_path = os.path.join(self.tmp, "layout.bin")
        write_layout(layout, layout_path)

        with open(layout_path, "rb") as f:
            raw = f.read()
        # UTF-16 LE, no BOM, and every character takes >= 2 bytes
        raw.decode("utf-16-le")  # must not raise
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8")

        pbix_path = os.path.join(self.tmp, "fake.pbix")
        with zipfile.ZipFile(pbix_path, "w") as z:
            z.write(layout_path, "Report/Layout")

        round_tripped = read_layout(pbix_path)
        self.assertEqual(round_tripped, layout)
        self.assertEqual(round_tripped["sections"][0]["displayName"], "Résumé — 概要")


if __name__ == "__main__":
    unittest.main()
