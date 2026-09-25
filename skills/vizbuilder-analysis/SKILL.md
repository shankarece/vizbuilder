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

`datamodel.tables` is filled only when the PBIX carries a readable model
schema; the `DataModel` itself is a compressed binary that is not decoded. If
the list is empty, `field_references` still shows every field the existing
visuals bind to, and the Data pane in Desktop shows the rest.

## Data Lineage

```cmd
python data_lineage.py metadata.json lineage.json
```

- Which tables/columns/measures feed which visuals
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
