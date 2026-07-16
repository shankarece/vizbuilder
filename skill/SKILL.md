---
name: VizBuilder (PBRS Visuals & Analysis)
description: >
  Build, audit, analyze, and document Power BI Report Server (PBRS) .pbix files.
  Invoke this skill for: creating visuals (bar, line, card, KPI, matrix, table),
  fixing layouts (alignment, overlap, sizing), analyzing dashboards (lineage, orphans),
  checking consistency (naming, titles, sizing), extracting documentation, generating
  audit reports, and validating PBRS compatibility. Works offline, no PBIR/PBIP needed,
  no PowerShell required (CMD compatible). Supports banking/financial dashboards.
---

# VizBuilder — PBRS Visual Builder & Analyzer

Complete offline suite for Power BI Report Server (PBRS) .pbix files:
- **Build** visuals programmatically (32 types, multi-page dashboards)
- **Audit** layouts (alignment, overlap, sizing consistency)
- **Analyze** dashboards (data lineage, field usage, orphaned objects)
- **Check** consistency (naming, titles, colors, data types)
- **Extract** documentation (data dictionary, measure catalog, relationship maps)
- **Generate** HTML audit reports (health score, violations, recommendations)
- **Validate** PBRS compatibility (file size, unsupported features, performance)

Works offline (no Power BI Desktop connection needed), no PBIR/PBIP format, no PowerShell.

## Project Location

Scripts are in the repo root (cloned from
`https://github.com/shankarece/vizbuilder`). Key files:

- `visuals_config.py` — **the only file to edit** (defines visuals + pages)
- `build.py` — entry point (or `build.bat` for CMD)
- `layout_builder.py` — engine (do not edit)
- `visual_types.py` — 32 visual type definitions (do not edit)
- `pbix_patch.py` — PBIX zip manipulation (do not edit)

## Running (CMD — no PowerShell needed)

```cmd
REM Build and auto-open in Desktop
build.bat input.pbix output.pbix --open

REM Build only (open manually)
python build.py input.pbix output.pbix
```

The `--open` flag automatically launches the output in Power BI Desktop.

## IMPORTANT RULES FOR EDITING visuals_config.py

1. **NEVER create a new file** — always edit the existing `visuals_config.py`
2. **When adding visuals to an existing page**, append to the existing
   `build_visuals()` or the appropriate page in `build_pages()` — do NOT
   replace existing visuals
3. **When asked to "add a tab" or "add a page"**, switch from single-page
   (`build_visuals`) to multi-page (`build_pages`) — see Multi-Page below
4. **Always set `title=`** on every visual
5. **Always set `DASHBOARD_TITLE`** for single-page mode
6. **vid must be unique** per page — check existing vids before adding

## Single-Page Dashboard

```python
from layout_builder import add_visual, add_title

PAGE_NAME       = "Sales Overview"
DASHBOARD_TITLE = "Sales Dashboard"   # appears as large title at top

def build_visuals() -> list:
    visuals = []

    visuals.append(add_visual("clustered_column", bindings={
        "category": "Orders[Category]",
        "value":    "Orders[Sales]",
    }, x=20, y=60, w=600, h=290, vid=1, title="Sales by Category"))

    visuals.append(add_visual("card", bindings={
        "value": "Orders[Sales]",
    }, x=660, y=60, w=300, h=120, vid=2, title="Total Sales"))

    return visuals
```

## Multi-Page Dashboard

When the user wants multiple pages/tabs, define `build_pages()` instead
of `build_visuals()`. This takes priority when both exist.

```python
from layout_builder import add_visual, add_title

def build_pages() -> list:
    return [
        {
            "name": "Sales Overview",       # tab/page name
            "title": "Sales Dashboard",     # large title at top of page
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

                add_visual("table", bindings={
                    "value": "Orders[Customer Name]",
                }, x=20, y=390, w=940, h=280, vid=2, title="Customer Details"),
            ],
        },
    ]
```

### Converting single-page to multi-page

When the user says "add a page" or "add a tab", convert like this:
1. Move existing visuals from `build_visuals()` into the first page dict
2. Add the new page as a second dict in the list
3. Remove `build_visuals()` function (or keep it — `build_pages` takes priority)
4. Each page has its own `title` and independent `vid` numbering

## add_visual() Parameters

```
add_visual(
    visual_type,       # "bar", "line", "donut", "card", "combo", etc.
    bindings={...},    # role → "Table[Column]" mappings
    x=50, y=50,        # position (pixels, canvas is 1280×720)
    w=400, h=300,      # size (pixels, auto-defaults per type)
    vid=1,             # unique visual id per page
    tab_order=0,       # z-order
    title="My Title",  # visual title (auto-generated if omitted)
    show_labels=False,  # show data point labels
)
```

## add_title() — Dashboard Page Title

