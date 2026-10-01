# vizbuilder architecture

How the pieces fit together, what goes in and out of each one, and what each
skill is for. Written for a technical lead who wants to understand the tool.

## 1. The problem it solves

A Power BI Report Server (PBRS) `.pbix` file has two independent layers:

| Layer | What it holds | Where it lives in the file |
|---|---|---|
| Data model | tables, columns, relationships, DAX measures, row-level security | `DataModel` (compressed Analysis Services binary) |
| Report layer | pages, visuals, bindings, positions, titles | `Report/Layout` (JSON) |

No single offline tool edits both. So the work is split: a live modeling tool
builds the model, vizbuilder builds the report layer, an AI agent coordinates
them from plain-English prompts, and a person does the final check.

## 2. End-to-end flow

```
 PROMPT (plain English)
    |
    v
 AGENT (Devin) -- reads AGENTS.md + skills/ for rules and commands
    |
    |-- 1. MODEL PHASE  (needs Power BI Desktop running)
    |      Power BI Modeling MCP  ->  tables, relationships, DAX, RLS
    |      human/agent then: File -> Save (close Desktop)
    |
    |-- 2. DISCOVER     (offline, read-only)
    |      analyze.py --metadata-only  ->  real table/column/measure names
    |
    |-- 3. BUILD        (offline)
    |      dashboard definition (.py)  +  input.pbix
    |      build.py -> layout_builder -> pbix_patch  ->  output.pbix
    |
    |-- 4. VERIFY       (offline, read-only)
    |      lint.py (layout)  +  analyze.py (lineage, consistency, PBRS check, docs)
    |
    v
 HUMAN: open output.pbix in Power BI Desktop for Report Server,
        check numbers, File -> Save, publish
```

Rule: model first, save, then build. `build.py` copies the model from the
file on disk, so an unsaved model is missing from the output.

## 3. Components: inputs and outputs

### 3.1 Power BI Modeling MCP (data model layer, live)
- **What it is:** an MCP server the agent calls. It connects to a running
  Power BI Desktop session and edits the model through the Tabular Object
  Model.
- **Tool groups seen in use:** `connection_operations` (find and connect to the
  open Desktop instance), `table_operations` (list/get tables and columns),
  `dax_query_operations` (run DAX), plus partition, calendar and transaction
  operations.
- **In:** a connection to the open file, plus agent instructions such as
  "add measure Profit Ratio" or "list tables".
- **Out:** changes inside the live Desktop session. They exist only in memory
  until **File -> Save**.
- **Requires:** Power BI Desktop running with the file open. This is why it is
  slow compared with the offline tools. Each session has to connect and read
  metadata first.
- **Does not do:** pages, visuals, layout.

### 3.2 vizbuilder build engine (report layer, offline)
Standard library Python only. No Desktop, no internet.

| File | Role | In | Out |
|---|---|---|---|
| `visuals_config.py` or your own config (`--config`) | The dashboard definition: pages, visuals, bindings, positions | written by you or the agent | read by the engine |
| `visual_types.py` | Supported visual types, aliases, data roles, PBRS-safe list | n/a | rules used by the engine |
| `layout_builder.py` | Turns the definition into legacy `Report/Layout` JSON. Parses bindings: `Table[Column]`, `Sum(Table[Col])`, `Table[[Measure]]` | input `.pbix` + definition | layout JSON |
| `pbix_patch.py` | Writes the output zip: replaces `Report/Layout`, removes `SecurityBindings`, copies `DataModel` byte-for-byte | input `.pbix` + layout JSON | `output.pbix` |
| `build.py` / `build.bat` | Command-line driver for the three above, prints PBRS compatibility warnings, optional `--open` | `input.pbix output.pbix [--config file]` | `output.pbix` |
| `desktop.py` | Finds and launches Power BI Desktop (prefers the Report Server edition) for `--open` | n/a | opens the file |

Why `SecurityBindings` is removed: Desktop stores an encrypted integrity check
there, and any external edit to the file makes Desktop refuse it. Removing it
lets the file open. Desktop regenerates it on the next **File -> Save**. That is
why a built file must be opened and saved in Desktop before deployment.

The input file is never overwritten.

### 3.3 Layout linter
- `lint.py` / `lint.bat`
- **In:** any `.pbix`. **Out:** a report of overlap, misalignment, uneven
  gaps, inconsistent sizing, out-of-bounds visuals and missing titles. With
  `--fix` it writes a corrected copy.

