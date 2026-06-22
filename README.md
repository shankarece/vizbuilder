# pbix-visual-builder

Add visuals to Power BI Report Server (PBRS) `.pbix` files programmatically
using Python — no Power BI Service, no premium licence, no external packages.

Compatible with **September 2024**, **May 2025**, and later versions of PBI Desktop.

---

## How It Works

PBRS `.pbix` files are ZIP archives containing:
- `Report/Layout` — UTF-16 LE JSON defining all pages and visuals
- `DataModel` — Analysis Services binary (the data model)
- `SecurityBindings` — DPAPI-encrypted integrity hash

**The problem**: `SecurityBindings` hashes the file contents. Any external
change — even 1 byte — causes `MashupValidationError` on open.

**The solution**:
1. Strip `SecurityBindings` from the PBIX
2. Inject the modified `Report/Layout` with new visuals
3. Open in regular PBI Desktop → **File → Save** regenerates `SecurityBindings`

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.8+ | No pip installs — standard library only |
| Regular PBI Desktop | Match your PBRS version | Opens result and regenerates SecurityBindings |
| PBRS Desktop | Any | To verify and deploy final file |

> **Important**: use the **same monthly release** for both regular Desktop and
> PBRS Desktop (e.g. both September 2024 or both May 2025). Mismatched versions
> can cause "unrecognized version" errors.

---

## Installation

No packages to install. Just clone and run.

```bash
git clone https://github.com/<your-org>/pbix-visual-builder.git
cd pbix-visual-builder
python build.py MyReport.pbix MyReport-WithVisuals.pbix
```

---

## Files

| File | Purpose | Edit? |
|---|---|---|
| `visuals_config.py` | Define your visuals and table name | **YES — edit this** |
| `build.py` | End-to-end entry point | No |
| `layout_builder.py` | Layout read/write engine and query builders | No |
| `visual_types.py` | 32 visual types, data roles, aliases (ported from pbi-cli) | No |
| `pbix_patch.py` | PBIX zip manipulation | No |
| `requirements.txt` | Dependency list (empty — stdlib only) | No |

---

## Usage

### Step 1 — Prepare the PBIX

Open your `.pbix` in **regular PBI Desktop**, load your data, and **File → Save**.
This ensures the data model is populated before we add visuals.

### Step 2 — Configure your visuals

Edit `visuals_config.py`:

```python
TABLE     = "Orders"          # must match table name in your data model
PAGE_NAME = "Sales Overview"  # page display name
```

Then define your visuals in `build_visuals()`.

### Step 3 — Build

```bash
python build.py MyReport.pbix MyReport-WithVisuals.pbix
```

Output:
```
============================================================
  PBIX Visual Builder
============================================================
  Input:  MyReport.pbix
  Output: MyReport-WithVisuals.pbix

Step 1/2  Building layout with visuals...
  Page:    Sales Overview
  Visuals: 3

Step 2/2  Patching PBIX...
  Removed:  SecurityBindings
  Replaced: Report/Layout  (12,628 bytes)
  Copied:   DataModel
  ...

  Done!
  Next steps:
  1. Open the output PBIX in regular PBI Desktop
  2. Verify visuals look correct
  3. File -> Save  (regenerates SecurityBindings)
  4. Deploy to Power BI Report Server
============================================================
```

### Step 4 — Save and deploy

Open `MyReport-WithVisuals.pbix` in **regular PBI Desktop** → verify visuals →
**File → Save** → deploy the saved file to Report Server.

---

## Adding Visuals

Edit **`visuals_config.py`** only. Uses pbi-cli's `Table[Column]` binding syntax:

```python
# Simple — just specify type and bindings
add_visual("bar", bindings={
    "category": "Orders[Region]",
    "value":    "Orders[Sales]",
})

# With position and size
add_visual("clustered_column", bindings={
    "category": "Orders[Category]",
    "value":    "Orders[Sales]",
    "legend":   "Orders[Segment]",
}, x=20, y=60, w=600, h=290, vid=1, tab_order=0)

# Combo chart (column + line)
add_visual("combo", bindings={
    "category": "Sales[Month]",
    "column":   "Sales[Revenue]",
    "line":     "Sales[Profit]",
})

# Scatter chart
add_visual("scatter", bindings={
    "x":      "Products[Price]",
    "y":      "Products[Quantity]",
    "detail": "Products[Name]",
    "size":   "Products[Revenue]",
})

# KPI
add_visual("kpi", bindings={
    "indicator": "Sales[Actual]",
    "goal":      "Sales[Target]",
    "trend":     "Sales[Date]",
})
```

### Supported visual types (32 types, ported from pbi-cli)

| Alias | Canonical name | Description |
|---|---|---|
| `bar` | `barChart` | Horizontal bar chart |
| `line` | `lineChart` | Line chart |
| `column` | `columnChart` | Vertical bar chart |
| `clustered_column` | `clusteredColumnChart` | Clustered column chart |
| `clustered_bar` | `clusteredBarChart` | Clustered bar chart |
| `stacked_bar` | `stackedBarChart` | Stacked bar chart |
| `area` | `areaChart` | Area chart |
| `ribbon` | `ribbonChart` | Ribbon chart |
| `donut` / `pie` | `donutChart` | Donut chart |
| `combo` | `lineStackedColumnComboChart` | Combo (column + line) |
| `waterfall` | `waterfallChart` | Waterfall chart |
| `funnel` | `funnelChart` | Funnel chart |
| `scatter` | `scatterChart` | Scatter chart |
| `treemap` | `treemap` | Treemap |
| `card` | `card` | Single-value card |
| `new_card` | `cardNew` | New card visual |
| `modern_card` | `cardVisual` | Modern card visual |
| `multi_row_card` | `multiRowCard` | Multi-row card |
| `table` | `tableEx` | Table |
| `matrix` | `pivotTable` | Matrix |
| `slicer` | `slicer` | Slicer |
| `kpi` | `kpi` | KPI |
| `gauge` | `gauge` | Gauge |
| `map` | `azureMap` | Azure Map |

### Binding roles by visual type

| Visual | Roles (use friendly names) |
|---|---|
| Bar / Column / Line / Area / Ribbon / Stacked / Clustered | `category`, `value`, `legend` |
| Donut / Pie | `category`, `value`, `legend` |
| Combo | `category`, `column`, `line`, `legend` |
| Scatter | `x`, `y`, `detail`, `size`, `legend` |
| Waterfall | `category`, `value`, `breakdown` |
| Funnel | `category`, `value` |
| Treemap | `category`, `value` |
| Card / Multi-row / New card | `value` or `field` |
| Table | `value` or `column` |
| Matrix | `row`, `value`, `column` |
| KPI | `indicator` / `value`, `goal`, `trend` / `trend_line` |
| Gauge | `value`, `max` / `target` |
| Map | `category`, `size` |

---

## Workflow Summary

```
PBRS .pbix
  └─► regular Desktop: Get Data → load → File→Save → Close
  └─► python build.py input.pbix output.pbix
  └─► regular Desktop: open output → verify → File→Save
  └─► deploy .pbix to Power BI Report Server
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `MashupValidationError` | SecurityBindings not removed | Ensure you're opening the *output* file, not the input |
| Visuals show "Can't display visual" | Table or column name mismatch | Check `TABLE` in `visuals_config.py` matches data model exactly |
| "Unrecognized version" on PBRS | Version mismatch between Desktop versions | Use same monthly release for regular and PBRS Desktop |
| `FileNotFoundError` on input | Wrong path | Use full absolute path or run from the same folder as the PBIX |
