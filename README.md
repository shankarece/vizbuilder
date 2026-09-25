# pbix-visual-builder

Add visuals to Power BI Report Server (PBRS) `.pbix` files programmatically
using Python — no Power BI Service, no premium licence, no external packages.

Works with **Power BI Desktop for Report Server** (recommended) and regular
PBI Desktop — September 2024, May 2025, and later releases.

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
3. Open in Power BI Desktop for Report Server (or regular Desktop) → **File → Save** regenerates `SecurityBindings`

Everything else in the file (`DataModel`, `Version`, settings) is copied
byte-for-byte, so a file saved by PBRS Desktop stays a PBRS Desktop file.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.8+ | No pip installs — standard library only |
| Power BI Desktop for Report Server | Same release as your Report Server | **Recommended.** Prepares the input, opens the result, regenerates SecurityBindings |
| Regular PBI Desktop | Same monthly release as PBRS Desktop | Optional alternative |

> **Recommended: do everything in Power BI Desktop for Report Server.** A file
> saved there always matches your server. If you use regular Desktop, it must be
> the **same monthly release** as your PBRS Desktop (e.g. both September 2024 or
> both May 2025), or the server shows "unrecognized version".

### Visual types to check on Report Server

PBRS Desktop has no preview features and ships a few releases a year, so some
newer visuals may be missing from your release. `build.py` prints a
**PBRS Desktop compatibility warning** when you use one of these:

| Visual | Safer choice |
|---|---|
| `map` / `azure_map` (Azure Maps) | `table` or `bar` |
| `new_card`, `modern_card` | `card` or `multi_row_card` |
| `text_slicer`, `list_slicer`, `advanced_slicer` | `slicer` |
| `page_navigator` | `button` |

---

## Installation

No packages to install. Just clone and run. **No PowerShell needed — works with CMD.**

```cmd
git clone https://github.com/shankarece/vizbuilder.git
cd vizbuilder

REM Build and auto-open (uses Power BI Desktop for Report Server when installed)
build.bat MyReport.pbix MyReport-WithVisuals.pbix --open

REM Force a specific Desktop edition
build.bat MyReport.pbix MyReport-WithVisuals.pbix --open --rs
build.bat MyReport.pbix MyReport-WithVisuals.pbix --open --regular

REM Or without auto-open
python build.py MyReport.pbix MyReport-WithVisuals.pbix
```

### Install Windsurf / Claude Code skills (optional)

```cmd
python install_skill.py
```

Then use natural language prompts in Windsurf to create visuals.

---

## Files

| File | Purpose | Edit? |
|---|---|---|
| `visuals_config.py` | Define your visuals and table name | **YES — edit this** |
| `build.py` | End-to-end entry point | No |
| `build.bat` | CMD launcher (no PowerShell needed) | No |
| `layout_builder.py` | Layout read/write engine and query builders | No |
| `visual_types.py` | 32 visual types, data roles, aliases (ported from pbi-cli) | No |
| `pbix_patch.py` | PBIX zip manipulation | No |
| `desktop.py` | Finds/opens Power BI Desktop (Report Server edition first) for `--open` | No |
| `install_skill.py` | Install / list / uninstall Claude Code / Windsurf skills | Run once |
| `skills/*/SKILL.md` | 8 task-focused Claude Code skills | No |
| `tests/test_skills.py` | Skill frontmatter, trigger, and installer tests | No |
| `tests/test_pbrs.py` | PBRS Desktop compatibility tests (synthetic PBIX build) | No |
| `requirements.txt` | Dependency list (empty — stdlib only) | No |

---

## Usage

### Step 1 — Prepare the PBIX

Open your `.pbix` in **Power BI Desktop for Report Server**, load your data, and **File → Save**.
This ensures the data model is populated before we add visuals.

### Step 2 — Configure your visuals

Edit `visuals_config.py`:

```python
PAGE_NAME       = "Sales Overview"     # page tab name
DASHBOARD_TITLE = "Sales Dashboard"    # large title at top of page
```

Then define your visuals in `build_visuals()`.