### 3.4 Analysis suite (verification and documentation, offline, read-only)
Run as one command: `python analyze.py file.pbix --output analysis\`.

| Step | File | Output |
|---|---|---|
| Metadata | `pbix_analyzer.py` | `<name>_metadata.json`: tables, columns, measures, relationships, pages, visuals, `SecurityBindings` status |
| Lineage | `data_lineage.py` | which visuals use which fields; which measures depend on which tables |
| Consistency | `consistency_checker.py` | naming, sizing, alignment, titles, unused or orphaned fields, hidden objects |
| PBRS validation | `pbrs_validator.py` | compatibility errors and warnings (file size, unsupported visuals, Premium-only features, version, relationships) |
| Documentation | `metadata_extractor.py`, `generate_docs.py` | data dictionary, measure catalog, relationship map, HTML audit report with health score |

It reads structure. It does not judge whether a DAX measure returns the right
number.

### 3.5 Formatting audit and restyle
- `format_tools.py` / `format.bat`, documented in the `vizbuilder-analysis` skill.
- **In:** any `.pbix`, optionally a theme JSON (font, colour palette, title
  size). **Out:** an audit of mixed fonts, off-palette colours and inconsistent
  number formats. With `--restyle` it writes a new `<name>-restyled.pbix` with
  every visual mapped to the theme. The original is untouched. Number formats
  are flagged, not changed. The audit also runs as the last step of `analyze.py`.

### 3.6 Support tools
- `doctor.py` / `doctor.bat`: checks Python, folder contents, and runs a
  self-test build.
- `install_skill.py`: copies the skills into `~/.claude/skills/` so an agent
  can find them.
- `make_release.py`: builds the versioned zip with the sample files.

## 4. The skills: what each is for

Skills are instruction files in `skills/<name>/SKILL.md`. They contain no
code. They tell the AI agent when to act and which command to run. Each has
trigger words in its description so the agent picks the right one.

| Skill | Purpose | Typical request |
|---|---|---|
| `vizbuilder-modeling` | Handoff between the live model tool (MCP, pbi-cli) and vizbuilder: order of operations, save/close rules | "create measures", "build the model first" |
| `vizbuilder-report` | The overall workflow from input `.pbix` to deployable output; file format, Desktop editions | "build the pbix", "how does this work" |
| `vizbuilder-visuals` | How to add visuals: types, binding roles, `Table[Column]` syntax | "add a bar chart of sales by region" |
| `vizbuilder-pages` | Multi-page reports, tab names, page titles, layout patterns | "add a second page" |
| `vizbuilder-layout` | Run the linter and fix alignment, overlap, sizing | "fix the spacing" |
| `vizbuilder-analysis` | Metadata, lineage, orphaned fields, consistency, formatting audit and restyle; also used to get real field names before binding | "which columns are unused" |
| `vizbuilder-docs` | Generate data dictionary, measure catalog, HTML audit report | "document this report" |
| `vizbuilder-deployment` | PBRS validation and the release checklist | "is this ready for Report Server" |
| `vizbuilder-diagnostics` | First stop when something fails: build errors, blank visuals, Desktop won't open | "build failed", "visual is blank" |

`AGENTS.md` at the repo root is the entry point. It lists the skills, the
commands, and the rules the agent must follow, for example: edit only the
dashboard definition, never overwrite the input, check real names first, and
never publish.

## 5. Division of responsibility

| Task | Who does it |
|---|---|
| Understand the prompt, choose steps, write the dashboard definition | AI agent, guided by skills |
| Tables, relationships, DAX measures, RLS | Power BI Modeling MCP (live) |
| Visuals, pages, layout in the file | vizbuilder (offline) |
| Check structure, layout, PBRS compatibility, produce documents | analysis suite and linter (offline) |
| Check the numbers, save, publish | a person |

## 6. Guardrails

- Input file is never overwritten; output goes to a new path.
- The data model is copied byte-for-byte; vizbuilder never changes it.
- Build prints a compatibility warning for visuals not confirmed on Report
  Server Desktop.
- Confirmed on Report Server Desktop: card, slicer, column/bar/line without a
  legend, donut, table, matrix. Unconfirmed: any legend, combo, KPI, gauge,
  scatter, waterfall, funnel.
- The agent must not publish. Opening in Desktop and saving is a human step.
- Automated tests cover the engine, bindings, analysis, release packaging and
  skills.

## 7. Known limits

- The data model cannot be created offline; it needs a live Desktop session.
- Layout is set by coordinates, so each build needs a visual check in Desktop.
- Model-metadata reading in the analysis step may use an optional library. If
  `datamodel.tables` comes back empty, check the install.
- Report Server has fewer visuals and features than the cloud service.

## 8. Quick reference

```cmd
python doctor.py
python analyze.py in.pbix --metadata-only --output analysis\
build.bat in.pbix out.pbix --config my_dashboard.py
lint.bat out.pbix --report audit.md
python analyze.py out.pbix --output analysis\
```
