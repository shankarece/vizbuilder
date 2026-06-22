"""
visual_types.py
---------------
Visual type metadata ported from pbi-cli's visual_backend.py and pbir_models.py.
Defines supported types, data roles, friendly aliases, default sizes, and
measure/column role classification.

You should NOT need to edit this file.
"""

# ── Supported visual types ────────────────────────────────────────────────────

SUPPORTED_VISUAL_TYPES = frozenset({
    "barChart", "lineChart", "card", "tableEx", "pivotTable",
    "slicer", "kpi", "gauge", "donutChart", "columnChart",
    "areaChart", "ribbonChart", "waterfallChart", "scatterChart",
    "funnelChart", "multiRowCard", "treemap", "cardNew",
    "stackedBarChart", "lineStackedColumnComboChart",
    "clusteredColumnChart", "clusteredBarChart",
    "cardVisual", "textbox", "shape", "image", "actionButton",
    "textSlicer", "listSlicer", "advancedSlicerVisual",
    "pageNavigator", "azureMap",
})

# ── Friendly aliases → canonical type names ───────────────────────────────────

VISUAL_TYPE_ALIASES = {
    "bar": "barChart",
    "bar_chart": "barChart",
    "line": "lineChart",
    "line_chart": "lineChart",
    "column": "columnChart",
    "column_chart": "columnChart",
    "clustered_column": "clusteredColumnChart",
    "clustered_column_chart": "clusteredColumnChart",
    "clustered_bar": "clusteredBarChart",
    "clustered_bar_chart": "clusteredBarChart",
    "stacked_bar": "stackedBarChart",
    "stacked_bar_chart": "stackedBarChart",
    "area": "areaChart",
    "area_chart": "areaChart",
    "ribbon": "ribbonChart",
    "ribbon_chart": "ribbonChart",
    "waterfall": "waterfallChart",
    "waterfall_chart": "waterfallChart",
    "scatter": "scatterChart",
    "scatter_chart": "scatterChart",
    "funnel": "funnelChart",
    "funnel_chart": "funnelChart",
    "donut": "donutChart",
    "donut_chart": "donutChart",
    "pie": "donutChart",
    "combo": "lineStackedColumnComboChart",
    "combo_chart": "lineStackedColumnComboChart",
    "table": "tableEx",
    "matrix": "pivotTable",
    "multi_row_card": "multiRowCard",
    "card_new": "cardNew",
    "new_card": "cardNew",
    "modern_card": "cardVisual",
    "card_visual": "cardVisual",
    "text_slicer": "textSlicer",
    "list_slicer": "listSlicer",
    "advanced_slicer": "advancedSlicerVisual",
    "tile_slicer": "advancedSlicerVisual",
    "button": "actionButton",
    "action_button": "actionButton",
    "text_box": "textbox",
    "img": "image",
    "page_navigator": "pageNavigator",
    "page_nav": "pageNavigator",
    "map": "azureMap",
    "azure_map": "azureMap",
}

# ── Data roles per visual type ────────────────────────────────────────────────
# Keys are the PBIR role names used in queryState / projections

VISUAL_DATA_ROLES = {
    "barChart":                     ["Category", "Y", "Legend"],
    "lineChart":                    ["Category", "Y", "Legend"],
    "columnChart":                  ["Category", "Y", "Legend"],
    "clusteredColumnChart":         ["Category", "Y", "Legend"],
    "clusteredBarChart":            ["Category", "Y", "Legend"],
    "stackedBarChart":              ["Category", "Y", "Legend"],
    "areaChart":                    ["Category", "Y", "Legend"],
    "ribbonChart":                  ["Category", "Y", "Legend"],
    "donutChart":                   ["Category", "Y", "Legend"],
    "waterfallChart":               ["Category", "Y", "Breakdown"],
    "funnelChart":                  ["Category", "Y"],
    "scatterChart":                 ["Details", "X", "Y", "Size", "Legend"],
    "lineStackedColumnComboChart":  ["Category", "ColumnY", "LineY", "Legend"],
    "treemap":                      ["Category", "Values"],
    "card":                         ["Values"],
    "cardNew":                      ["Fields"],
    "cardVisual":                   ["Data"],
    "multiRowCard":                 ["Values"],
    "tableEx":                      ["Values"],
    "pivotTable":                   ["Rows", "Values", "Columns"],
    "slicer":                       ["Values"],
    "textSlicer":                   ["Values"],
    "listSlicer":                   ["Values"],
    "advancedSlicerVisual":         ["Values"],
    "kpi":                          ["Indicator", "Goal", "TrendLine"],
    "gauge":                        ["Y", "MaxValue"],
    "azureMap":                     ["Category", "Size"],
    "actionButton":                 [],
    "textbox":                      [],
    "shape":                        [],
    "image":                        [],
    "pageNavigator":                [],
}

# ── Role aliases: user-friendly names → PBIR role names ───────────────────────
# Allows binding with --category, --value, --legend etc.

