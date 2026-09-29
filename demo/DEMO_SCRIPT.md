# Demo script: AI-assisted Power BI development on Report Server

**Audience:** your lead and interested colleagues. **Length:** about 20 minutes.
**Message:** *A business user describes a report in plain words. An AI assistant
builds it on the approved data model in seconds. A person reviews it in Power BI
Desktop and publishes it to our own Report Server. It runs on our machines, with
no cloud service and no data leaving the building.*

## 1. Before the day (do this, do not skip it)

| Task | Why |
|---|---|
| Run the **five-minute check** in `VERIFY_IN_DESKTOP.md` | It is the only proof the output works in *your* Desktop version. Do it first. |
| Run `python doctor.py` on the demo computer | Proves the tool works there. |
| Put the demo file (Superstore `Demo.pbix`) in `C:\work\`, saved in Desktop | Avoids OneDrive slowness and locked files. |
| Do a **full dry run** of section 3, with the clock | Live demos fail on the first surprise. |
| Prepare the fallbacks in section 5 | So a failure is a 30-second detour. |
| Close every other program; turn off notifications | Less to go wrong on screen. |

Rehearse with the exact prompts in `PROMPTS.md`.

## 2. The story (3 minutes, no screen)

1. Today: a request for a report waits for a specialist; changes take days.
2. What we show: the same request, described in plain language, drafted in seconds.
3. What does **not** change: our data model, Report Server, security, and a
   person who reviews and publishes. The assistant drafts; people decide.

## 3. Live demo (12 minutes)

| # | Say | Do | Time |
|---|---|---|---|
| 1 | "First, is this computer ready?" | Run `doctor.bat`. Show the green `[OK]` lines. | 1 |
| 2 | "Here is our Superstore report with its data and model." | Open `Demo.pbix` in Desktop for a few seconds: show the Data pane. Close it. | 1 |
| 3 | "A business user asks for a dashboard in plain words." | Paste the **executive dashboard** prompt from `PROMPTS.md` into the assistant. | 1 |
| 4 | "While it works: it reads the rules for our environment and builds a new file. Our original is never touched." | Point at the assistant's steps. Show the build finishing in seconds. | 2 |
| 5 | "It checked its own work." | Show the layout check and any Report Server warning it printed. | 1 |
| 6 | "Now a person reviews it." | Open `Demo-Out.pbix` in Desktop for Report Server. Page through both pages. Click the Region slicer. | 3 |
| 7 | "Changes take seconds." | Ask: *"Add a Segment slicer on the left and make the cards the same size."* Rebuild, reopen. | 2 |
| 8 | "And we can audit it." | Run the full analysis; open the HTML audit report: health score, unused fields, Report Server compatibility. | 1 |
| 9 | "Last step is human: save and publish." | **File -> Save**. Show the publish menu (do not publish the demo). | 1 |

If the assistant is slow or unavailable, use the manual fallback (section 5).

## 4. Honest limits (say these before you are asked)

- The assistant builds the **report layer** (pages and visuals) on a model that
  already exists. Loading data and designing the model is done first, live, with
  a modeling tool; that is a separate step.
- It supports the common visuals. A few (maps, the newest cards and slicers) may
  not exist in every Report Server Desktop release, and it warns about them.
- A person always reviews in Desktop and saves before publishing. That is a
  feature: it keeps a human accountable.
- It is new. Pilot it with one team and one report first.

## 5. If something goes wrong

| Problem | Do this |
|---|---|
| Assistant is slow or errors | Run the build yourself: `build.bat "C:\work\Demo.pbix" "C:\work\Demo-Out.pbix" --config demo\superstore_dashboard.py --open` |
| Output will not open | Open the pre-built `Demo-Backup.pbix` you saved in Desktop the day before. Say: "here is the result from earlier". |
| A visual shows an error | Note it, carry on, and say what you would ask the assistant to change. Do not debug live. |
| Column names differ from Superstore | Edit the names at the top of `demo\superstore_dashboard.py` (one block). |

Always keep a **backup file**: build the dashboard the day before, open it in
Desktop, **File -> Save As -> `Demo-Backup.pbix`**.

## 6. Likely questions

| Question | Honest answer |
|---|---|
| Does data leave our network? | The tool makes no network connections (a test enforces it). Your assistant product's own data handling is a separate question for security to confirm. |
| Can it break our reports? | It never overwrites the original; it writes a new file that a person reviews. |
| Will it work on our Report Server version? | It targets the classic `.pbix` format. We verified it in our Desktop version on [date] (see the check). |
| Who maintains it? | It is a small, dependency-free Python program in one folder; see `START_HERE.md`. |
| What does it cost? | vizbuilder itself needs no licence or subscription. Your assistant product and Power BI licences are separate. |
| What is next? | Pilot with one team; add approved templates; add automated publishing after security review. |

## 7. The ask

Approve a small pilot: one team, one report, four weeks. Success = a business user
produces a reviewed report on Report Server in under an hour, and reviewers say the
layout needed little rework.
