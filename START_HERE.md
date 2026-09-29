# vizbuilder - start here

vizbuilder lets an AI assistant (or a person) build the **pages and visuals** of a
Power BI Report Server report, in seconds, on a report file that already has its
data. It runs entirely on your computer with plain Python: no internet, no cloud,
no extra packages, no PowerShell. Nothing is installed system-wide.

## Set up (10 minutes, once per computer)

1. **Unzip** the package to a plain folder, for example `C:\tools\vizbuilder-<version>\`.
2. **Check the computer.** Double-click `doctor.bat` (or run `python doctor.py`).
   You need Python 3.8 or newer. Lines marked `[OK]` are fine; `[!!]` are notes;
   `[XX]` must be fixed. It proves the tool works here by building a small test report.
3. **Optional: give your AI assistant the skills.** Run `python install_skill.py`.
   The assistant also reads `AGENTS.md` in this folder automatically if you open
   the folder in it. Restart the assistant after installing.

## Which document is for me?

| I am... | Read |
|---|---|
| A business user who wants a report built | `demo\USER_GUIDE.md`, then `demo\PROMPTS.md` |
| Giving a demo to my lead | `demo\DEMO_SCRIPT.md` (and do `demo\VERIFY_IN_DESKTOP.md` first; its two sample files are in `demo\verify\`) |
| A developer or administrator | `README.md`, `AGENTS.md`, `skills\` |
| Having a problem | Run `doctor.bat`; then `skills\vizbuilder-diagnostics\SKILL.md` |
| Sharing this with colleagues | `README.md`, section "Sharing vizbuilder with colleagues" |

## The whole flow in one picture

```
report file with data  --(1) ask for a dashboard-->  assistant runs vizbuilder
   (saved in Power BI           |                            |
    Desktop for Report          |                            v
    Server, in C:\work\)        |                  NEW file (original untouched)
                                |                            |
                                +----(3) ask for changes<----+ (2) you open it in Desktop and look
                                                             |
                                            (4) File -> Save, then publish (always a person)
```

## Command line, if you prefer it

```cmd
build.bat "C:\work\Sales.pbix" "C:\work\Sales-Out.pbix" --config "C:\work\my_dashboard.py" --open
lint.bat "C:\work\Sales-Out.pbix"
python analyze.py "C:\work\Sales-Out.pbix" --output "C:\work\analysis"
```

`demo\superstore_dashboard.py` is a complete example to copy. Keep your own
config files outside this folder so upgrading never overwrites them.

## Ground rules

- Every build writes a **new** file. The original is never modified.
- A built file has to be opened in Power BI Desktop for Report Server and saved
  (**File -> Save**) before it is published. That step is always a person's.
- Work in a plain local folder, not OneDrive, SharePoint or a network drive.
- Do not commit or email `.pbix` files that contain real data.

## Known limits

- It builds the report layer. Loading data and designing the data model is a
  separate, earlier step (see `skills\vizbuilder-modeling\SKILL.md`).
- Not every visual exists in every Report Server Desktop release; the build warns
  about the risky ones.
- Read `CHANGELOG.md` for what changed and what is still unconfirmed.