ROLE_ALIASES = {
    "barChart":                     {"category": "Category", "value": "Y", "legend": "Legend"},
    "lineChart":                    {"category": "Category", "value": "Y", "legend": "Legend"},
    "columnChart":                  {"category": "Category", "value": "Y", "legend": "Legend"},
    "clusteredColumnChart":         {"category": "Category", "value": "Y", "legend": "Legend"},
    "clusteredBarChart":            {"category": "Category", "value": "Y", "legend": "Legend"},
    "stackedBarChart":              {"category": "Category", "value": "Y", "legend": "Legend"},
    "areaChart":                    {"category": "Category", "value": "Y", "legend": "Legend"},
    "ribbonChart":                  {"category": "Category", "value": "Y", "legend": "Legend"},
    "donutChart":                   {"category": "Category", "value": "Y", "legend": "Legend"},
    "waterfallChart":               {"category": "Category", "value": "Y", "breakdown": "Breakdown"},
    "funnelChart":                  {"category": "Category", "value": "Y"},
    "scatterChart":                 {"x": "X", "y": "Y", "detail": "Details", "size": "Size", "legend": "Legend", "value": "Y"},
    "lineStackedColumnComboChart":  {"category": "Category", "column": "ColumnY", "line": "LineY", "legend": "Legend", "value": "ColumnY"},
    "treemap":                      {"category": "Category", "value": "Values"},
    "card":                         {"field": "Values", "value": "Values"},
    "cardNew":                      {"field": "Fields", "value": "Fields"},
    "cardVisual":                   {"field": "Data", "value": "Data"},
    "multiRowCard":                 {"field": "Values", "value": "Values"},
    "tableEx":                      {"value": "Values", "column": "Values"},
    "pivotTable":                   {"row": "Rows", "value": "Values", "column": "Columns"},
    "slicer":                       {"value": "Values", "field": "Values"},
    "textSlicer":                   {"value": "Values", "field": "Values"},
    "listSlicer":                   {"value": "Values", "field": "Values"},
    "advancedSlicerVisual":         {"value": "Values", "field": "Values"},
    "kpi":                          {"indicator": "Indicator", "value": "Indicator", "goal": "Goal", "trend_line": "TrendLine", "trend": "TrendLine"},
    "gauge":                        {"value": "Y", "max": "MaxValue", "max_value": "MaxValue", "target": "MaxValue"},
    "azureMap":                     {"category": "Category", "value": "Size", "size": "Size"},
    "actionButton": {}, "textbox": {}, "shape": {}, "image": {}, "pageNavigator": {},
}

# ── Roles that default to measures (aggregated) vs columns (grouping) ─────────

MEASURE_ROLES = frozenset({
    "Y", "Values", "Fields", "Indicator", "Goal",
    "ColumnY", "LineY", "X", "Size", "Data", "MaxValue",
})

# ── Default visual dimensions (width, height) ────────────────────────────────

DEFAULT_SIZES = {
    "barChart":                     (400, 300),
    "lineChart":                    (400, 300),
    "columnChart":                  (400, 300),
    "clusteredColumnChart":         (400, 300),
    "clusteredBarChart":            (400, 300),
    "stackedBarChart":              (400, 300),
    "areaChart":                    (400, 300),
    "ribbonChart":                  (400, 300),
    "donutChart":                   (350, 300),
    "waterfallChart":               (450, 300),
    "funnelChart":                  (350, 300),
    "scatterChart":                 (400, 350),
    "lineStackedColumnComboChart":  (500, 300),
    "treemap":                      (400, 300),
    "card":                         (200, 120),
    "cardNew":                      (200, 120),
    "cardVisual":                   (217, 87),
    "multiRowCard":                 (300, 200),
    "tableEx":                      (500, 350),
    "pivotTable":                   (500, 350),
    "slicer":                       (200, 300),
    "textSlicer":                   (200, 50),
    "listSlicer":                   (200, 300),
    "advancedSlicerVisual":         (280, 280),
    "kpi":                          (250, 150),
    "gauge":                        (300, 250),
    "azureMap":                     (500, 400),
    "actionButton":                 (51, 22),
    "textbox":                      (300, 100),
    "shape":                        (300, 200),
    "image":                        (200, 150),
    "pageNavigator":                (120, 400),
}


def resolve_visual_type(user_type: str) -> str:
    """Resolve a user-provided type name to the canonical PBIR visualType."""
    if user_type in SUPPORTED_VISUAL_TYPES:
        return user_type
    resolved = VISUAL_TYPE_ALIASES.get(user_type)
    if resolved:
        return resolved
    raise ValueError(
        f"Unknown visual type: '{user_type}'. "
        f"Use one of: {', '.join(sorted(SUPPORTED_VISUAL_TYPES))} "
        f"or an alias like: bar, line, column, donut, pie, table, matrix, combo, etc."
    )
