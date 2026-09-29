---
name: VizBuilder Visuals
description: >
  Add, configure, and bind data to visuals in PBRS .pbix reports by editing
  visuals_config.py for vizbuilder. Invoke this skill whenever the user
  mentions "add a chart", "bar chart", "column chart", "line chart", "donut",
  "pie", "card", "KPI", "gauge", "scatter", "table visual", "matrix",
  "slicer", "combo chart", "waterfall", "funnel", "treemap", "map", "bind
  data", "bind field", "visual type", "data labels", "visual title", or wants
  to place, resize, or remove any visual on a report. Also invoke when the
  user asks what visual types are supported or which binding roles to use.
tools: vizbuilder
---

# VizBuilder Visuals Skill

Visuals are defined in `visuals_config.py` with `add_visual()` and written into
the PBIX by `build.py`. No Power BI Desktop connection is needed.

## Editing Rules

1. **Never create a new file** — always edit the existing `visuals_config.py`.
2. **Append, don't replace** — when adding to an existing page, add to the
   existing `build_visuals()` list or the right page in `build_pages()`.
3. **Always set `title=`** on every visual.
4. **`vid` must be unique per page** — check existing vids before adding.
5. Rebuild after every change: `build.bat input.pbix output.pbix --open`.

## add_visual()

```python
from layout_builder import add_visual

add_visual(
    "clustered_column",            # alias or canonical PBIR type
    bindings={                     # friendly role -> "Table[Column]"
        "category": "Orders[Category]",
        "value":    "Orders[Sales]",
        "legend":   "Orders[Segment]",
    },
    x=20, y=60,                    # position in px (canvas is 1280 x 720)
    w=600, h=290,                  # size in px (defaults per type if omitted)
    vid=1,                         # unique id on the page
    tab_order=0,                   # z-order
    title="Sales by Category",     # auto-generated if omitted
    show_labels=False,             # data labels (always on for cards/donuts)
)
```

## Prerequisite: Fields Must Exist in the Data Model

Bindings are written straight into the layout JSON. vizbuilder does **not**
check the data model, so a typo only shows up in Desktop as
"Can't display visual".

- Table and column names must match the model **exactly** (case and spaces):
  `"Fact_Sales"` ≠ `"fact_sales"`, `"Total Revenue"` ≠ `"Total_Revenue"`.
- List the real names first:
  `python analyze.py input.pbix --metadata-only` and read `datamodel.tables`
  in the `*_metadata.json` output (see vizbuilder-analysis). If that list is
  empty (the model is stored only as binary), copy names from the Data pane
  in Desktop, or reuse the bindings already in `field_references`.

## Binding Syntax (what to write in `bindings`)

| Write | Means | Use for |
|---|---|---|
| `"Orders[Region]"` | A column. On a value axis (`value`, `column`, `line`, `x`, `y`, `size`, `indicator`, `goal`, `max`) it is **summed**; elsewhere it is a plain column. | Categories, rows, legends, cards of numeric columns |
| `"Sum(Orders[Sales])"`, `"Avg(Orders[Discount])"`, `"Count(Orders[Order ID])"` | A column with an explicit aggregation | Numeric columns in tables; averages; counts |
| `"Orders[[Profit Ratio]]"` | A **measure defined in the model**, used as the model defines it | Ratios, YTD, anything with real DAX |
| `["Orders[Region]", "Sum(Orders[Sales])"]` | A **list** of fields in one role, in order | Table columns, several matrix values |

Rules of thumb:

- **Slicers and tables list plain columns** (never summed). In a table, mark
  numeric fields yourself: `Sum(...)`, `Avg(...)`, or a `[[Measure]]`.
- **Matrix:** `row` and `column` are plain, `value` is summed (or a list of
  `Sum(...)` / `[[Measure]]`).
- A measure is already aggregated: do not wrap it (`Sum(Orders[[X]])` is an error).
- Use `Table[[Measure]]` only for names that exist as **measures** in the model;
  use `Table[Column]` for columns. The tool cannot check which is which.

## Confirmed and Unconfirmed Visuals

Visuals whose data roles are the same in every source we checked (use these
first): `card`, `slicer`, `clustered_column`, `clustered_bar`, `bar`, `column`,
`line` (without legend), `donut`, `table`, `matrix`.

**Unconfirmed on Report Server Desktop** - the role names vizbuilder writes may
not match the classic layout, so these may draw without their legend, line or
dots: a `legend` on any chart, `combo`, `kpi`, `gauge`, `scatter`, `waterfall`, `funnel`.
`demo/VERIFY_IN_DESKTOP.md` tests them side by side. Until that is done, prefer
the confirmed list, and if a chart needs grouping, say so in your reply.

## Binding Examples

