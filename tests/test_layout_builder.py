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
