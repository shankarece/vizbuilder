# Changelog

Version number lives in `VERSION`. `python build.py --version` prints it, and the
build banner shows it, so colleagues can say which release they have.

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
