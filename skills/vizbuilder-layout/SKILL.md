---
name: VizBuilder Layout
description: >
  Audit and auto-fix the visual layout of PBRS .pbix reports with the
  vizbuilder layout linter. Invoke this skill whenever the user mentions
  "lint", "layout issues", "alignment", "align visuals", "overlap",
  "overlapping visuals", "spacing", "uneven gaps", "grid", "snap to grid",
  "resize visuals", "same size", "out of bounds", "tidy the layout", "fix
  layout", "layout audit", or wants to clean up visual positions in an
  existing .pbix without editing visuals_config.py.
tools: vizbuilder
---

# VizBuilder Layout Skill

`lint.py` / `lint.bat` reads `Report/Layout` from any `.pbix` (built by
vizbuilder or not), checks every visual on every page, and can auto-fix the
safe issues. No Power BI Desktop connection is needed.

## Commands

```cmd
REM Audit and print issues
lint.bat file.pbix

REM Audit and save a markdown report
lint.bat file.pbix --report audit.md

REM Auto-fix and write file-fixed.pbix
lint.bat file.pbix --fix

REM Fix, save report, and open the fixed file in Desktop
lint.bat file.pbix --fix --report audit.md --open
```

`--fix` never overwrites the input: it writes `<name>-fixed.pbix` next to it
(with `SecurityBindings` stripped — open it in Desktop and **File → Save**).

## Checks

| Check | Severity | Auto-fixable? |
|---|---|---|
| Overlapping visuals | ERROR | No — reposition in `visuals_config.py` |
| Out of canvas bounds (1280×720) | ERROR | Yes — clamps to canvas |
| Near-aligned positions (within 8 px) | WARNING | Yes — snaps to common edge |
| Missing visual titles | WARNING | No — add `title=` |
| Inconsistent sizes (same type) | INFO | Yes — equalizes |
| Off-grid positions (10 px grid) | INFO | Yes — snaps to grid |
| Uneven horizontal gaps | INFO | Yes — equalizes spacing |
| Too close to canvas edge (< 5 px) | INFO | No — often intentional |

## Report Output

`--report` writes markdown with:

- Visual inventory (page, type, position, size, title)
- Issues grouped by category and severity
- Fixes applied (when `--fix` is used)

## Fixing at the Source

`--fix` patches the built file only. When the report is generated from
`visuals_config.py`, carry the fixes back so the next build doesn't undo them:

1. Run `lint.bat output.pbix --report audit.md`.
2. Update the matching `x`, `y`, `w`, `h` values in `visuals_config.py`
   (snap to multiples of 10, keep 20 px margins and gutters).
3. Rebuild and lint again until there are no errors.

## Workflow: Clean Up a Dashboard

```cmd
REM 1. See what's wrong
lint.bat output.pbix --report audit.md

REM 2. Apply safe fixes and open the result
lint.bat output.pbix --fix --open

REM 3. Resolve remaining ERRORs (overlaps) by editing positions
REM 4. In Desktop: File -> Save
```
