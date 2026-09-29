# Getting Started: Build Power BI Dashboards with Devin & Claude

**For new users** - Complete step-by-step guide to building Power BI Report Server dashboards using natural language.

---

## **What You'll Need (5 minutes setup)**

### 1. **Power BI Desktop for Report Server** (Windows)
   - Download from Microsoft
   - Open your `.pbix` file in it
   - Keep it running while building

### 2. **Python 3.10+** (Windows)
   ```bash
   python --version
   ```
   If not installed: https://www.python.org/downloads/

### 3. **vizbuilder** (The Tool)
   - Download from GitHub: https://github.com/shankarece/vizbuilder/releases
   - Extract to `C:\vizbuilder`
   - Test it: `python doctor.bat` in Command Prompt

### 4. **Devin or Claude Code** (The AI)
   - Devin: https://devin.ai
   - Or Claude Code: https://claude.ai/code
   - Both can invoke vizbuilder skills automatically

---

## **The 3-Step Workflow**

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: Prepare                                        │
│  └─ Open your .pbix file in Power BI Desktop           │
│  └─ Have your data model ready                         │
│                                                         │
│  Step 2: Describe                                      │
│  └─ Tell Devin what dashboard you want                 │
│  └─ Example: "Build a sales dashboard with KPIs"      │
│                                                         │
│  Step 3: Review                                        │
│  └─ Check the output in Power BI Desktop               │
│  └─ Iterate: "Make the chart wider" or "Add a slicer" │
│                                                         │
│  Step 4: Save & Deploy                                 │
│  └─ File → Save in Power BI Desktop                    │
│  └─ Publish to Report Server (if needed)               │
└─────────────────────────────────────────────────────────┘
```

---

## **Example 1: Beginner (5 minutes)**

### **Goal:** Create a simple sales dashboard

**Step 1: Prepare**
- Open `C:\work\Sales.pbix` in Power BI Desktop
- Look at the data: Tables like "Orders", "Customers"

**Step 2: Tell Devin**
```
In Devin or Claude Code, say:

"I want to build a Power BI dashboard for sales analysis.
The PBIX file is at C:\work\Sales.pbix.
Please:
1. Inspect the tables and columns
2. Create a dashboard with:
   - Total Sales KPI card
   - Bar chart showing sales by region
   - Donut chart for sales by category
3. Make it fit on one page"
```

**Step 3: Devin responds**
- Reads your PBIX file structure
- Generates Python code for the dashboard
- Builds the PBIX automatically
- Shows you the result

**Step 4: Review in Desktop**
- Look at the built file
- See the visuals and KPIs
- Check if everything looks good

**Step 5: Save**
```
File → Save (in Power BI Desktop)
```

Done! ✅

---

## **Example 2: Intermediate (15 minutes)**

### **Goal:** Executive dashboard with multiple pages

**Step 1: Prepare**
- Have Power BI Desktop open with your data
- Know what metrics you care about: Revenue, Profit, Customers

**Step 2: First Conversation**
```
"Build an executive dashboard for our Superstore data.
Create TWO pages:

PAGE 1 - Executive Summary:
- Four KPI cards at the top: Total Sales, Total Profit, Orders, Customers
- Three charts below: Sales by Region (bar), Sales by Category (donut), 
  Profit Trend (line)

PAGE 2 - Regional Detail:
- Matrix showing Sales & Profit by Region and Product
- Bar chart for top regions
- Customer details table

Make everything fit on standard page size.
The PBIX is at C:\work\Superstore.pbix"
```

**Step 3: Devin/Claude builds**
- Inspects your model
- Generates dashboard Python code
- Builds both pages
- Validates layout (no overlaps, proper spacing)
- Shows you: "Built: C:\work\Superstore_out.pbix"

**Step 4: Iterate in Devin**
- Look at the output in Power BI Desktop
- Ask Devin to adjust:
  ```
  "Make the bar chart on page 2 wider"
  "Add a Region slicer to page 1"
  "Change the donut to a pie chart"
  "Make the KPI cards smaller so more fits on top"
  ```

**Step 5: Review & Save**
- Verify everything in Desktop
- `File → Save`

Done! ✅

---

## **Example 3: Advanced (30 minutes)**

### **Goal:** Complete workflow with model changes + report

**Step 1: Tell Devin the whole story**
```
"I need to build a complete Power BI dashboard project:

Current state:
- PBIX file: C:\work\Sales.pbix
- Tables: Orders, Products, Customers
- No calculated measures yet

What I need:
1. ADD MEASURES to the model:
   - Revenue = Sum(Orders[Sales])
   - Profit = Sum(Orders[Sales]) - Sum(Orders[Cost])
   - Profit Margin = Profit / Revenue
   
2. BUILD A DASHBOARD:
   - Page 1: Executive Summary with 4 KPIs + 3 charts
   - Page 2: Regional drill-down with details
   - Page 3: Customer analysis
   
3. ADD SECURITY:
   - Row-level security: filter by user's region
   
4. VALIDATE:
   - Check layout fits on one page
   - Validate for Power BI Report Server Desktop
   - Generate audit report