```python
# Bar / column / line / area: category + value (+ legend)
add_visual("bar", bindings={
    "category": "Geo[Region]",
    "value":    "Sales[Revenue]",
}, vid=1, title="Revenue by Region")

# Combo: category + column series + line series
add_visual("combo", bindings={
    "category": "Calendar[Month]",
    "column":   "Sales[Revenue]",
    "line":     "Sales[Margin]",
}, vid=2, title="Revenue vs Margin")

# Scatter: x, y, detail (+ size, legend)
add_visual("scatter", bindings={
    "x":      "Sales[Quantity]",
    "y":      "Sales[Revenue]",
    "detail": "Product[Name]",
}, vid=3, title="Quantity vs Revenue")

# Matrix: rows + values (+ columns)
add_visual("matrix", bindings={
    "row":    "Product[Category]",
    "value":  "Sales[Amount]",
    "column": "Calendar[Year]",
}, vid=4, title="Sales by Category and Year")

# KPI: indicator + goal + trend axis
add_visual("kpi", bindings={
    "indicator": "Sales[Revenue]",
    "goal":      "Sales[Target]",
    "trend":     "Calendar[Date]",
}, vid=5, title="Revenue vs Target")

# Gauge: value + max/target
add_visual("gauge", bindings={
    "value": "Sales[Revenue]",
    "max":   "Sales[Target]",
}, vid=6, title="Target Attainment")

# Card: single value
add_visual("card", bindings={"value": "Sales[Revenue]"},
           vid=7, title="Total Revenue")

# Card on a model measure (ratio, YTD, ...)
add_visual("card", bindings={"value": "Sales[[Profit Ratio]]"},
           vid=8, title="Profit Ratio")

# Slicer: plain column, never summed
add_visual("slicer", bindings={"field": "Geo[Region]"},
           vid=9, title="Region")

# Table: text columns plain, numbers aggregated explicitly
add_visual("table", bindings={"value": [
    "Geo[Region]", "Product[Category]", "Sum(Sales[Revenue])", "Sales[[Order Count]]"]},
    vid=10, title="Sales by region and category")
```

Each role takes one field or a list of fields.

## Supported Visual Types (32)

### Charts

| Alias | PBIR type | Roles |
|---|---|---|
| `bar` | barChart | category, value, legend |
| `column` | columnChart | category, value, legend |
| `clustered_bar` | clusteredBarChart | category, value, legend |
| `clustered_column` | clusteredColumnChart | category, value, legend |
| `stacked_bar` | stackedBarChart | category, value, legend |
| `line` | lineChart | category, value, legend |
| `area` | areaChart | category, value, legend |
| `ribbon` | ribbonChart | category, value, legend |
| `donut` / `pie` | donutChart | category, value, legend |
| `combo` | lineStackedColumnComboChart | category, column, line, legend |
| `waterfall` | waterfallChart | category, value, breakdown |
| `funnel` | funnelChart | category, value |
| `scatter` | scatterChart | x, y, detail, size, legend |
| `treemap` | treemap | category, value |

### Cards and KPIs

| Alias | PBIR type | Roles |
|---|---|---|
| `card` | card | value / field |
| `new_card` / `card_new` | cardNew | value / field |
| `modern_card` / `card_visual` | cardVisual | value / field |
| `multi_row_card` | multiRowCard | value / field |
| `kpi` | kpi | indicator / value, goal, trend / trend_line |
| `gauge` | gauge | value, max / target |

### Tables

| Alias | PBIR type | Roles |
|---|---|---|
| `table` | tableEx | value / column |
| `matrix` | pivotTable | row, value, column |

### Slicers

| Alias | PBIR type | Roles |
|---|---|---|
| `slicer` | slicer | value / field |
| `text_slicer` | textSlicer | value / field |
| `list_slicer` | listSlicer | value / field |
| `advanced_slicer` / `tile_slicer` | advancedSlicerVisual | value / field |

### Maps

| Alias | PBIR type | Roles |
|---|---|---|
| `map` / `azure_map` | azureMap | category, size |

### Decorative and Navigation (no bindings)

`textbox` / `text_box`, `shape`, `image` / `img`, `button` / `action_button`,
`page_navigator` / `page_nav` — pass `bindings={}`.

## Report Server Compatibility

Power BI Desktop for Report Server has no preview features and ships a few
releases a year. `build.py` warns when a config uses a type that may be missing
from the user's PBRS release. When building for Report Server, prefer the
safer choice:

| Type | Why | Use instead |
|---|---|---|
| `map` / `azure_map` | Azure Maps needs online Azure services | `table` or `bar` |
| `new_card`, `modern_card` | New card may be missing | `card` or `multi_row_card` |
| `text_slicer`, `list_slicer`, `advanced_slicer` | Newer slicers may be missing | `slicer` |
| `page_navigator` | Missing in older releases | `button` |

Only use these when the user confirms their PBRS Desktop release shows them.

## Default Sizes

Omitting `w`/`h` uses a per-type default from `visual_types.DEFAULT_SIZES`
(e.g. card 200×120, KPI 250×150, gauge 300×250, charts 400×300).

## Formatting (auto-applied)

| Feature | Charts | Cards | Donut |
|---|---|---|---|
| Title | from `title=` or auto-generated | same | same |
| Axis titles | enabled | — | — |
| Legend | shown (right) | — | — |
| Data labels | `show_labels=True` | always on | category + % |

## Removing or Moving Visuals

Delete the `add_visual(...)` call (or change its `x`, `y`, `w`, `h`) in
`visuals_config.py` and rebuild. To adjust positions of an already-built file
without touching the config, use the vizbuilder-layout skill (`lint.bat --fix`).

## Workflow: Add a Chart

```cmd
REM 1. Confirm field names
python analyze.py input.pbix --metadata-only --output analysis\

REM 2. Append add_visual(...) to visuals_config.py with a unique vid and title

REM 3. Build and open
build.bat input.pbix output.pbix --open

REM 4. Check the layout
lint.bat output.pbix
```
