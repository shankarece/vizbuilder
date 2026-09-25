---
name: VizBuilder Diagnostics
description: >
  Troubleshoot vizbuilder builds and the resulting PBRS .pbix files. Invoke
  this skill whenever the user says "vizbuilder not working", "build
  failed", "error", "MashupValidationError", "Can't display visual",
  "unrecognized version", "FileNotFoundError", "visual is blank", "field not
  found", "Desktop won't open the file", "python not found", "setup issues",
  or encounters any vizbuilder error. This is the first skill to check when
  something goes wrong.
tools: vizbuilder
---

# VizBuilder Diagnostics Skill

Troubleshoot the environment, the build, and the output file.

## Environment Check

```cmd
REM Python 3.8+ is the only requirement (no pip installs)
python --version

REM Engine imports cleanly
python -c "import layout_builder, visual_types, pbix_patch; print('ok')"

REM Config imports cleanly (catches syntax errors in visuals_config.py)
python -c "import visuals_config; print('ok')"
```

Run these from the repo root. If `python` is not found, use `py` on Windows.

## Common Errors

| Error / Symptom | Cause | Fix |
|---|---|---|
| `MashupValidationError` on open | Opened the input, or a file whose SecurityBindings wasn't stripped | Open the *output* file |
| "Can't display visual" | Table/column name mismatch | Compare bindings with `datamodel.tables` in `*_metadata.json` or the Desktop Data pane (exact case and spaces) |
| Visual shows wrong totals / error on text field | Text column in an aggregated role (wrapped in `Sum`) | Bind numeric columns to value roles; set "Don't summarize" in Desktop |
| "Unrecognized version" on PBRS | Regular and PBRS Desktop from different months | Use the same monthly release for both |
| `FileNotFoundError` on input | Wrong path | Use an absolute path or run from the PBIX folder |
| `ValueError: Invalid field reference` | Binding not in `Table[Column]` form | Use `"Orders[Sales]"`, not `"Orders.Sales"` |
| `No pages (sections) found` | Input `.pbix` has no report page | Open input in Desktop, add a page, save |
| Visuals missing on page 2+ | `build_pages()` not defined / wrong key | Each page dict needs `name` and `visuals` |
| Visual overlaps the page title | `y` < 50 | Start visuals at `y=60` |
| `--open` does nothing | Desktop not found / not Windows | Open the output file manually |
| Changes lost after rebuild | Edited the output in Desktop, then rebuilt | Rebuild regenerates layout from `visuals_config.py` — put changes there |

## Inspecting the Output

```cmd
REM What did the build actually write?
python analyze.py output.pbix --metadata-only --output debug\

REM Layout problems
lint.bat output.pbix --report debug\lint.md
```

Compare `field_references` in `debug\output_metadata.json` with
`datamodel.tables` in the same file (or the Desktop Data pane) to spot
misspelled fields.

## Workflow: A Visual Won't Render

1. `python analyze.py output.pbix --metadata-only --output debug\`
2. Find the visual in `report` → check its bindings.
3. Find the table in `datamodel.tables` (or the Desktop Data pane) → confirm each column exists with the
   exact name and a suitable (numeric) type for value roles.
4. Fix `visuals_config.py`, rebuild, reopen.

## Best Practices

- Keep the input `.pbix` unchanged; always build to a new output file.
- Change one thing at a time and rebuild.
- Run `lint.bat` after every build.
- Report bugs with the command, full console output, and the
  `*_metadata.json` (not the `.pbix` if it contains real data).
