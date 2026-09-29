# Agent instructions (vizbuilder)

vizbuilder builds the **report layer** (pages, visuals) of Power BI Report
Server (PBRS) `.pbix` files, offline, with plain Python (standard library only).
It cannot create the data model (tables, relationships, measures) — that is done
first, live, with a modeling tool (a Power BI Modeling MCP or pbi-cli).

## Read the skills first

Task-specific guidance is in `skills/<name>/SKILL.md`. Read the one that
matches the request before acting:

| Skill | Use it for |
|---|---|
| `vizbuilder-modeling` | Building the data model first; pbi-cli / MCP handoff |
| `vizbuilder-report` | End-to-end workflow, PBIX format, Desktop editions |
| `vizbuilder-visuals` | `add_visual`, visual types, `Table[Column]` bindings |
| `vizbuilder-pages` | Multi-page dashboards, titles, layout patterns |
| `vizbuilder-layout` | Lint and auto-fix alignment, overlap, sizing |
| `vizbuilder-analysis` | Metadata, lineage, consistency checks |
| `vizbuilder-docs` | Data dictionary, measure catalog, HTML audit report |
| `vizbuilder-deployment` | PBRS validation, deploy checklist |
| `vizbuilder-diagnostics` | Errors and troubleshooting |

## Commands (run from the repo root)

```cmd
python -m unittest discover tests
python analyze.py input.pbix --metadata-only --output analysis\
build.bat input.pbix output.pbix
lint.bat output.pbix --report audit.md
python analyze.py output.pbix --output analysis\
```

## Rules

1. **Edit only the dashboard definition** (`visuals_config.py`, or the file the
   user passes with `build.py --config`). Do not edit engine files unless asked
   to fix a bug. Users keep their own config outside the tool folder so an
   upgrade never overwrites it: `build.bat in.pbix out.pbix --config <path>`.
2. **Never overwrite the input `.pbix`.** Always build to a new output path.
3. **Work on a local copy** of the `.pbix` (for example `C:\work\`), not a
   OneDrive or network path, and not while another process is syncing it.
4. **Model first, save, then build.** Live model changes (relationships,
   measures) exist only in the running Desktop session until **File → Save**.
   `build.py` copies the model from the file on disk, so an unsaved model is
   missing from the output. Save (ideally close Desktop) before building.
5. **Check real names first.** Read `datamodel.tables` in the metadata output
   (or the Desktop Data pane). Table and column names must match exactly.
6. **Known limitation:** value fields are always written as `Sum(column)`, so
   bind raw numeric columns. Real DAX measures cannot be bound yet.
7. **Never use PBIR-based report tooling on a `.pbix`**: pbi-cli's report-layer
   commands and skills (`pbi report`, `visual`, `filters`, `bookmarks`, `format`),
   `pbir-cli`, and data-goblin's `reports` / `create-pbi-report` skills. They
   write PBIR, not the `.pbix` format Report Server uses. Those tools are for the
   data model only (see `vizbuilder-modeling`).
8. **Prefer PBRS-safe visuals.** If `build.py` prints a "PBRS Desktop
   compatibility warning", use the suggested alternative unless told otherwise.
9. A built file has no `SecurityBindings`. It must be opened in Power BI
   Desktop for Report Server and saved before it can be deployed. That step is
   for a human.

## Definition of done for a dashboard request

- Tests pass (`python -m unittest discover tests`)
- `build.py` succeeded with no unresolved compatibility warnings
- `lint.py` shows no errors
- `analyze.py` PBRS validation has no errors
- Tell the user what to verify in Desktop, then File → Save and deploy