Start with step 1, then 2, then 3."
```

**Step 2: Devin orchestrates everything**
- ✅ Adds measures using pbi-cli (if you have it)
- ✅ Builds the dashboard pages
- ✅ Sets up RLS
- ✅ Validates layout and compatibility
- ✅ Generates HTML audit report

**Step 3: Iterate in conversation**
```
"The dashboard looks good, but:
- Make page 1 KPI cards smaller
- Add a date filter for time period selection
- Show profit margin on the KPI row
- Change the color scheme"
```

Devin adjusts and rebuilds. You review and save.

---

## **Common Prompts Cheat Sheet**

Copy-paste these into Devin or Claude Code:

### **Simple Dashboards**
```
"Build a sales dashboard with Total Sales KPI and a chart showing sales by region"

"Create a dashboard with 3 cards (Sales, Profit, Customers) and 2 charts"

"Make a one-page dashboard that fits on a standard report page"
```

### **Multi-Page Dashboards**
```
"Build two pages: Page 1 overview with KPIs, Page 2 with detailed analysis"

"Create an executive dashboard: Page 1 summary, Page 2 regional drill-down, 
Page 3 customer details"
```

### **Adjustments After Building**
```
"Make the bar chart wider and adjust other visuals proportionally"

"The dashboard is too crowded. Reduce chart sizes and make it fit on one page"

"Add a Region slicer that filters all visuals"

"Change the donut chart to a bar chart"

"Make the layout more professional: even spacing, grid alignment"
```

### **Data Model Work**
```
"Add a Revenue measure: Sum(Orders[Sales])"

"Create a profit measure: Sales - Cost"

"Add row-level security by Region"

"Inspect the tables and columns in this model"
```

### **Validation**
```
"Validate the dashboard layout"

"Check if this dashboard is compatible with Power BI Report Server Desktop"

"Generate an audit report for this dashboard"
```

---

## **What Happens Behind the Scenes**

When you tell Devin to build a dashboard:

1. **Devin reads your PBIX** → Inspects tables and columns
2. **Generates Python code** → Creates dashboard configuration
3. **Runs vizbuilder** → Builds the report with visuals
4. **Validates layout** → Checks spacing, alignment, page fit
5. **Shows you results** → Displays the built file path
6. **You review in Desktop** → Open the file, check visuals
7. **You iterate** → Ask Devin to adjust, repeat steps 2-5

---

## **Understanding the Output**

When Devin says:
```
Built: C:\work\Superstore_out.pbix (2,850 KB)
```

This means:
- ✅ Successfully created your dashboard
- ✅ Visuals are added
- ✅ Layout is validated
- ✅ File is ready to open in Power BI Desktop

**Next:** Open `C:\work\Superstore_out.pbix` in Power BI Desktop for Report Server to see it.

---

## **If Something Goes Wrong**

### **Error: "PBIX file not found"**
→ Check the file path: `C:\work\Sales.pbix` should exist

### **Error: "Power BI Desktop not responding"**
→ Open Power BI Desktop and load your PBIX file before building

### **Error: "Measure not found"**
→ Check the measure name matches your model exactly (case-sensitive)

### **Visuals are cut off or overlapping**
→ Tell Devin: "Validate the layout and fix spacing"

### **File is huge (50+ MB)**
→ Normal if you embedded data. Save in Power BI Desktop to compress.

---

## **Tips for Success**

✅ **DO:**
- Keep Power BI Desktop open with your PBIX file
- Be specific: "bar chart by region" not just "chart"
- Iterate: "Make it wider", "Add a slicer", "Change colors"
- Save in Desktop after building: `File → Save`
- Test with sample data first

❌ **DON'T:**
- Close Power BI Desktop while building
- Assume the model has measures if you didn't create them
- Build on network/OneDrive paths (use local C:\ drive)
- Forget to save after making changes

---

## **The Complete Beginner Workflow**

```
1. Open Power BI Desktop
   └─ Open your C:\work\Sales.pbix

2. Open Devin or Claude Code in browser

3. Tell Devin:
   "Build a simple sales dashboard with:
    - Total Sales KPI
    - Sales by Region bar chart
    - File is at C:\work\Sales.pbix"

4. Devin inspects model and builds dashboard
   └─ Shows: "Built: C:\work\Sales_out.pbix"

5. Go to Power BI Desktop
   └─ File → Open → C:\work\Sales_out.pbix
   └─ See your dashboard!

6. Like it? 
   └─ File → Save
   
7. Want to change it?
   └─ Tell Devin: "Make the chart wider"
   └─ Repeat steps 3-6
```

---

## **Next Steps**

- **Done with your first dashboard?** Try a multi-page version
- **Need to add measures?** Tell Devin: "Add a Revenue measure"
- **Want row-level security?** Tell Devin: "Add RLS by Region"
- **Ready to publish?** Save in Desktop, then publish to Report Server

---

## **Resources**

- **vizbuilder repo:** https://github.com/shankarece/vizbuilder
- **Devin AI:** https://devin.ai
- **Claude Code:** https://claude.ai/code
- **vizbuilder Skills:** Available in Devin/Claude Code (auto-loaded)
- **Prompts Guide:** See `AGENT_PROMPTS.md` for 50+ example prompts

---

## **Key Takeaway**

You don't need to write code or understand Python. Just:

1. **Open your PBIX file** in Power BI Desktop
2. **Tell Devin what you want** in plain English
3. **Review the result** in Desktop
4. **Iterate** if needed
5. **Save and deploy**

That's it! 🚀
