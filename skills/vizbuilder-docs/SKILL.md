---
name: VizBuilder Documentation
description: >
  Generate documentation for PBRS .pbix reports and their data models with
  vizbuilder -- data dictionary, measure catalog, column registry,
  relationship map, visual registry, and a single-file HTML audit report.
  Invoke this skill whenever the user says "document this report", "document
  this model", "data dictionary", "measure catalog", "list all measures",
  "column list", "relationships", "model inventory", "catalog", "HTML
  report", "audit report", "health score", "share with stakeholders", or
  wants a written description of what a .pbix contains.
tools: vizbuilder
---

# VizBuilder Documentation Skill

Turn the analysis output (see vizbuilder-analysis) into shareable documents.
Everything runs offline.

## Prerequisite

Documentation is generated from `*_metadata.json` (and optionally lineage and
violations). Create them first:

```cmd
python analyze.py file.pbix --output analysis\
```

`analyze.py` already runs both steps below; call them directly only to
regenerate one output.

## Documentation Exports

```cmd
python metadata_extractor.py analysis\file_metadata.json docs\
```

| Output | Contents |
|---|---|
| `data_dictionary.json` | All tables, columns, measures with metadata |
| `measure_catalog.csv` | Measures with DAX expressions and format strings |
| `columns_registry.csv` | Columns with types, hidden flag, expressions |
| `relationships.md` | Relationships with cardinality |
| `tables_summary.md` | Tables with column and measure counts |
| `visual_registry.json` | Visuals with bindings and positions |

## HTML Audit Report

```cmd
python generate_docs.py metadata.json lineage.json violations.json report.html
```

Lineage and violations are optional positional arguments, but the report is
far more useful with them. The single self-contained HTML file includes:

- **Executive summary** — pages, visuals, tables, measures
- **Health score** (0–100) from the violation count
- **File metadata** — size, version, SecurityBindings status
- **Visual inventory** — positions and bindings
- **Data lineage** — used vs orphaned objects
- **Violations** — grouped by severity with suggestions
- **Data model reference** — tables, columns, measures

Light and dark themes are supported.

## Workflow: Stakeholder Pack

```cmd
REM 1. Full analysis (includes HTML report)
python analyze.py file.pbix --output analysis\

REM 2. Share:
REM    analysis\file_audit_report.html   (overview for everyone)
REM    analysis\measure_catalog.csv      (for analysts)
REM    analysis\relationships.md         (for modellers)
```

## Best Practices

- Regenerate documentation after every model or layout change.
- Commit the markdown/CSV exports (not the `.pbix`) to version control to
  track model changes over time.
- Document the business meaning of measures, not only their DAX.
- Never share exports that contain sensitive column names or sample values
  without review.
