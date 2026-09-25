---
name: VizBuilder Report
description: >
  Build and manage Power BI Report Server (PBRS) .pbix reports end to end with
  vizbuilder. Invoke this skill whenever the user mentions "build report",
  "build the pbix", "PBRS report", "report server", "pbix file", "run build",
  "build.bat", "open in Desktop", "SecurityBindings", "report layout", "legacy
  layout", "Power BI Desktop for Report Server", "PBRS Desktop", "RS Desktop",
  "how does vizbuilder work", or wants the overall workflow from an
  input .pbix to a deployable report. For specific tasks, see also:
  vizbuilder-visuals (charts, bindings), vizbuilder-pages (tabs, titles),
  vizbuilder-layout (lint, alignment), vizbuilder-analysis (lineage, audit),
  vizbuilder-docs (data dictionary, HTML report), vizbuilder-deployment
  (PBRS validation, deploy), vizbuilder-diagnostics (errors, troubleshooting),
  vizbuilder-modeling (build the data model first, on a live connection).
tools: vizbuilder
---

# VizBuilder Report Skill

Build PBRS `.pbix` reports programmatically with plain Python (standard
library only). No Power BI Service, no premium licence, no PBIR/PBIP format,
no PowerShell (everything runs from CMD), and no live connection to Desktop.

## Project Location

Scripts live in the repo root (cloned from
`https://github.com/shankarece/vizbuilder`):

| File | Purpose | Edit? |
|---|---|---|
| `visuals_config.py` | Visuals and pages definition | **Yes — the only file to edit** |
| `build.py` / `build.bat` | End-to-end build entry point | No |
| `layout_builder.py` | Layout read/write engine, `add_visual`, `add_title` | No |
| `visual_types.py` | 32 visual types, role aliases, default sizes | No |
| `pbix_patch.py` | PBIX zip manipulation | No |
| `desktop.py` | Finds/opens Power BI Desktop for `--open` | No |

## Legacy PBIX Format (what vizbuilder edits)

A PBRS `.pbix` is a ZIP archive:

```
MyReport.pbix
  Report/Layout        # UTF-16 LE JSON: pages (sections) and visualContainers
  DataModel            # Analysis Services binary (never touched)
  SecurityBindings     # DPAPI integrity hash over the file contents
  ...
```

Any external change invalidates `SecurityBindings` and Desktop refuses the file
with `MashupValidationError`. vizbuilder therefore:

1. Strips `SecurityBindings`
2. Replaces `Report/Layout` with the generated layout
3. Leaves everything else byte-for-byte (DataModel is copied untouched)

Opening the output in Power BI Desktop for Report Server (or regular Desktop
from the same monthly release) and pressing **File → Save** regenerates
`SecurityBindings`. Because `Version`, `DataModel`, and report settings are
copied unchanged, a file saved by PBRS Desktop stays a PBRS Desktop file.

## Building

```cmd
REM Build and auto-open (Power BI Desktop for Report Server when installed)
build.bat input.pbix output.pbix --open

REM Force the Desktop edition used by --open
build.bat input.pbix output.pbix --open --rs
build.bat input.pbix output.pbix --open --regular

REM Build only
python build.py input.pbix output.pbix
```

`--open` looks for `%ProgramFiles%\Microsoft Power BI Desktop RS\bin\PBIDesktop.exe`
first, then regular Desktop. Set `PBI_DESKTOP_PATH` to use a specific
`PBIDesktop.exe`. The build refuses to overwrite its input.

If any visual may be missing from PBRS Desktop (e.g. Azure Map, new card,
text/list/button slicers), the build prints a
**PBRS Desktop compatibility warning** with a safer alternative.

Never overwrite the input file — always write to a new output path.

## Rules (Don't Break These)

1. **Edit only `visuals_config.py`** — never create a new config file and never
   edit the engine files.
2. **Prepare the input first** — the input `.pbix` must already have its data
   loaded and saved in Desktop so the tables/columns you bind to exist. If
   there's no data model yet, build it with a live-connection tool first
   (see vizbuilder-modeling), not with vizbuilder.
3. **Prefer Power BI Desktop for Report Server** for preparing the input and
   saving the output. If regular Desktop is used, it must be the **same monthly
   release** as PBRS Desktop, or the server reports "unrecognized version".
4. **Always File → Save in Desktop** before deploying — a file without
   `SecurityBindings` is not deployable.
5. **Never commit `.pbix` files** with real data (they are git-ignored).

## Workflow: Build a Complete Report

This workflow uses several skills:

```cmd
REM 1. Inspect the model you will bind to (vizbuilder-analysis)
python analyze.py input.pbix --metadata-only --output analysis\

REM 2. Define pages and visuals in visuals_config.py
REM    (vizbuilder-pages, vizbuilder-visuals)

REM 3. Build and open (this skill)
build.bat input.pbix output.pbix --open

REM 4. Lint and fix the layout (vizbuilder-layout)
lint.bat output.pbix --fix --report audit.md

REM 5. Check PBRS compatibility (vizbuilder-deployment)
python analyze.py output.pbix --output analysis\

REM 6. In Desktop: verify -> File -> Save -> deploy to Report Server
```

## Related Skills

| Skill | When to use |
|---|---|
| **vizbuilder-modeling** | Data model doesn't exist yet — build it live before running vizbuilder |
| **vizbuilder-visuals** | Add visuals, pick types, bind `Table[Column]` fields |
| **vizbuilder-pages** | Multi-page/tab dashboards, page titles, page layouts |
| **vizbuilder-layout** | Audit and auto-fix alignment, overlap, sizing |
| **vizbuilder-analysis** | Metadata, lineage, orphaned fields, consistency checks |
| **vizbuilder-docs** | Data dictionary, measure catalog, HTML audit report |
| **vizbuilder-deployment** | PBRS compatibility validation and deployment steps |
| **vizbuilder-diagnostics** | Errors, "Can't display visual", version problems |
