# How vizbuilder works, step by step

This explains how the parts work together. For the component list and the
diagram, see `../ARCHITECTURE.md`.

## 1. The one fact everything depends on

A `.pbix` file is a zip archive. Three entries matter here:

| Entry | Contents | Who may change it |
|---|---|---|
| `DataModel` | tables, columns, relationships, measures, security roles (a compressed binary) | only a live modeling tool (Power BI Modeling MCP or Desktop). vizbuilder copies it byte-for-byte |
| `Report/Layout` | pages, visuals, field bindings, positions, titles (JSON stored as UTF-16) | vizbuilder |
| `SecurityBindings` | an encrypted integrity check made by Desktop | vizbuilder deletes it; Desktop recreates it on File -> Save |

Because the two layers are separate entries, one tool can rebuild the report
without touching the model. That is the whole design.

## 2. A worked example: "Build a Superstore dashboard"

### Step 0. The prompt
You tell Devin: "Build an executive dashboard from AI Demo.pbix." Devin reads
`AGENTS.md` (the rules) and picks the matching skills from their trigger words
(for example `vizbuilder-report`, `vizbuilder-visuals`, `vizbuilder-pages`).
Skills are plain text. They tell the agent which command to run and which
mistakes to avoid. They do no work themselves.

### Step 1. Model phase (only if the model needs changes)
Devin calls the Power BI Modeling MCP:
- `connection_operations` finds the running Desktop instance with the file open
- `table_operations` lists tables and columns
- `dax_query_operations` runs DAX to test a measure

The MCP changes the model inside the live Desktop session. Nothing is on disk
yet. The file must be saved (File -> Save) and, ideally, Desktop closed.
Reason: step 3 reads the model from the file on disk. An unsaved measure
would be missing from the output.

If the model is already finished, skip this step. It is the slowest part,
because the MCP has to connect and read metadata first.

### Step 2. Discover the real names
```cmd
python analyze.py "C:\work\AI Demo.pbix" --metadata-only --output analysis\
```
`pbix_analyzer.py` opens the zip and writes `AI Demo_metadata.json`: tables,
columns, measures, relationships, pages, visuals. The agent reads this file
and uses the exact names in the next step.

vizbuilder does not check bindings against the model when it builds. A wrong
name builds fine and then shows "Can't display visual" in Desktop. This
discovery step is the protection.

### Step 3. Write the dashboard definition
The agent writes (or edits) a Python file, not the engine. Example:

```python
from layout_builder import add_visual

def build_pages():
    return [{
        "name": "Executive Summary",
        "title": "Superstore - Executive Summary",
        "visuals": [
            add_visual("card", {"value": "Orders[Sales]"},
                       x=20, y=60, w=200, h=100, vid=1, title="Total sales"),
            add_visual("clustered_column",
                       {"category": "Orders[Category]", "value": "Orders[Sales]"},
                       x=20, y=180, w=500, h=250, vid=2, title="Sales by category"),
        ],
    }]
```

Binding syntax:

| You write | Meaning |
|---|---|
| `Orders[Region]` | a column (summed on a value axis, plain elsewhere) |
| `Sum(Orders[Sales])`, `Avg(...)`, `Count(...)` | column with an explicit aggregation |
| `Orders[[Profit Ratio]]` | a measure defined in the model |
| `["Orders[Region]", "Sum(Orders[Sales])"]` | several fields in one role (table columns) |

### Step 4. Build
```cmd
build.bat "C:\work\AI Demo.pbix" "C:\work\AI Demo-Out.pbix" --config my_dashboard.py
```
`build.py` runs two stages.

**Stage A, `layout_builder.build_layout`:**
1. Reads `Report/Layout` from the input file (decodes UTF-16, parses JSON).
2. Loads your definition file and calls `build_pages()`.
3. Each `add_visual(...)` call turns your friendly roles into the legacy
   visual JSON that Report Server uses (the query, the projections, the
   position, the title and formatting).
4. For page number *i* in your list, it takes the existing page *i* of the
   file and **replaces its visuals**. Pages beyond your list are left alone,
   and extra pages in your list are added. It also adds a title box per page.
5. Warns for visual types not confirmed on Report Server Desktop.

**Stage B, `pbix_patch.patch_pbix`:**
1. Creates a new zip at the output path.
2. Skips `SecurityBindings`.
3. Writes the new `Report/Layout`.
4. Copies every other entry unchanged, including `DataModel`.

The input file is never modified. Build refuses to run if the output path
equals the input path.

