---
name: VizBuilder (PBRS Visuals)
description: >
  Add visuals to Power BI Report Server (PBRS) .pbix files using vizbuilder.
  Invoke this skill whenever the user mentions "add a chart to PBIX",
  "PBRS visual", "bar chart", "line chart", "card", "KPI", "gauge", "scatter",
  "table visual", "matrix", "slicer", "combo chart", "create dashboard",
  "vizbuilder", "pbix visual", or wants to add visuals to a PBRS report.
---

# VizBuilder — PBRS Visual Builder Skill

Add visuals to Power BI Report Server `.pbix` files programmatically.
Works offline — no Desktop connection needed, no PBIR/PBIP format required.

## How It Works

1. Edit `visuals_config.py` to define visuals
2. Run `python build.py input.pbix output.pbix`
3. Open output in regular Desktop → File → Save → deploy to PBRS

## Project Location

The vizbuilder scripts are in the repo root (or cloned from
`https://github.com/shankarece/vizbuilder`). Key files:

- `visuals_config.py` — **the only file to edit** (defines visuals)
- `build.py` — entry point
- `layout_builder.py` — engine (do not edit)
- `visual_types.py` — 32 visual type definitions (do not edit)
- `pbix_patch.py` — PBIX zip manipulation (do not edit)

## Adding Visuals

Edit `visuals_config.py`. Use the `add_visual()` function with
`Table[Column]` binding syntax:

```python
from layout_builder import add_visual

PAGE_NAME = "Sales Overview"

def build_visuals() -> list:
    visuals = []

    # Bar chart with title
    visuals.append(add_visual("bar", bindings={
        "category": "Sales[Region]",
        "value":    "Sales[Revenue]",
    }, title="Revenue by Region", x=20, y=60, w=600, h=290, vid=1))

    # Donut chart
    visuals.append(add_visual("donut", bindings={
        "category": "Sales[Segment]",
        "value":    "Sales[Revenue]",
    }, title="Revenue by Segment", x=660, y=60, w=300, h=290, vid=2))

    # Card — total value
    visuals.append(add_visual("card", bindings={
        "value": "Sales[Revenue]",
    }, title="Total Revenue", x=660, y=390, w=300, h=120, vid=3))

    # Line chart with data labels
    visuals.append(add_visual("line", bindings={
        "category": "Sales[Month]",
        "value":    "Sales[Revenue]",
    }, title="Monthly Trend", show_labels=True, vid=4))

    # Combo chart (columns + line)
    visuals.append(add_visual("combo", bindings={
        "category": "Sales[Month]",
        "column":   "Sales[Revenue]",
        "line":     "Sales[Profit]",
    }, title="Revenue vs Profit", vid=5))

    # Scatter
    visuals.append(add_visual("scatter", bindings={
        "x":      "Products[Price]",
        "y":      "Products[Quantity]",
        "detail": "Products[Name]",
    }, title="Price vs Quantity", vid=6))

    # KPI
    visuals.append(add_visual("kpi", bindings={
        "indicator": "Sales[Actual]",
        "goal":      "Sales[Target]",
        "trend":     "Sales[Date]",
    }, title="Sales KPI", vid=7))

    # Table
    visuals.append(add_visual("table", bindings={
        "value": "Orders[Customer Name]",
    }, title="Customer List", vid=8))

    # Matrix
    visuals.append(add_visual("matrix", bindings={
        "row":    "Products[Category]",
        "value":  "Sales[Revenue]",
        "column": "Sales[Year]",
    }, title="Revenue Matrix", vid=9))

    # Slicer
    visuals.append(add_visual("slicer", bindings={
        "value": "Orders[Region]",
    }, vid=10))

    return visuals
```

## add_visual() Parameters

```
add_visual(
    visual_type,      # "bar", "line", "donut", "card", "combo", etc.
    bindings={...},   # role → "Table[Column]" mappings
    x=50, y=50,       # position (pixels, canvas is 1280×720)
    w=400, h=300,     # size (pixels, auto-defaults per type)
    vid=1,            # unique visual id
    tab_order=0,      # z-order
    title="My Title", # visual title (auto-generated if omitted)
    show_labels=False, # show data point labels
)
```

## Supported Visual Types (32)

### Charts
| Alias | Roles |
|---|---|
| `bar`, `column`, `clustered_column`, `clustered_bar`, `stacked_bar` | category, value, legend |
| `line`, `area`, `ribbon` | category, value, legend |
| `donut` / `pie` | category, value, legend |
| `combo` | category, column, line, legend |
| `waterfall` | category, value, breakdown |
| `funnel` | category, value |
| `scatter` | x, y, detail, size, legend |
| `treemap` | category, value |

### Cards & KPIs
| Alias | Roles |
|---|---|
| `card`, `new_card`, `modern_card`, `multi_row_card` | value / field |
| `kpi` | indicator, goal, trend |
| `gauge` | value, max / target |

### Tables
| Alias | Roles |
|---|---|
| `table` | value |
| `matrix` | row, value, column |

### Slicers
| Alias | Roles |
|---|---|
| `slicer`, `text_slicer`, `list_slicer` | value / field |

### Other
| Alias | Roles |
|---|---|
| `map` | category, size |
| `textbox`, `shape`, `image`, `button`, `page_navigator` | (none) |

## Formatting

Visuals automatically get:
- **Title** (from `title=` param or auto-generated from bindings)
- **Axis titles** enabled for charts with axes
- **Legend** shown for charts that support it
- **Data labels** on donut charts (category + percentage)

Set `show_labels=True` to enable data labels on bar/line/column charts.

## Running

```bash
python build.py input.pbix output.pbix
```

Then open `output.pbix` in regular Power BI Desktop → verify → File → Save →
deploy to PBRS.

## Important Notes

- Table and column names in bindings must match the data model exactly
- Canvas size is 1280×720 pixels — position visuals within this grid
- `vid` must be unique per visual on the page
- The tool strips `SecurityBindings` — you MUST open in Desktop and
  File → Save before deploying to PBRS
- Works with September 2024 and May 2025 PBRS Desktop versions
- No pip installs needed — Python standard library only
