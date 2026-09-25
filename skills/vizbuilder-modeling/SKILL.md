---
name: VizBuilder Modeling Handoff
description: >
  Coordinate vizbuilder (offline PBRS report builder) with a live data-model
  tool -- pbi-cli, a Power BI / Fabric MCP server, or Tabular Editor scripting
  -- so an agent can build a full dashboard: data model first, visuals second,
  on the same .pbix. Invoke this skill whenever the user mentions "Power BI
  MCP", "build the data model", "create measures", "create tables", "DAX",
  "TOM", "tabular object model", "live connection", "pbi connect",
  "relationships and measures", "connect to Power BI Desktop", "end to end
  dashboard", "agentic dashboard", "build a dashboard from scratch", or asks
  why vizbuilder can't create tables/measures/relationships.
tools: vizbuilder
---

# VizBuilder Modeling Handoff Skill

vizbuilder only builds the **report layer** (pages, visuals, bindings) of a
`.pbix` file, offline, with no dependencies. It cannot create the **data
model** (tables, columns, relationships, measures) because that lives in the
`DataModel` entry -- a compressed Analysis Services binary, not JSON. Building
it requires a **live Tabular Object Model (TOM) connection**, which needs
Power BI Desktop actually running and (on Windows) `pythonnet` + AMO/ADOMD.NET.

That's a different tool's job. This skill is the handoff between them.

## The Two Layers

| Layer | Tool | Needs |
|---|---|---|
| Data model (tables, relationships, measures, RLS) | pbi-cli, a Power BI/Fabric MCP, Tabular Editor scripting | Desktop running, live TOM connection |
| Report (pages, visuals, layout, bindings) | **vizbuilder** | Nothing — offline, stdlib only, no connection |

Neither tool touches the other's layer. `DataModel` is opaque to vizbuilder
(copied byte-for-byte, see vizbuilder-report); `Report/Layout` is normally out
of scope for a TOM-based tool, since TOM only models data, not the report.

## Order of Operations

Always build the model **before** the report, and never run them at the same
time against the same open file:

1. **Model phase (live connection required).** With Desktop open on the
   `.pbix`, use the model tool to load/connect data sources and create
   tables, relationships, and measures. Finish with **File → Save** in
   Desktop, then **close Desktop** (or at least the live connection) so the
   file on disk is the current source of truth and nothing else has it open.
2. **Verify the model landed** (offline, vizbuilder-analysis):
   ```cmd
   python analyze.py model.pbix --metadata-only --output analysis\
   ```
   Check `datamodel.tables` in `analysis\model_metadata.json` for the exact
   table and column names, and `datamodel.tables[].measures` for measure
   names, before binding any visual to them.
3. **Report phase (offline, no connection).** With Desktop fully closed, run
   vizbuilder as usual: edit `visuals_config.py`, then
   ```cmd
   build.bat model.pbix dashboard.pbix --open
   ```
   (see vizbuilder-visuals, vizbuilder-pages, vizbuilder-report).
4. **Never run the model tool and vizbuilder on the same file in the same
   moment.** vizbuilder reads and rewrites the zip on disk; a live TOM
   connection holds the file open and can overwrite vizbuilder's changes on
   its own next save. If more model changes are needed after visuals exist,
   reopen in Desktop, make them, save, close, then rebuild the report with
   vizbuilder again (the `Report/Layout` you already built survives, since
   vizbuilder only touches `DataModel` by copying it untouched, and Desktop's
   own save preserves `Report/Layout` it didn't change).

## Why Not Merge Them Into One Tool

Doing model changes live avoids the alternative -- hand-crafting the
`DataModel` binary offline -- which is not realistically safe (no public
schema for the AS storage engine format vizbuilder could target without a
live connection anyway). Keeping vizbuilder connection-free is what lets it
run anywhere (Linux CI, an agent sandbox, no Desktop installed) for the
report layer; keeping model changes on a live TOM connection is what makes
them consistent and validated by the engine itself, not a guess at the
binary format. Splitting the two lets each one stay light for its layer
instead of one tool needing both a zero-dependency mode and a live-connection
mode.

## If You Only Have pbi-cli (No MCP Server)

pbi-cli's model skills are the reference shape for the model phase even
without an MCP wrapper -- point the agent at its CLI directly:

```bash
pbi connect                                            # attach to running Desktop
pbi table list                                          # confirm what already exists
pbi measure create "Total Revenue" -e "SUM(Sales[Amount])" -t Sales
pbi relationship list
```

Then disconnect / close Desktop and switch to vizbuilder for the report, per
the order above. Do not use pbi-cli's own `report`/`visual`/`pages` commands
on a file vizbuilder manages -- those write PBIR (a folder format), not the
legacy `Report/Layout` vizbuilder edits; the two report formats are not
interchangeable on the same file.

## Full Agentic Workflow (One Prompt, Two Tools)

```text
1. "Connect to Power BI Desktop and build a model from <data source> with
    tables X, Y, Z, a relationship between X and Y, and measures A, B."
   -> model tool, live connection, ends with File -> Save, close Desktop

2. "Confirm the model: list tables, columns, and measures."
   -> python analyze.py model.pbix --metadata-only --output analysis\
   -> read analysis\model_metadata.json

3. "Add a KPI row with measures A and B, and a bar chart of X by Y."
   -> vizbuilder-visuals / vizbuilder-pages edit visuals_config.py
   -> build.bat model.pbix dashboard.pbix --open   (vizbuilder-report)
   -> lint.bat dashboard.pbix --fix                (vizbuilder-layout)
   -> python analyze.py dashboard.pbix --output analysis\  (vizbuilder-deployment)

4. Human: verify in Desktop -> File -> Save -> deploy to Report Server
   (vizbuilder-deployment)
```

## Related Skills

| Skill | When to use |
|---|---|
| **vizbuilder-report** | Report-layer build workflow once the model exists |
| **vizbuilder-visuals** | Adding visuals once table/column/measure names are confirmed |
| **vizbuilder-analysis** | Reading `datamodel.tables` to verify the model phase landed |
| **vizbuilder-deployment** | Final validation and Report Server deployment |