### Step 5. Verify
```cmd
lint.bat "C:\work\AI Demo-Out.pbix" --report audit.md
python analyze.py "C:\work\AI Demo-Out.pbix" --output analysis\
```
- `lint.py` reads the new layout and checks overlap, out-of-bounds, alignment,
  uneven spacing, mixed sizes, missing titles and grid snap. With `--fix` it
  writes a corrected copy (grid snap, canvas clamp, alignment, sizes, gaps;
  overlaps are reported only).
- `analyze.py` runs a chain. Each step reads the previous step's JSON file:

```
 pbix_analyzer      -> <name>_metadata.json
 data_lineage       -> <name>_lineage.json      (reads metadata)
 consistency_checker-> <name>_violations.json   (reads metadata + lineage)
 metadata_extractor -> data dictionary, measure catalog, relationships, ...
 generate_docs      -> <name>_audit_report.html  (reads all of the above)
 pbrs_validator     -> <name>_pbrs_validation.json
 format_tools audit -> <name>_formatting.json
```
`pbrs_validator` reports on file size, visual types, Premium-only features,
relationships, version and security bindings.

### Step 6. Human check
A built file has no `SecurityBindings`. A person must:
1. Open the output in Power BI Desktop for Report Server.
2. Check the numbers and the visuals.
3. File -> Save. Desktop writes a fresh `SecurityBindings`.
4. Publish to Report Server.

The agent never does this step.

## 3. Who hands what to whom

| Producer | Artifact | Consumer |
|---|---|---|
| You / Devin | prompt | Devin |
| `AGENTS.md`, `skills/*/SKILL.md` | rules and commands | Devin |
| Modeling MCP + Desktop | saved `.pbix` with the model | `analyze.py`, `build.py` |
| `analyze.py --metadata-only` | `*_metadata.json` (real names) | Devin, when writing the definition |
| Devin | dashboard definition `.py` | `build.py` through `layout_builder` |
| `layout_builder` | new `Report/Layout` | `pbix_patch` |
| `pbix_patch` | `output.pbix` | `lint.py`, `analyze.py`, Desktop |
| `lint.py`, `analyze.py`, `format_tools.py` | reports and fixed copies | Devin and the person |
| Desktop (Report Server edition) | final saved `.pbix` | Report Server |

## 4. Why it is arranged this way

- **The model needs a live engine.** Its binary format cannot be written
  safely by hand. The MCP uses the real Tabular Object Model, so the engine
  validates the changes.
- **The report layer is only JSON in a zip.** That makes it editable with the
  Python standard library: no installs, no Desktop, no internet. It also runs
  anywhere, including a locked-down office machine.
- **Neither tool touches the other's layer**, so they cannot undo each
  other's work, as long as they are not run on the same file at the same
  time.
- **Analysis tools only read.** They can run any time without risk, which is
  why they are used both before and after the build.

## 5. Other commands that use the same machinery

| Command | What it does |
|---|---|
| `lint.bat file.pbix --fix` | snaps to the grid, clamps to the canvas, aligns near-aligned visuals, equalizes same-type sizes, evens row gaps; writes a new file. Overlaps are reported, not auto-resolved |
| `format.bat file.pbix --theme theme.json --restyle` | maps colours and fonts to a theme, writes `<name>-restyled.pbix` |
| `python doctor.py` | checks Python and the folder, then runs a self-test build |
| `python install_skill.py` | copies the skills into `~/.claude/skills/` so an agent finds them |
| `python make_release.py` | runs the tests and builds the versioned zip |

## 6. When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| "Can't display visual" | table or column name does not match the model | run `analyze.py --metadata-only`, copy the exact name |
| Visual is blank | wrong binding role, or `[[ ]]` used on something that is not a measure | check the role in `vizbuilder-visuals`; use `Table[Column]` for columns |
| Measure missing in the output | the model was not saved before the build | save in Desktop, then rebuild |
| Desktop will not open the output | file edited while Desktop or OneDrive held it | work in `C:\work`, close Desktop, rebuild |
| Layout cut off | positions exceed the 1280 x 720 canvas | run `lint.bat`, then adjust the coordinates |
| MCP is slow | it has to connect and read metadata each session | skip it when the model is finished |
| `datamodel.tables` empty in metadata | the optional `pbixray` package is not installed | install it, or read the names from the Desktop Data pane |

The `vizbuilder-diagnostics` skill covers these and more.

## 7. What it does not do

- It cannot create tables, relationships, measures or security roles.
- It does not check that a measure returns the right number.
- It does not publish.
- Legends, combo, KPI, gauge, scatter, waterfall and funnel visuals are
  untested on Report Server Desktop. Card, slicer, column/bar/line without a
  legend, donut, table and matrix are confirmed.