```python
add_title("My Dashboard Title", font_size=20)
```

Auto-added when `DASHBOARD_TITLE` is set (single-page) or `"title"` key
exists in page dict (multi-page). Can also be added manually to visuals list.

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

## Formatting (auto-applied)

- **Dashboard title** — large bold text across top of each page
- **Visual titles** — from `title=` param or auto-generated
- **Axis titles** — enabled on charts with axes
- **Legend** — shown on right for applicable charts
- **Data labels** — on donut charts; use `show_labels=True` for others

## Banking / Financial Dashboard Patterns

Common layouts for financial dashboards:

### KPI Row (top of page)
```python
# Row of 4 KPI cards across the top
add_visual("card", bindings={"value": "Txn[Total Assets]"},
    x=20, y=60, w=290, h=100, vid=1, title="Total Assets")
add_visual("card", bindings={"value": "Txn[Total Deposits]"},
    x=330, y=60, w=290, h=100, vid=2, title="Total Deposits")
add_visual("card", bindings={"value": "Txn[Total Loans]"},
    x=640, y=60, w=290, h=100, vid=3, title="Total Loans")
add_visual("card", bindings={"value": "Txn[NPL Ratio]"},
    x=950, y=60, w=290, h=100, vid=4, title="NPL Ratio")
```

### Standard Banking Page Layout
```python
# KPI cards row:      y=60,  h=100  (4 cards)
# Main charts row:    y=180, h=260  (2 charts side by side)
# Detail row:         y=460, h=220  (table + smaller chart)
```

### Multi-Page Banking Dashboard
```python
def build_pages():
    return [
        {"name": "Executive Summary", "title": "Bank Performance Dashboard",
         "visuals": [...]},
        {"name": "Loan Portfolio", "title": "Loan Analysis",
         "visuals": [...]},
        {"name": "Deposits", "title": "Deposit Trends",
         "visuals": [...]},
        {"name": "Risk & Compliance", "title": "Risk Metrics",
         "visuals": [...]},
    ]
```

## Reference Banking Dashboard Repos (for layout inspiration)

- `github.com/pkanphade/Banking-Analysis-PowerBI-Dashboard` — client demographics, financial metrics
- `github.com/Pratik94229/Bank-Loan-Dashboard---Power-BI` — multi-page loan portfolio
- `github.com/meabhaykr/Financial-Insights-in-Banking-Data-using-PowerBI` — risk, customer, branch dashboards
- `github.com/dalion619/programmable-banking-power-bi-template` — .pbit template for transaction logs

## PBIX Analysis Suite (Phases 1-4)

Comprehensive offline analysis, documentation, and validation for PBRS dashboards.

### Phase 1: Metadata Extraction (`pbix_analyzer.py`)

Extract complete PBIX structure, data model, and report definitions.

```cmd
python pbix_analyzer.py file.pbix metadata_output.json
```

Outputs `*_metadata.json` containing:
- **File info**: size, creation date, modified date, PBIX version
- **Data model**: tables, columns, measures, relationships, data types
- **Report structure**: pages, visuals (types, positions, titles, bindings)
- **Security**: SecurityBindings status, RLS role count
- **Embedded data**: estimated model size, hidden objects count

**Use when**: You need a complete inventory of your dashboard structure, data lineage, or want to programmatically analyze PBIX content.

### Phase 2: Data Lineage Analysis (`data_lineage.py`)

Trace data flow from tables through measures to visuals; identify orphaned fields.

```cmd
python data_lineage.py metadata.json lineage_output.json
```

Outputs `*_lineage.json` containing:
- **Lineages**: which tables/columns/measures are used by which visuals
- **Orphaned objects**: unused tables, columns, measures (dead code)
- **Measure-to-measure dependencies**: calculated measure chains
- **Circular reference detection**: flag problematic dependency loops

**Use when**: You want to clean up unused fields, understand data flow, or find "dark data" not used in any visual.

### Phase 3: Consistency Checking (`consistency_checker.py`)

Check design patterns and structural consistency.

```cmd
python consistency_checker.py metadata.json lineage.json violations.json
```

Analyzes 8 categories:
1. **Naming conventions** — visual IDs, measure/table naming patterns
2. **Visual sizing** — same visual types should have uniform dimensions
3. **Title presence** — all data visuals should have descriptive titles
4. **Alignment** — positions should snap to 10px grid
5. **Unused objects** — finds orphaned tables, columns, measures
6. **Measure consistency** — patterns in calculated measures
7. **Hidden objects** — warns if >30% of columns are hidden
8. **Data types** — detects excessive string columns (poor design)

Severity levels:
- **Error**: breaks functionality
- **Warning**: design smell, potential performance issue
- **Info**: suggestion for improvement

**Use when**: You want to audit dashboard quality, fix design inconsistencies, or prepare for PBRS deployment.

