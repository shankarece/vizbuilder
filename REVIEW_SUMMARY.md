# What changed — plain-language review (no diff needed)

This describes everything in PR #1
(`claude/vizbuilder-pbi-cli-update-h3yn6y` → `master`) without needing a
diff view. Delete this file once you're done reviewing.

## New files

| File | What it is |
|---|---|
| `desktop.py` | Finds and launches Power BI Desktop for `--open`. Prefers the Report Server edition, falls back to regular Desktop. |
| `skills/vizbuilder-report/SKILL.md` | (moved from `skill/SKILL.md`) End-to-end build workflow, PBIX format, SecurityBindings. |
| `skills/vizbuilder-visuals/SKILL.md` | Adding visuals, 32 visual types, `Table[Column]` bindings. |
| `skills/vizbuilder-pages/SKILL.md` | Multi-page dashboards, tabs, page titles, layout patterns. |
| `skills/vizbuilder-layout/SKILL.md` | `lint.py` checks and auto-fix. |
| `skills/vizbuilder-analysis/SKILL.md` | `analyze.py` pipeline: metadata, lineage, consistency. |
| `skills/vizbuilder-docs/SKILL.md` | Data dictionary, measure catalog, HTML audit report. |
| `skills/vizbuilder-deployment/SKILL.md` | PBRS validation, deploy steps, release checklist. |
| `skills/vizbuilder-diagnostics/SKILL.md` | Common errors → cause → fix. |
| `skills/vizbuilder-modeling/SKILL.md` | Handoff to a live-connection tool (pbi-cli / a Power BI-Fabric MCP) to build the data model, since vizbuilder can't. |
| `tests/test_skills.py` | Validates skill frontmatter, checks every visual alias is documented, runs 24 sample prompts through a keyword-matcher to confirm the right skill wins, round-trips `install_skill.py`. |
| `tests/test_pbrs.py` | Builds a fake PBRS-style `.pbix`, runs the real build pipeline on it, checks the output is safe to open (SecurityBindings gone, everything else byte-identical, valid UTF-16 layout), checks the compatibility warnings fire, checks Desktop-edition selection. |
| `tests/test_visual_types.py` | Tests alias resolution (`bar` → `barChart`, etc.) and that all the internal lookup tables agree with each other. |
| `tests/test_layout_builder.py` | Tests the code that turns `add_visual(...)` calls into the actual JSON Power BI reads, plus the UTF-16 file read/write round trip. |
| `tests/test_pbix_patch.py` | Tests the code that strips `SecurityBindings` and swaps in the new layout inside the `.pbix` zip. |
| `tests/test_consistency_checker.py` | Tests the design-quality checks (missing titles, inconsistent sizing, misalignment, etc.). |

**Total: 82 automated tests, all passing**, run with `python -m unittest discover tests`.

## Modified files

- **`README.md`** — new "Windsurf / Claude Code Integration" section listing all 9 skills; new "Data model vs. report layer" section explaining what vizbuilder can't do; PBRS Desktop is now the recommended edition throughout; new troubleshooting rows.
- **`install_skill.py`** — rewritten. Old version copied one file and had no way to remove it. New version: `list` / `install [--skill X] [--force]` / `uninstall`, writes a marker-delimited block to `~/.claude/CLAUDE.md`, and automatically removes the old single `vizbuilder` skill if it finds one. Plain `python install_skill.py` still works exactly as before (installs everything).
- **`build.py`** — now refuses to overwrite its own input file; uses `desktop.py` for `--open` instead of a hardcoded regular-Desktop-only path; prints a warning if you used a visual type that might not exist in Report Server Desktop.
- **`lint.py`** — `--open` now goes through `desktop.py` too (previously called `os.startfile` directly, which only ever opens whatever Windows has associated with `.pbix`).
- **`layout_builder.py`** — added a function that scans a built layout and lists any visuals that might not be supported in Report Server Desktop.
- **`visual_types.py`** — added the list of visual types that might not exist in Report Server Desktop, with a safer alternative for each (used by both `build.py` and `pbrs_validator.py`, so they never disagree).
- **`pbrs_validator.py`** — now uses that same shared list instead of its own separate one.
- **`pbix_analyzer.py`** — fixed a bug where the PBIX version number was read incorrectly (it's stored as UTF-16, was being read as UTF-8/JSON and usually came back "Unknown").
- **`analyze.py`** — fixed a bug where `--output <folder>` was silently ignored and results always went to `./pbix_analysis` regardless.
- **`pbix_patch.py`** — fixed a small resource leak (a temp file handle wasn't being closed), which on Windows can leave a file locked.
- **`.github` / `skill/`** — the old `skill/` folder (one file) is gone, replaced by `skills/` (9 folders, one per topic).

## How to review without diff

Since you can't use the diff view, the simplest approach:
1. Download the branch zip (as before — branch dropdown → `claude/vizbuilder-pbi-cli-update-h3yn6y` → Code → Download ZIP).
2. Read this file.
3. Open any specific file above directly (double-click it) if you want to see its actual contents — you don't need to compare it against the old version to understand what it does now.
4. Run `python -m unittest discover tests` to confirm all 82 tests still pass on your machine.

## Known limitation (unchanged by this PR)

vizbuilder still cannot create the data model (tables, relationships,
measures) — only the report/visuals layer. See `vizbuilder-modeling` for
why and what to pair it with.
