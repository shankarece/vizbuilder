"""
Superstore executive dashboard (demo).

Two pages built only from visuals that are safe on Power BI Report Server:
cards, slicers, column / bar / donut charts, a table and a matrix. Every
position sits on the 10 px grid, nothing overlaps, and every visual has a title.

Use it as it is, or copy it and change the names below:

    build.bat "C:\\work\\Demo.pbix" "C:\\work\\Demo-Out.pbix" --config demo\\superstore_dashboard.py --open

It expects the usual Superstore table called Orders. If your columns are named
differently, change only the block below.
"""
from layout_builder import add_visual

# ── Change these if your model uses different names ──────────────────────────
TABLE = "Orders"
SALES, PROFIT, QUANTITY, DISCOUNT = "Sales", "Profit", "Quantity", "Discount"
CATEGORY, SUB_CATEGORY = "Category", "Sub-Category"
REGION, SEGMENT, CUSTOMER = "Region", "Segment", "Customer Name"

# Optional: a measure that exists in your model (for example "Profit Ratio").
# When set, it replaces the "Average discount" card. Leave as None to skip.
MARGIN_MEASURE = None


def col(name):
    """A plain column: Orders[Region]."""
    return f"{TABLE}[{name}]"


def total(name):
    """A column summed: Sum(Orders[Sales])."""
    return f"Sum({TABLE}[{name}])"


def build_pages():
    if MARGIN_MEASURE:
        fourth_card = add_visual("card", {"value": f"{TABLE}[[{MARGIN_MEASURE}]]"},
                                 x=650, y=60, w=200, h=100, vid=4, title=MARGIN_MEASURE)
    else:
        fourth_card = add_visual("card", {"value": f"Avg({TABLE}[{DISCOUNT}])"},
                                 x=650, y=60, w=200, h=100, vid=4, title="Average discount")

    executive = [
        add_visual("card", {"value": col(SALES)}, x=20, y=60, w=200, h=100, vid=1,
                   title="Total sales"),
        add_visual("card", {"value": col(PROFIT)}, x=230, y=60, w=200, h=100, vid=2,
                   title="Total profit"),
        add_visual("card", {"value": col(QUANTITY)}, x=440, y=60, w=200, h=100, vid=3,
                   title="Units sold"),
        fourth_card,
        add_visual("slicer", {"field": col(REGION)}, x=20, y=180, w=150, h=220, vid=5,
                   title="Region"),
        add_visual("slicer", {"field": col(SEGMENT)}, x=20, y=420, w=150, h=220, vid=6,
                   title="Segment"),
        add_visual("clustered_column", {"category": col(CATEGORY), "value": col(SALES)},
                   x=190, y=180, w=380, h=220, vid=7, title="Sales by category"),
        add_visual("donut", {"category": col(SEGMENT), "value": col(SALES)},
                   x=590, y=180, w=240, h=220, vid=8, title="Sales by segment"),
        add_visual("clustered_bar", {"category": col(SUB_CATEGORY), "value": col(PROFIT)},
                   x=190, y=420, w=380, h=220, vid=9, title="Profit by sub-category"),
        add_visual("table", {"value": [col(REGION), col(CATEGORY),
                                       total(SALES), total(PROFIT)]},
                   x=590, y=420, w=240, h=220, vid=10, title="Sales and profit by region"),
    ]

    detail = [
        add_visual("matrix", {"row": col(REGION), "column": col(CATEGORY),
                              "value": [total(SALES), total(PROFIT)]},
                   x=20, y=60, w=400, h=300, vid=1, title="Region by category"),
        add_visual("bar", {"category": col(REGION), "value": col(SALES)},
                   x=440, y=60, w=400, h=300, vid=2, title="Sales by region"),
        add_visual("table", {"value": [col(CUSTOMER), col(SEGMENT),
                                       total(SALES), total(PROFIT)]},
                   x=20, y=380, w=820, h=280, vid=3, title="Customer detail"),
    ]

    return [
        {"name": "Executive Summary", "title": "Superstore - Executive Summary",
         "visuals": executive},
        {"name": "Region and Product Detail", "title": "Superstore - Region and Product Detail",
         "visuals": detail},
    ]