### Phase 4a: Documentation Export (`metadata_extractor.py`)

Generate structured documentation in multiple formats.

```cmd
python metadata_extractor.py metadata.json output_directory/
```

Generates 6 exports:
1. **data_dictionary.json** — all tables, columns, measures with metadata
2. **measure_catalog.csv** — all measures with DAX expressions and format strings
3. **columns_registry.csv** — all columns with types, hidden status, expressions
4. **relationships.md** — markdown list of all relationships with cardinality
5. **tables_summary.md** — markdown overview of tables (column/measure counts)
6. **visual_registry.json** — all visuals with bindings and positions

**Use when**: You need to share data model documentation with analysts, create a data dictionary, or generate reports for stakeholders.

### Phase 4b: HTML Audit Report (`generate_docs.py`)

Create a unified interactive HTML audit report (combines all phases).

```cmd
python generate_docs.py metadata.json lineage.json violations.json report.html
```

Single-file HTML report includes:
- **Executive summary** — page count, visual count, tables, measures
- **Health score** (0–100) — based on violation count
- **File metadata** — size, version, SecurityBindings status
- **Visual inventory** — table of all visuals with positions and bindings
- **Data lineage** — used/orphaned object summary
- **Consistency violations** — categorized by severity with suggestions
- **Data model documentation** — table/column/measure reference

Professional styling with light/dark theme support.

**Use when**: You need to share a complete dashboard audit with stakeholders or create onboarding documentation.

### Phase 4c: PBRS Compatibility Validator (`pbrs_validator.py`)

Validate PBIX for Power BI Report Server deployment.

```cmd
python pbrs_validator.py file.pbix metadata.json validation.json
```

Checks:
- **File size** — against 2GB PBRS limit
- **Visual types** — detects unsupported visuals for PBRS
- **Relationships** — flags bidirectional cross-filters that impact performance
- **Premium features** — detects calculated tables, premium-only patterns
- **SecurityBindings** — warns if stripped (need to regenerate in Desktop)
- **Performance** — recommends optimization (table count, column count, visuals per page)

Output categories:
- **Error**: blocking issue (cannot deploy to PBRS)
- **Warning**: may cause issues in PBRS
- **Info**: optimization recommendation

**Use when**: You're preparing a dashboard for PBRS deployment and need to ensure compatibility.

### Complete Analysis Pipeline

Run all 4 phases with a single command:

```cmd
python analyze.py file.pbix --output analysis_results/
```

Orchestrates:
1. Extract metadata → `*_metadata.json`
2. Analyze lineage → `*_lineage.json`
3. Check consistency → `*_violations.json`
4. Export documentation → 6 formats (CSV, JSON, Markdown)
5. Generate HTML report → `*_audit_report.html`
6. Validate PBRS → `*_pbrs_validation.json`

**Single output directory** with all reports and exports.

Flags:
- `--metadata-only` — extract metadata only
- `--lineage-only` — analyze lineage only (requires metadata.json)
- `--output <dir>` — save to custom directory (default: `./pbix_analysis/`)

**Use when**: You want a complete 360° dashboard audit in one go.

## Layout Linter / Auditor

Audit any PBIX file for layout issues and auto-fix them.

```cmd
REM Audit and print issues
lint.bat file.pbix

REM Audit and save markdown report
lint.bat file.pbix --report audit.md

REM Auto-fix issues and save corrected file
lint.bat file.pbix --fix

REM Fix and auto-open in Desktop
lint.bat file.pbix --fix --open
```

### What it checks

| Check | Severity | Auto-fixable? |
|---|---|---|
| Overlapping visuals | ERROR | No (needs manual repositioning) |
| Out of canvas bounds | ERROR | YES - clamps to canvas |
| Near-aligned positions (off by a few px) | WARNING | YES - snaps to common position |
| Missing visual titles | WARNING | No (add via title= param) |
| Inconsistent sizes (same type, diff size) | INFO | YES - equalizes |
| Off-grid positions | INFO | YES - snaps to 10px grid |
| Uneven horizontal gaps | INFO | YES - equalizes spacing |
| Too close to canvas edge | INFO | No (intentional in some layouts) |

### Using with prompts

- *"Check this PBIX for layout issues"* - runs lint.bat
- *"Fix the alignment issues in my dashboard"* - runs lint.bat --fix
- *"Generate a layout audit report"* - runs lint.bat --report

### Report output

The `--report` flag generates a markdown document with:
- Visual inventory table (all visuals, positions, sizes, titles)
- Issues grouped by category with severity
- Fixes applied (if --fix was used)

## Workflow

```
Clone repo -> edit visuals_config.py -> build.bat input.pbix output.pbix --open
-> Desktop opens -> verify -> File->Save -> deploy to PBRS
```

To audit an existing PBIX:
```
lint.bat existing.pbix --fix --report audit.md --open
```
