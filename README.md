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

Edit **`visuals_config.py`** only. Use `make_visual()` with these parameters:

```python
make_visual(
    vid        = 1,                      # unique integer id on the page
    tab_order  = 0,                      # z/tab order (0 = first)
    x=20, y=60, w=600, h=290,           # position and size in pixels
    visual_type = "clusteredColumnChart",
    table       = table,
    projections = {
        "Category": [{"queryRef": f"{table}.Category", "active": True}],
        "Y":        [{"queryRef": f"Sum({table}.Sales)"}]
    },
    selects = [
        col_select("Category", f"{table}.Category"),
        agg_select("Sales",    f"Sum({table}.Sales)")
    ],
    selections = [
        sel(f"{table}.Category",   "Category",     data_type=1, role_kind=1, roles=["Category"]),
        sel(f"Sum({table}.Sales)", "Sum of Sales", data_type=2, role_kind=2, roles=["Y"])
    ],
    order_by = order_by_agg("Sales", direction=2)
)
```

### Supported visual types

| `visual_type` | Description |
|---|---|
| `clusteredColumnChart` | Vertical bar chart |
| `clusteredBarChart` | Horizontal bar chart |
| `lineChart` | Line chart |
| `areaChart` | Area chart |
| `donutChart` | Donut chart |
| `pieChart` | Pie chart |
| `card` | Single-value card |
| `multiRowCard` | Multi-row card |
| `tableEx` | Table |
| `matrix` | Matrix |
| `slicerVisual` | Slicer |

### Role names by visual type

| Visual | Axis/Category role | Value role | Legend role |
|---|---|---|---|
| Column / Bar / Line / Area | `Category` | `Y` | `Series` |
| Donut / Pie | `Category` | `Y` | — |
| Card | — | `Values` | — |
| Table | — | `Values` | — |
| Matrix | `Rows`, `Columns` | `Values` | — |

### data_type values

| Value | Type |
|---|---|
| `1` | Text / Category |
| `2` | Decimal / Number |
| `4` | DateTime |

### Aggregation functions (agg_select `func` parameter)

| Value | Function |
|---|---|
| `0` | Sum |
| `1` | Average |
| `2` | Min |
| `3` | Max |
| `4` | Count |

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
