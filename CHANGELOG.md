# Changelog

Version number lives in `VERSION`. `python build.py --version` prints it, and the
build banner shows it, so colleagues can say which release they have.

## 0.2.1

- The two made-up sample files for the Desktop check now live in the repo
  (`demo/verify/`) and ship in the release zip, so a plain GitHub download is
  complete. Every other `.pbix` is still ignored by git and left out of releases.
- `.bat` files use Windows line endings (`.gitattributes`, and in the release zip).
- Tests: the released `.pbix` samples are checked (no external connections, data
  model untouched, the documented rebuild command reproduces the check file).

## 0.2.0

Office edition: everything needed to run, hand over and demonstrate vizbuilder on
Power BI Report Server Desktop with no internet.

- **Bindings:** `Table[[Measure]]` binds a real model measure; `Sum(...)`,
  `Avg(...)`, `Count(...)` aggregate explicitly; a role takes a list of fields
  (table columns, several matrix values).
- **Fixed:** slicers and tables were written as `Sum(Column)`, which cannot work on
  text (a Region slicer would not draw). They now use plain columns. **Behaviour
  change:** numbers in a table must now be marked `Sum(...)` (or be a measure).
- **Fixed:** reading reports saved by Power BI Desktop. The analyzer, lineage and
  linter assumed vizbuilder's own container shape and crashed or reported
  0 x 0 visuals on Desktop-saved files; lineage never saw any bindings on classic
  `.pbix` files, so "unused fields" was always empty or wrong. Containers now
  also carry the standard top-level `x/y/width/height` fields.
- **New:** optional `pbixray` support reads tables, columns, measures and
  relationships from a `.pbix` offline (`datamodel.source` is `"pbixray"`).
- **New:** `doctor.py` / `doctor.bat` environment check with a real self-test.
- **New:** `START_HERE.md` and `demo/` (Superstore dashboard, demo script, user
  guide, prompts, five-minute Desktop check with A/B role tests).
- **New:** a test enforces that the program imports no network library.
- **Still unconfirmed on Report Server Desktop:** legends, combo, KPI, gauge,
  scatter, waterfall, funnel role names. `demo/VERIFY_IN_DESKTOP.md` settles it.
- 190+ automated tests.

## 0.1.1

- `vizbuilder-modeling`: which data-goblin/power-bi-agentic-development plugins
  are safe to use with vizbuilder (model-side only) and why its `reports`
  plugin must stay out of any environment that builds `.pbix` for Report Server
  (it writes PBIR). GPL-3.0 and weekly-release caveats noted.
- Agents are now told never to use any PBIR-based report tooling (pbi-cli report
  commands, `pbir-cli`, `create-pbi-report`) on a `.pbix`.

## 0.1.0

First packaged release.

- Nine task-focused agent skills in `skills/` (report, visuals, pages, layout,
  analysis, docs, deployment, diagnostics, modeling) and `AGENTS.md`.
- `install_skill.py`: list / install / uninstall, optional `--with-pbi-cli`
  (pbi-cli's model-side skills only).
- Power BI Desktop for Report Server support: `--rs` / `--regular` for `--open`,
  build-time compatibility warnings for visuals PBRS may lack.
- `build.py --config <file>` keeps your dashboard definition outside the tool
  folder so upgrading never overwrites it.
- Fixes: `analyze.py --output` was ignored, PBIX version read as UTF-8,
  unclosed layout file handle, `lint.py --open` ignored the Desktop edition.
- 88+ automated tests (`python -m unittest discover tests`).

Known limitations: value fields are always written as `Sum(column)` (real DAX
measures cannot be bound yet); vizbuilder cannot create the data model.
