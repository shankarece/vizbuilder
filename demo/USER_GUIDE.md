# Building a Power BI report with your AI assistant

For people who use Power BI but do not write code. You describe the report in
plain words; the assistant builds it; you check it in Power BI Desktop and
publish it. Your data stays on your computer and Report Server. Nothing is sent
to the internet by this tool.

## Before you start (once per report)

1. **Have a report file that already contains your data.** Someone opens
   Power BI Desktop for Report Server, loads the data, sets up the model, and
   saves a `.pbix`. This is the *starting file*. (The assistant can help with
   the model too; see your team's notes.)
2. **Copy it to a plain folder such as `C:\work\`.** Not OneDrive, SharePoint or
   a network drive, and close it in Desktop.
3. Ask the assistant to check the setup: *"Run doctor.py and tell me if this
   computer is ready."* Anything marked `[XX]` needs fixing first.

## The four steps

**1. Ask.** Say what you want, naming the file. Example:

> Using C:\work\Sales.pbix, build an executive dashboard: four cards across the
> top, a Region slicer, sales by category and profit by sub-category. Save it as
> C:\work\Sales-Out.pbix.

More examples are in `PROMPTS.md`.

**2. Read what it says back.** The assistant will tell you what it built, and
warn you if something may not work on Report Server (for example a map). Ask it
to explain or change anything you do not like.

**3. Open the new file in Power BI Desktop for Report Server.** Look at every
page. Check the numbers against something you trust. If something is wrong, go
back to step 1 and ask for the change ("make the cards smaller", "swap the
donut for a bar chart"). Each change takes seconds.

**4. Save and publish.** In Desktop choose **File -> Save**, then publish to
Report Server as you normally do. *This step is always yours.* A file straight
from the assistant is not ready to publish until you have saved it in Desktop.

## What you can ask for

Cards (single numbers), column and bar charts, line and area charts, donut charts,
tables, matrices, slicers (filters), several pages, page titles, and tidy layout.
Use plain names from your data: "sales by region", "profit by sub-category".

## What to check yourself

- The **numbers**. The assistant arranges visuals; it does not know your business
  rules. Compare a total with a report you trust.
- Anything **new to your data model**: measures such as "profit ratio" must
  already exist in the model. Ask: "which measures does this report have?"
- That the report **opens and looks right** on the Report Server before sharing.

## If something goes wrong

| What you see | What to do |
|---|---|
| A visual says "Can't display this visual" | Tell the assistant which one and paste the message. Usually a field name is wrong. |
| Desktop will not open the file | Open your *original* file instead, and tell the assistant the error text. |
| The assistant says a file is "in use" or "not found" | Close it in Desktop; use a folder like `C:\work\`. |
| Nothing seems to happen for minutes | The file may be in OneDrive or a network folder. Copy it to `C:\work\`. |
| You are unsure the setup is right | Ask it to run `doctor.py`. |

## Ground rules

- Your original file is never changed; every build writes a **new** file.
- Do not put files with real customer data into shared folders or emails.
- The assistant suggests; **you** approve. Nothing is published without you.
