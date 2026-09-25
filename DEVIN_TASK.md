# Devin task: add test coverage for the core engine

This file exists so this task can be copied from GitHub directly (e.g. on a
machine that can't reach the Claude session that wrote it). It is not part
of vizbuilder's own docs or skills — delete it once the task is done and its
output has been merged.

## Task

Add four new test modules under `tests/`, covering code that
`tests/test_skills.py` and `tests/test_pbrs.py` don't already exercise.
**Do not modify `tests/test_skills.py` or `tests/test_pbrs.py`.**

- **`tests/test_visual_types.py`** — `resolve_visual_type` (aliases, unknown
  type errors, case sensitivity); cross-check `VISUAL_TYPE_ALIASES` all map
  to entries in `SUPPORTED_VISUAL_TYPES`; every `SUPPORTED_VISUAL_TYPES`
  entry has a `VISUAL_DATA_ROLES` entry and a `DEFAULT_SIZES` entry; every
  role alias in `ROLE_ALIASES` targets a role declared in
  `VISUAL_DATA_ROLES` for that type.

- **`tests/test_layout_builder.py`** — `parse_field_ref` (valid + malformed
  refs), `add_visual` (resulting config/query/dataTransforms structure,
  correct projections, multi-table aliasing), `add_title`, and
  `write_layout`/`read_layout` round-tripping UTF-16 LE correctly.

- **`tests/test_pbix_patch.py`** — build a small fake PBIX zip and verify
  `patch_pbix` strips `SecurityBindings`, replaces `Report/Layout`, keeps
  `DataModel` as `ZIP_STORED`, copies all other entries unchanged, and
  raises on a missing input file or missing layout file.

- **`tests/test_consistency_checker.py`** — the `Violation` class, each
  individual checker function (titles, sizing, alignment, hidden objects,
  measures) on small hand-built metadata/lineage dicts, and
  `ConsistencyAnalyzer.analyze`'s summary and severity sorting.

Use `unittest`, standard library only, no network access, matching the
style already in `tests/test_skills.py` and `tests/test_pbrs.py`.

## When done

Run:

```
python -m unittest discover tests
```

It must include the existing 22 tests still passing (26 total once the four
new modules are added). Report the full result.
