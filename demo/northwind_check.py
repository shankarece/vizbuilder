"""
Verification file for the sample Northwind model (demo/northwind_sample.pbix).

Open the built file in Power BI Desktop for Report Server and look at each page.
The point is to learn, on YOUR Desktop version, which visuals draw correctly:

  Page 1  visuals believed to be safe: cards, a measure card, slicer, charts,
          table and matrix.
  Page 2  A/B pairs for legends and the combo chart: "A" is what vizbuilder
          writes today, "B" uses the role names two other tools use.
  Page 3  KPI, gauge, scatter (A/B), waterfall and funnel.

Build it:
    build.bat demo\\verify\\northwind_sample.pbix Northwind-check.pbix --config demo\\northwind_check.py --open

Then follow demo\\VERIFY_IN_DESKTOP.md and report what you see.
"""
from layout_builder import add_visual

REV, QTY = "Orders[Revenue]", "Orders[Quantity]"


def _grid(index, columns=3, x0=20, y0=60, w=400, h=300, gap_x=20, gap_y=20):
    """Position of the index-th tile in a grid, on the 10 px grid."""
    return dict(x=x0 + (index % columns) * (w + gap_x),
                y=y0 + (index // columns) * (h + gap_y), w=w, h=h)


def build_pages():
    safe = [
        add_visual("card", {"value": REV}, x=20, y=60, w=400, h=100, vid=1,
                   title="Card: revenue (summed column)"),
        add_visual("card", {"value": "Orders[[Avg Order Value]]"}, x=440, y=60, w=400, h=100,
                   vid=2, title="Card: Avg Order Value (a model MEASURE)"),
        add_visual("card", {"value": "Orders[[Order Count]]"}, x=860, y=60, w=400, h=100,
                   vid=3, title="Card: Order Count (a model MEASURE)"),
        add_visual("clustered_column", {"category": "Categories[CategoryName]", "value": REV},
                   x=20, y=180, w=400, h=250, vid=4, title="Column: revenue by category"),
        add_visual("donut", {"category": "Customers[Segment]", "value": REV},
                   x=440, y=180, w=400, h=250, vid=5, title="Donut: revenue by segment"),
        add_visual("clustered_bar", {"category": "Products[ProductName]", "value": REV},
                   x=860, y=180, w=400, h=250, vid=6, title="Bar: revenue by product"),
        add_visual("table", {"value": ["Customers[CustomerName]", "Customers[Segment]",
                                       "Sum(Orders[Revenue])", "Orders[[Order Count]]"]},
                   x=20, y=450, w=400, h=250, vid=7, title="Table: text columns + sum + measure"),
        add_visual("matrix", {"row": "Regions[RegionName]", "column": "Customers[Segment]",
                              "value": ["Sum(Orders[Revenue])"]},
                   x=440, y=450, w=400, h=250, vid=8, title="Matrix: region by segment"),
        add_visual("slicer", {"field": "Regions[RegionName]"}, x=860, y=450, w=400, h=250,
                   vid=9, title="Slicer: region (click a value)"),
    ]

    legend = [
        add_visual("clustered_column", {"category": "Regions[RegionName]", "value": REV,
                                        "legend": "Customers[Segment]"},
                   vid=1, title="A  column, legend role = 'Legend' (current)", **_grid(0)),
        add_visual("clustered_column", {"category": "Regions[RegionName]", "value": REV,
                                        "Series": "Customers[Segment]"},
                   vid=2, title="B  column, legend role = 'Series'", **_grid(1)),
        add_visual("stacked_bar", {"category": "Regions[RegionName]", "value": REV,
                                   "Series": "Customers[Segment]"},
                   vid=3, title="B  stacked bar, role = 'Series'", **_grid(2)),
        add_visual("combo", {"category": "Categories[CategoryName]", "column": REV,
                             "line": QTY},
                   vid=4, title="A  combo, roles ColumnY + LineY (current)", **_grid(3)),
        add_visual("combo", {"category": "Categories[CategoryName]", "Y": "Sum(Orders[Revenue])",
                             "Y2": "Sum(Orders[Quantity])"},
                   vid=5, title="B  combo, roles Y + Y2", **_grid(4)),
        add_visual("line", {"category": "Categories[CategoryName]", "value": REV,
                            "Series": "Customers[Segment]"},
                   vid=6, title="B  line, role = 'Series' (one line per segment)", **_grid(5)),
    ]

    others = [
        add_visual("kpi", {"indicator": REV, "goal": QTY},
                   vid=1, title="KPI  indicator + goal", **_grid(0)),
        add_visual("gauge", {"value": REV, "max": QTY},
                   vid=2, title="GAUGE  value + max", **_grid(1)),
        add_visual("scatter", {"x": REV, "y": QTY, "detail": "Products[ProductName]"},
                   vid=3, title="A  scatter, dots by role 'Details' (current)", **_grid(2)),
        add_visual("scatter", {"x": REV, "y": QTY, "Category": "Products[ProductName]"},
                   vid=4, title="B  scatter, dots by role 'Category'", **_grid(3)),
        add_visual("waterfall", {"category": "Categories[CategoryName]", "value": REV},
                   vid=5, title="WATERFALL  revenue by category", **_grid(4)),
        add_visual("funnel", {"category": "Regions[RegionName]", "value": REV},
                   vid=6, title="FUNNEL  revenue by region", **_grid(5)),
    ]

    return [
        {"name": "1 Safe visuals", "title": "Page 1: visuals believed safe", "visuals": safe},
        {"name": "2 Legend and combo", "title": "Page 2: A/B - which version draws a legend / a line?",
         "visuals": legend},
        {"name": "3 KPI gauge scatter", "title": "Page 3: KPI, gauge, scatter A/B, waterfall, funnel",
         "visuals": others},
    ]
