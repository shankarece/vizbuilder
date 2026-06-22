"""
visuals_config.py
-----------------
THIS IS THE ONLY FILE YOU NEED TO EDIT to customise your report.

Uses pbi-cli's Table[Column] syntax for field binding. Example:

    add_visual("bar", bindings={
        "category": "Orders[Region]",
        "value":    "Orders[Sales]",
    })

That's it — the engine handles the legacy PBIX query/projection/selection
boilerplate automatically.

Canvas size: 1280 x 720 pixels.

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

from layout_builder import add_visual

# ── Configuration ─────────────────────────────────────────────────────────────

PAGE_NAME = "Sales Overview"


# ── Visuals ───────────────────────────────────────────────────────────────────

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
    ))

    # ── 3. Card — Total Sales ────────────────────────────────────────────────
    visuals.append(add_visual(
        "card",
        bindings={
            "value": "Orders[Sales]",
        },
        x=660, y=390, w=300, h=120,
        vid=3, tab_order=2,
    ))

    # ── Add more visuals below ───────────────────────────────────────────────

    # Line Chart — Sales over time
    # visuals.append(add_visual(
    #     "line",
    #     bindings={
    #         "category": "Orders[Order Date]",
    #         "value":    "Orders[Sales]",
    #     },
    #     x=20, y=390, w=600, h=290,
    #     vid=4, tab_order=3,
    # ))

    # Table — detailed data
    # visuals.append(add_visual(
    #     "table",
    #     bindings={
    #         "value": "Orders[Customer Name]",
    #         # Add more value bindings by using PBIR role names:
    #         # "Values": "Orders[Sales]",  # second column
    #     },
    #     x=20, y=390, w=600, h=290,
    #     vid=5, tab_order=4,
    # ))

    # Combo Chart — columns + line
    # visuals.append(add_visual(
    #     "combo",
    #     bindings={
    #         "category": "Orders[Category]",
    #         "column":   "Orders[Sales]",
    #         "line":     "Orders[Quantity]",
    #     },
    #     x=20, y=390, w=600, h=290,
    #     vid=6, tab_order=5,
    # ))

    # Scatter Chart
    # visuals.append(add_visual(
    #     "scatter",
    #     bindings={
    #         "x":      "Orders[Sales]",
    #         "y":      "Orders[Quantity]",
    #         "detail": "Orders[Category]",
    #     },
    #     x=20, y=390, w=600, h=290,
    #     vid=7, tab_order=6,
    # ))

    return visuals
