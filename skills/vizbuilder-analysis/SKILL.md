---
name: VizBuilder Analysis
description: >
  Analyze PBRS .pbix dashboards offline with vizbuilder -- extract metadata,
  trace data lineage, find orphaned or unused fields, and check design
  consistency. Invoke this skill whenever the user mentions "analyze",
  "analyse this pbix", "what's in this report", "metadata", "lineage", "data
  flow", "which visuals use", "unused columns", "orphaned measures", "dead
  fields", "circular reference", "consistency check", "naming conventions",
  "audit the dashboard", "field usage", or needs the real table and column
  names before binding visuals.
tools: vizbuilder
---

# VizBuilder Analysis Skill

Offline analysis of any `.pbix` file (reads the ZIP directly; no Desktop
connection, no PBIR/PBIP). Standard library only.

## Full Pipeline (recommended)

```cmd
python analyze.py file.pbix --output analysis\
```

Writes to the output directory (default `pbix_analysis\`):

| File | Produced by |
|---|---|
| `<name>_metadata.json` | `pbix_analyzer.py` |
| `<name>_lineage.json` | `data_lineage.py` |
| `<name>_violations.json` | `consistency_checker.py` |
| data dictionary, measure catalog, registries | `metadata_extractor.py` (vizbuilder-docs) |
| `<name>_audit_report.html` | `generate_docs.py` (vizbuilder-docs) |
| `<name>_pbrs_validation.json` | `pbrs_validator.py` (vizbuilder-deployment) |

Flags:

- `--metadata-only` — stop after metadata extraction (fast; use before binding)
- `--lineage-only` — re-run lineage from an existing `*_metadata.json`
- `--output <dir>` — output directory

## Metadata Extraction

```cmd
python pbix_analyzer.py file.pbix metadata.json
```

Contains:

- **File info** — size, dates, PBIX version
- **Data model** — tables, columns, measures, relationships, data types
- **Report** — pages, visuals (type, position, title, bindings)
- **Security** — SecurityBindings status, RLS role count

Top-level keys: `file`, `pbix_version`, `security`, `structure`, `datamodel`, `report`,
`field_references`. Use `datamodel.tables` to get exact `Table[Column]` names
for vizbuilder-visuals bindings.

The `DataModel` inside a `.pbix` is a compressed binary that the standard
library cannot decode, so by default `datamodel.tables` is **empty** and
`datamodel.source` is `"none"`. To read tables, columns, measures (with DAX) and
relationships **offline**, install the optional
[pbixray](https://github.com/Hugoberry/pbixray) package (MIT; it needs `pandas`,
so an offline office needs a wheel folder, see below). When present it is used
automatically and `datamodel.source` becomes `"pbixray"`.

```cmd
pip install pbixray
```

Without it, `field_references` still lists every field the existing visuals use,
and the Desktop Data pane (or your modeling tool) shows the rest. Lineage and
orphan detection need the model: with an empty model they report nothing unused.

**No internet on the office machine?** On any machine that has it, run
`pip download pbixray -d wheels` (same Python version and 64-bit Windows), copy the
`wheels` folder across, then `pip install --no-index --find-links wheels pbixray`.

Hidden-column flags are not available from pbixray, so the "excessive hidden
columns" check stays quiet when it is used.

## Data Lineage

```cmd
python data_lineage.py metadata.json lineage.json
```

- Which tables/columns/measures feed which visuals (matched from each visual's
  saved query references such as `Sum(Orders.Revenue)`; works on reports saved
  by Desktop as well as ones vizbuilder built)
- **Orphaned objects** — tables, columns, measures not used by any visual
- Measure-to-measure dependency chains
- Circular reference detection

## Consistency Checks

```cmd
python consistency_checker.py metadata.json lineage.json violations.json
```

| # | Category | Looks for |
|---|---|---|
| 1 | Naming | Visual IDs, measure/table naming patterns |
| 2 | Visual sizing | Same visual type with different dimensions |
| 3 | Titles | Data visuals without a descriptive title |
| 4 | Alignment | Positions off the 10 px grid |
| 5 | Unused objects | Orphaned tables, columns, measures |
| 6 | Measures | Inconsistent calculated-measure patterns |
| 7 | Hidden objects | More than 30% of columns hidden |
| 8 | Data types | Excessive string columns |

Severity: **error** (breaks functionality), **warning** (design smell or
performance risk), **info** (suggestion).

## Workflow: Clean Up Unused Fields

```cmd
REM 1. Run the pipeline
python analyze.py file.pbix --output analysis\

REM 2. Read orphaned objects in analysis\file_lineage.json
REM 3. Confirm with the model owner, then hide/remove them in Desktop
REM 4. Re-run to confirm the orphan list is empty
```

## Workflow: Inspect Before Building

```cmd
python analyze.py input.pbix --metadata-only --output analysis\
```

Then bind visuals only to names that appear in
`analysis\input_metadata.json`.

## Related Skills

- **vizbuilder-docs** — turn the analysis into shareable documentation
- **vizbuilder-layout** — fix alignment/sizing issues found here
- **vizbuilder-deployment** — PBRS compatibility of the same file
