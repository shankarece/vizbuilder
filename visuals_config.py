"""
visuals_config.py
-----------------
THIS IS THE ONLY FILE YOU NEED TO EDIT to customise your report.

Define:
  - TABLE      : the data model table name (must match what PBI Desktop loaded)
  - PAGE_NAME  : display name for the first page
  - build_visuals() : add/remove/edit visuals here

Canvas size is 1280 x 720 pixels by default.

Supported visual_type values:
    clusteredColumnChart   Vertical bar chart
    clusteredBarChart      Horizontal bar chart
    lineChart              Line chart
    areaChart              Area chart
    donutChart             Donut chart
    pieChart               Pie chart
    card                   Single-value card
    multiRowCard           Multi-row card
    tableEx                Table
    matrix                 Matrix
    slicerVisual           Slicer

Role names by visual type:
    clusteredColumnChart / clusteredBarChart / lineChart / areaChart:
        Category (axis)   Y (values)   Series (legend)

    donutChart / pieChart:
        Category          Y

    card / multiRowCard:
        Values

    tableEx / matrix:
        Values            Rows (matrix only)   Columns (matrix only)

data_type values for sel():
    1 = Text / Category
    2 = Decimal / Number
    4 = DateTime

role_kind values for sel():
    1 = Grouping  (axis, legend, category fields)
    2 = Measure   (value / aggregation fields)
"""

from layout_builder import (
    make_visual, col_select, agg_select, order_by_agg, sel
)

# ── Configuration ─────────────────────────────────────────────────────────────

TABLE     = "Orders"       # Must match the table name in your data model
PAGE_NAME = "Sales Overview"


# ── Visuals ───────────────────────────────────────────────────────────────────

def build_visuals(table: str = TABLE) -> list:
    """
    Define all visuals for Page 1.
    Each call to make_visual() adds one chart/card to the page.

    Canvas is 1280 x 720 px.
    Visual positions: x (left), y (top), w (width), h (height) — all in pixels.
    Leave ~40px at top for the page title area.
    """
    visuals = []

    # ── Visual 1: Clustered Column Chart — Sales by Category ─────────────────
    # Position: left half, top row  (x=20, y=60, w=600, h=290)
    visuals.append(make_visual(
        vid=1, tab_order=0,
        x=20, y=60, w=600, h=290,
        visual_type="clusteredColumnChart",
        table=table,
        projections={
            "Category": [{"queryRef": f"{table}.Category", "active": True}],
            "Y":        [{"queryRef": f"Sum({table}.Sales)"}]
        },
        selects=[
            col_select("Category", f"{table}.Category"),
            agg_select("Sales",    f"Sum({table}.Sales)")
        ],
        selections=[
            sel(f"{table}.Category",   "Category",     data_type=1, role_kind=1, roles=["Category"]),
            sel(f"Sum({table}.Sales)", "Sum of Sales", data_type=2, role_kind=2, roles=["Y"])
        ],
        order_by=order_by_agg("Sales", direction=2)
    ))

    # ── Visual 2: Donut Chart — Sales by Segment ─────────────────────────────
    # Position: right half, top row  (x=660, y=60, w=300, h=290)
    visuals.append(make_visual(
        vid=2, tab_order=1,
        x=660, y=60, w=300, h=290,
        visual_type="donutChart",
        table=table,
        projections={
            "Category": [{"queryRef": f"{table}.Segment", "active": True}],
            "Y":        [{"queryRef": f"Sum({table}.Sales)"}]
        },
        selects=[
            col_select("Segment", f"{table}.Segment"),
            agg_select("Sales",   f"Sum({table}.Sales)")
        ],
        selections=[
            sel(f"{table}.Segment",    "Segment",      data_type=1, role_kind=1, roles=["Category"]),
            sel(f"Sum({table}.Sales)", "Sum of Sales", data_type=2, role_kind=2, roles=["Y"])
        ],
        order_by=order_by_agg("Sales", direction=2)
    ))

    # ── Visual 3: Card — Total Sales ─────────────────────────────────────────
    # Position: right half, bottom row  (x=660, y=390, w=300, h=120)
    visuals.append(make_visual(
        vid=3, tab_order=2,
        x=660, y=390, w=300, h=120,
        visual_type="card",
        table=table,
        projections={
            "Values": [{"queryRef": f"Sum({table}.Sales)", "active": True}]
        },
        selects=[
            agg_select("Sales", f"Sum({table}.Sales)")
        ],
        selections=[
            sel(f"Sum({table}.Sales)", "Sum of Sales", data_type=2, role_kind=2, roles=["Values"])
        ]
    ))

    # ── Add more visuals below this line ─────────────────────────────────────
    # Example — Line Chart: Sales over time
    #
    # visuals.append(make_visual(
    #     vid=4, tab_order=3,
    #     x=20, y=390, w=600, h=290,
    #     visual_type="lineChart",
    #     table=table,
    #     projections={
    #         "Category": [{"queryRef": f"{table}.Order Date", "active": True}],
    #         "Y":        [{"queryRef": f"Sum({table}.Sales)"}]
    #     },
    #     selects=[
    #         col_select("Order Date", f"{table}.Order Date"),
    #         agg_select("Sales",      f"Sum({table}.Sales)")
    #     ],
    #     selections=[
    #         sel(f"{table}.Order Date", "Order Date",   data_type=4, role_kind=1, roles=["Category"]),
    #         sel(f"Sum({table}.Sales)", "Sum of Sales", data_type=2, role_kind=2, roles=["Y"])
    #     ],
    #     order_by=order_by_agg("Sales", direction=1)
    # ))

    return visuals
