# Five-minute check in Power BI Desktop for Report Server

Everything in vizbuilder has been tested by computer, but **no one has yet opened
its output in *your* Power BI Desktop for Report Server**. This check does that,
in about five minutes, and tells us exactly what works on your version. Do it
**before** any demo.

You need two files (sent with this package):

| File | What it is |
|---|---|
| `northwind_sample.pbix` | A small sample report with made-up data, created by an open-source tool. Untouched. |
| `Northwind-check.pbix` | The same sample after vizbuilder added 21 visuals across 3 pages. |

Copy both to a plain local folder such as `C:\work\` (not OneDrive or a network drive).

## Step 1 - Does your Desktop open the sample?

Open `northwind_sample.pbix` in Power BI Desktop for Report Server.

- **It opens** -> go to step 2.
- **It shows an error** -> write down the exact message and stop. The sample was
  made by a different tool, so this may only mean *that file* is not compatible.
  You can still demo with your own report (see `DEMO_SCRIPT.md`); tell us the message.

## Step 2 - Does vizbuilder's output open, and does page 1 draw?

Open `Northwind-check.pbix`. Page **1 Safe visuals** has 9 visuals. Tick what you see:

| # | Visual | Should show | OK? |
|---|---|---|---|
| 1 | Card: revenue | one number | |
| 2 | Card: Avg Order Value (model measure) | one number | |
| 3 | Card: Order Count (model measure) | one number | |
| 4 | Column: revenue by category | bars with names | |
| 5 | Donut: revenue by segment | coloured ring | |
| 6 | Bar: revenue by product | horizontal bars | |
| 7 | Table | rows of names, segments, revenue, count | |
| 8 | Matrix | regions down, segments across | |
| 9 | Slicer: region | a list of regions you can click | |

Also check that visuals sit where expected (a title bar on top, no overlaps).
A visual that says **"Can't display this visual"** is a failure: click *See details*
and copy the message.

## Step 3 - Which role names does your Desktop accept? (pages 2 and 3)

Some visuals are drawn twice, **A** (what vizbuilder writes today) and **B**
(the names two other tools use). Look at each pair and write down which one
draws correctly:

| Pair | What "draws correctly" means | A | B |
|---|---|---|---|
| Column with legend | bars are split into coloured segments and a legend appears | | |
| Combo chart | columns **and** a line both appear | | |
| Scatter | one dot per product (not a single dot) | | |
| Line with legend (B only) | a separate line per segment | n/a | |
| Stacked bar (B only) | bars split by segment | n/a | |
| KPI | a large number with a goal | | |
| Gauge | a dial | | |
| Waterfall / Funnel | shapes appear | | |

## Step 4 - Does saving work?

In Desktop choose **File -> Save**. Close and reopen the file. Tell us if any
message appeared.

## What to send back

1. The Desktop version (**Help -> About**, e.g. "September 2024").
2. The results of steps 1-4 (a photo of the screen is fine).
3. The exact text of any error.

With that, the role names can be fixed (or confirmed) with evidence, and the
demo can be planned around what is proven to work.
