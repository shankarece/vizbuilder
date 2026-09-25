---
name: VizBuilder Deployment
description: >
  Validate and deploy PBRS .pbix reports built with vizbuilder to Power BI
  Report Server. Invoke this skill whenever the user mentions "deploy",
  "publish to report server", "upload to PBRS", "PBRS compatibility",
  "validate for report server", "file size limit", "unsupported visuals",
  "premium features", "bidirectional relationships", "regenerate
  SecurityBindings", "release checklist", or is preparing a report to go to
  Report Server.
tools: vizbuilder
---

# VizBuilder Deployment Skill

Get a vizbuilder output from "built" to "running on Report Server".

## PBRS Compatibility Validation

```cmd
python pbrs_validator.py file.pbix metadata.json validation.json
```

(`metadata.json` comes from `python analyze.py file.pbix --metadata-only`;
the full `analyze.py` run also produces `<name>_pbrs_validation.json`.)

| Check | What it flags |
|---|---|
| File size | Against the PBRS upload limit |
| Visual types | Visuals not supported on Report Server |
| Relationships | Bidirectional cross-filters (performance) |
| Premium features | Calculated tables and premium-only patterns |
| SecurityBindings | Missing — file must be re-saved in Desktop |
| Version | PBIX version compatibility |
| Performance | Table/column counts, visuals per page |

Severity: **error** blocks deployment, **warning** may cause issues,
**info** is an optimization tip.

A freshly built file **always** warns about missing SecurityBindings — that
is expected until you save it in Desktop.

## Deployment Steps

1. **Build** — `build.bat input.pbix output.pbix --open`
2. **Lint** — `lint.bat output.pbix` (resolve all errors)
3. **Validate** — `python analyze.py output.pbix --output analysis\`, then
   resolve every error in `output_pbrs_validation.json`
4. **Verify in regular Desktop** — every visual renders, no
   "Can't display visual"
5. **File → Save** in regular Desktop (regenerates SecurityBindings)
6. **Open in PBRS Desktop** (same monthly release) to confirm it loads
7. **Upload** to the Report Server web portal (or save to Report Server from
   PBRS Desktop)

## Version Rules

- Regular Desktop and PBRS Desktop must be the **same monthly release**
  (e.g. both September 2024, or both May 2025).
- The Report Server must be on a release that matches or is newer than the
  PBRS Desktop used to save the file.

## Release Checklist

- [ ] No lint errors (overlaps, out-of-bounds)
- [ ] No PBRS validation errors
- [ ] All visuals have titles
- [ ] Saved in Desktop after the last build (SecurityBindings present)
- [ ] Opens in PBRS Desktop without version warnings
- [ ] `.pbix` not committed to git

## Related Skills

- **vizbuilder-diagnostics** — when any step above fails
- **vizbuilder-layout** — fixing lint errors
- **vizbuilder-analysis** — metadata needed by the validator
