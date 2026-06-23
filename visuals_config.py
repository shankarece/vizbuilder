"""
visuals_config.py
-----------------
THIS IS THE ONLY FILE YOU NEED TO EDIT to customise your report.

Uses pbi-cli's Table[Column] syntax for field binding. Example:

    add_visual("bar", bindings={
        "category": "Orders[Region]",
        "value":    "Orders[Sales]",
    }, title="Sales by Region")

Canvas size: 1280 x 720 pixels.

MULTI-PAGE SUPPORT
------------------
Option A — Single page (simple):
    Set PAGE_NAME, DASHBOARD_TITLE, and define build_visuals().

Option B — Multiple pages:
    Define build_pages() → list of {"name": ..., "title": ..., "visuals": [...]}.
    When build_pages() exists, it takes priority over build_visuals().

Supported visual types (use either the canonical name or any alias):
    bar / barChart                    Horizontal bar chart
    line / lineChart                  Line chart
    column / columnChart              Vertical bar chart
    clustered_column                  Clustered column chart
    clustered_bar                     Clustered bar chart
    stacked_bar                       Stacked bar chart
    area / areaChart                  Area chart
    donut / pie / donutChart          Donut chart
    combo / lineStackedColumnComboChart   Combo (column + line)
    waterfall / waterfallChart        Waterfall chart
    funnel / funnelChart              Funnel chart
    scatter / scatterChart            Scatter chart
    treemap                           Treemap
    ribbon / ribbonChart              Ribbon chart
    card                              Single-value card
    new_card / cardNew                New card visual
    modern_card / cardVisual          Modern card visual
    multi_row_card / multiRowCard     Multi-row card
    table / tableEx                   Table
    matrix / pivotTable               Matrix
    slicer                            Slicer
    kpi                               KPI
    gauge                             Gauge
    map / azureMap                    Azure Map

Binding roles (use friendly names — they map automatically):
    Most charts:    category, value, legend
    Combo chart:    category, column, line, legend
    Scatter chart:  x, y, detail, size, legend
    Card / Table:   value / field
    Matrix:         row, value, column
    KPI:            indicator / value, goal, trend_line
    Gauge:          value, max / target
    Treemap:        category, value
    Waterfall:      category, value, breakdown
"""

from layout_builder import add_visual, add_title

# ── Configuration ─────────────────────────────────────────────────────────────

PAGE_NAME       = "Sales Overview"
DASHBOARD_TITLE = "Sales Dashboard"


# ── Single-page visuals ─────────────────────────────────────────────────────

def build_visuals() -> list:
    """Define all visuals for the page. Returns a list of visualContainers."""

    visuals = []

    # ── 1. Clustered Column Chart — Sales by Category ────────────────────────
    visuals.append(add_visual(
        "clustered_column",
        bindings={
            "category": "Orders[Category]",
            "value":    "Orders[Sales]",
        },
        x=20, y=60, w=600, h=290,
        vid=1, tab_order=0,
        title="Sales by Category",
    ))

    # ── 2. Donut Chart — Sales by Segment ────────────────────────────────────
    visuals.append(add_visual(
        "donut",
        bindings={
            "category": "Orders[Segment]",
            "value":    "Orders[Sales]",
        },
        x=660, y=60, w=300, h=290,
        vid=2, tab_order=1,
        title="Sales by Segment",
    ))

    # ── 3. Card — Total Sales ────────────────────────────────────────────────
    visuals.append(add_visual(
        "card",
        bindings={
            "value": "Orders[Sales]",
        },
        x=660, y=390, w=300, h=120,
        vid=3, tab_order=2,
        title="Total Sales",
    ))

    return visuals


# ── Multi-page example (uncomment to use) ────────────────────────────────────
#
# def build_pages() -> list:
#     """Define multiple pages. Each page has a name, title, and visuals list."""
#     return [
#         {
#             "name": "Sales Overview",
#             "title": "Sales Dashboard",
#             "visuals": [
#                 add_visual("clustered_column", bindings={
#                     "category": "Orders[Category]",
#                     "value":    "Orders[Sales]",
#                 }, x=20, y=60, w=600, h=290, vid=1, title="Sales by Category"),
#
#                 add_visual("donut", bindings={
#                     "category": "Orders[Segment]",
#                     "value":    "Orders[Sales]",
#                 }, x=660, y=60, w=300, h=290, vid=2, title="Sales by Segment"),
#
#                 add_visual("card", bindings={
#                     "value": "Orders[Sales]",
#                 }, x=660, y=390, w=300, h=120, vid=3, title="Total Sales"),
#             ],
#         },
#         {
#             "name": "Regional Analysis",
#             "title": "Regional Performance",
#             "visuals": [
#                 add_visual("bar", bindings={
#                     "category": "Orders[Region]",
#                     "value":    "Orders[Sales]",
#                 }, x=20, y=60, w=600, h=290, vid=1, title="Sales by Region"),
#
#                 add_visual("table", bindings={
#                     "value": "Orders[Customer Name]",
#                 }, x=20, y=390, w=940, h=280, vid=2, title="Customer Details"),
#             ],
#         },
#     ]
