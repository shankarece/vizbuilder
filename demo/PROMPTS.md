# Ready-to-use prompts

Type these to your AI assistant (Devin, Windsurf, Claude Code). Replace the
parts in [brackets]. The assistant reads `AGENTS.md` and the skills in this
folder for the rules, so you only describe *what* you want.

## Check first

> Run doctor.py and tell me in plain words whether this computer is ready.

> Look at [C:\work\Sales.pbix]. List the tables, the columns and the measures
> it contains, and tell me which ones no visual uses.

## Build a dashboard

> Using [C:\work\Sales.pbix], build an executive dashboard: four cards across the
> top (total sales, total profit, units sold, average discount), a Region slicer,
> sales by category, sales by segment and profit by sub-category. Save the result
> as [C:\work\Sales-Out.pbix]. Then check the layout and tell me anything wrong.

> Build a two-page report from [C:\work\Sales.pbix]. Page 1 is an overview with
> the key numbers. Page 2 shows sales by region in a matrix and a table of
> customers. Keep it simple and use only visuals that work on Report Server.

## Change what is there

> Make the four cards on page 1 the same size and put them in one row.

> Add a Segment slicer on the left of page 1 and move the charts to make room.

> Replace the donut chart with a clustered bar chart of sales by region.

> Add a third page called "Returns" with a table of returned orders.

> Rename page 2 to "Regions" and change its title to "Sales by Region".

## Check and hand over

> Run the full analysis on [C:\work\Sales-Out.pbix] and summarise: layout
> problems, unused fields, and anything that would stop it working on Report Server.

> Write a one-page description of this report for the team: what each page
> shows and which fields it uses.

> Tell me exactly what I should check in Power BI Desktop before I save and publish.

## What a good assistant will do

- Ask which file and which fields if you are not specific.
- Never overwrite your original file.
- Tell you the last steps are yours: open in Desktop, look, **File -> Save**, publish.