For multiple pages/tabs, define `build_pages()` instead — see [Multi-Page](#multi-page-dashboards) below.

### Step 3 — Build

```cmd
build.bat MyReport.pbix MyReport-WithVisuals.pbix --open
```

The `--open` flag auto-launches the output in Power BI Desktop.
Without `--open`:

```cmd
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
  1. Open the output PBIX in Power BI Desktop for Report Server
     (or regular Desktop from the same monthly release)
  2. Verify visuals look correct
  3. File -> Save  (regenerates SecurityBindings)
  4. Deploy to Power BI Report Server
============================================================
```

### Step 4 — Save and deploy

Open `MyReport-WithVisuals.pbix` in **Power BI Desktop for Report Server** → verify visuals →
**File → Save** → deploy the saved file to Report Server.

---

## Adding Visuals

Edit **`visuals_config.py`** only. Uses pbi-cli's `Table[Column]` binding syntax:

```python
# Bar chart with title
add_visual("bar", bindings={
    "category": "Orders[Region]",
    "value":    "Orders[Sales]",
}, title="Sales by Region")

# Clustered column with position, size, and legend
add_visual("clustered_column", bindings={
    "category": "Orders[Category]",
    "value":    "Orders[Sales]",
    "legend":   "Orders[Segment]",
}, x=20, y=60, w=600, h=290, vid=1, title="Sales by Category & Segment")

# Combo chart (column + line)
add_visual("combo", bindings={
    "category": "Sales[Month]",
    "column":   "Sales[Revenue]",
    "line":     "Sales[Profit]",
}, title="Revenue vs Profit")

# Scatter chart
add_visual("scatter", bindings={
    "x":      "Products[Price]",
    "y":      "Products[Quantity]",
    "detail": "Products[Name]",
    "size":   "Products[Revenue]",
}, title="Price vs Quantity")

# KPI
add_visual("kpi", bindings={
    "indicator": "Sales[Actual]",
    "goal":      "Sales[Target]",
    "trend":     "Sales[Date]",
}, title="Sales Performance")

# Card with data labels
add_visual("card", bindings={
    "value": "Sales[Revenue]",
}, title="Total Revenue")

# Line chart with data labels enabled
add_visual("line", bindings={
    "category": "Sales[Month]",
    "value":    "Sales[Revenue]",
}, title="Monthly Trend", show_labels=True)
```

### Formatting (auto-applied)

| Feature | Charts | Cards | Donut |
|---|---|---|---|
| **Title** | from `title=` or auto-generated | from `title=` or auto-generated | from `title=` or auto-generated |
| **Axis titles** | enabled | — | — |
| **Legend** | shown (right) | — | — |
| **Data labels** | via `show_labels=True` | always on | category + % |

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

## Multi-Page Dashboards

To create multiple tabs/pages, define `build_pages()` in `visuals_config.py`:

```python
from layout_builder import add_visual, add_title

def build_pages() -> list:
    return [
        {
            "name": "Sales Overview",
            "title": "Sales Dashboard",    # page title banner
            "visuals": [
                add_visual("clustered_column", bindings={
                    "category": "Orders[Category]",
                    "value":    "Orders[Sales]",
                }, x=20, y=60, w=600, h=290, vid=1, title="Sales by Category"),

                add_visual("card", bindings={
                    "value": "Orders[Sales]",
                }, x=660, y=60, w=300, h=120, vid=2, title="Total Sales"),
            ],
        },
        {
            "name": "Regional Analysis",
            "title": "Regional Performance",
            "visuals": [
                add_visual("bar", bindings={
                    "category": "Orders[Region]",
                    "value":    "Orders[Sales]",
                }, x=20, y=60, w=600, h=290, vid=1, title="Sales by Region"),
            ],
        },
    ]
```

When `build_pages()` exists, it takes priority over `build_visuals()`.
Each page gets its own tab in Power BI, its own title banner, and
independent `vid` numbering.

---

## Windsurf / Claude Code Integration

vizbuilder ships a set of task-focused Claude Code skills (same structure
as [pbi-cli](https://github.com/MinaSaad1/pbi-cli)'s skills), so Windsurf or
Claude Code loads only the guidance relevant to your prompt.

| Skill | Use it for |
|---|---|
| `vizbuilder-report` | End-to-end build workflow, PBIX format, SecurityBindings |
| `vizbuilder-visuals` | Adding visuals, visual types, `Table[Column]` bindings |
| `vizbuilder-pages` | Multi-page dashboards, tabs, page titles, layout patterns |
| `vizbuilder-layout` | Linting and auto-fixing alignment, overlap, sizing |
| `vizbuilder-analysis` | Metadata, data lineage, orphaned fields, consistency checks |
| `vizbuilder-docs` | Data dictionary, measure catalog, HTML audit report |
| `vizbuilder-deployment` | PBRS compatibility validation, deployment checklist |
| `vizbuilder-diagnostics` | Errors and troubleshooting |

### Install the skills

```bash
python install_skill.py                                  # install / update all
python install_skill.py list                             # show install status
python install_skill.py install --skill vizbuilder-visuals
python install_skill.py uninstall                        # remove all
```

Each skill is copied to `~/.claude/skills/<name>/SKILL.md`, and a
marker-delimited block listing the skills is added to `~/.claude/CLAUDE.md`
(removed again by `uninstall`). Installing also removes the old single
`~/.claude/skills/vizbuilder/` skill and its `CLAUDE.md` entry.
Restart Windsurf after installing.

### Using prompts

After installing, just describe what you want:

- *"Add a bar chart showing Sales by Region"* → `vizbuilder-visuals`
- *"Add a Loan Portfolio tab to the dashboard"* → `vizbuilder-pages`
- *"Fix the alignment issues in my dashboard"* → `vizbuilder-layout`
- *"Find unused columns in this PBIX"* → `vizbuilder-analysis`
- *"Is this file ready for Report Server?"* → `vizbuilder-deployment`

The AI will edit `visuals_config.py` and run `build.py` / `lint.py` / `analyze.py` for you.

### Testing the skills

```bash
python -m unittest discover tests           # frontmatter, triggers, installer
python tests/test_skills.py --triggers      # print prompt -> skill table
```

---

## Workflow Summary

```
PBRS .pbix
  └─► PBRS Desktop: Get Data → load → File→Save → Close
  └─► python build.py input.pbix output.pbix
  └─► PBRS Desktop: open output → verify → File→Save
  └─► deploy .pbix to Power BI Report Server
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `MashupValidationError` | SecurityBindings not removed | Ensure you're opening the *output* file, not the input |
| Visuals show "Can't display visual" | Table or column name mismatch | Check `TABLE` in `visuals_config.py` matches data model exactly |
| "Unrecognized version" on PBRS | File last saved by a newer regular Desktop | Open and save in Power BI Desktop for Report Server (or regular Desktop from the same month) |
| Visual blank or "not supported" in PBRS Desktop | Visual type newer than your PBRS release | Use the safer choice from the build warning (e.g. `slicer`, `card`) |
| `--open` opens the wrong Desktop | Both editions installed | Add `--rs` or `--regular`, or set `PBI_DESKTOP_PATH` |
| `FileNotFoundError` on input | Wrong path | Use full absolute path or run from the same folder as the PBIX |
