# Agent Orchestrator Prompts Guide

Interactive prompts for building Power BI Report Server dashboards with natural language.

---

## **For Power BI Developers**

### Data Model & DAX

```
>> Inspect tables and columns in this model
>> Show all measures in the model
>> Add a measure: Revenue = Sum(Sales[Amount])
>> Create a profit measure: Profit = Sum(Sales[Amount]) - Sum(Sales[Cost])
>> Add Year-to-Date measure: YTD Sales = TOTALYTD(SUM(Sales[Amount]), Date[Date])
>> Fix this measure: change Sum to Average
>> Show data lineage: which columns are used by which visuals?
```

### Row-Level Security (RLS)

```
>> Add row-level security by Region
>> Set up RLS: filter Sales table by current user's region
>> Create RLS for Manager role: show only their team's data
>> Add security: Territory managers see only their territory
```

### Model Analysis

```
>> Find unused columns in this model
>> Show orphaned measures not used in any visual
>> Validate naming conventions: camel case or underscore?
>> List all calculated columns and their DAX
>> Show table relationships and cardinality
```

---

## **For Building Dashboards (Developers)**

### Basic Visuals

```
>> Build a dashboard with Total Sales KPI
>> Add a bar chart showing sales by region
>> Create a line chart for sales over time
>> Add a donut chart for sales by category
>> Build a matrix showing region by product sales
>> Add a table with customer details and totals
```

### Multi-Page Dashboards

```
>> Create two pages: Executive Summary and Regional Detail
>> Build page 1 with KPIs and overview charts
>> Add page 2 with drill-down details and analysis
>> Create page layout: top row KPIs, middle charts, bottom table
```

### Advanced Layouts

```
>> Build an executive dashboard: KPIs at top, 4 key charts in 2x2 grid
>> Create a row layout: card, bar chart, line chart, donut
>> Add a slicer for Region to filter all visuals
>> Build: 2 KPIs left column, 1 large chart right, table below
>> Make the bar chart wider and adjust other visuals proportionally
```

### Layout & Spacing

```
>> Validate the dashboard layout (check overlaps and spacing)
>> Fix alignment: snap all visuals to grid
>> Auto-space the visuals evenly
>> Adjust canvas size to fit all visuals without scrolling
>> Make visuals fit on one page (PBRS Desktop standard)
>> Reduce chart sizes to fit landscape orientation
```

### Visual Types & Formatting

```
>> Replace the donut chart with a pie chart
>> Change bar chart to column chart
>> Add data labels to the sales chart
>> Show percentage of total in the donut chart
>> Add a trend line to the sales chart
```

---

## **For Non-Technical Users (Business Users)**

### Simple Dashboard Requests

```
>> Create a sales dashboard
>> Build a profit by region dashboard
>> Make a customer analysis dashboard
>> Create a product performance dashboard
>> Build a regional sales comparison
```

### Specific Metrics

```
>> Show me total sales
>> Add a card for total profit
>> Create a KPI for customer count
>> Show average order value
>> Display year-to-date sales
```

### Charts & Visuals

```
>> Add a chart showing sales by region
>> Create a chart for top 10 products
>> Show sales by customer segment
>> Create a trend chart for sales over time
>> Add a comparison chart for this year vs last year
```

### Multi-Page Dashboards

```
>> Create two pages: one for overview, one for details
>> Build a dashboard with summary and drill-down
>> Create tabs for different regions
>> Make pages for Sales, Profit, and Customers
```

### Layout & Polish

```
>> Make the dashboard look professional
>> Arrange everything neatly on one page
>> Make it print-friendly
>> Adjust sizes so everything fits without scrolling
```

---

## **For Analysis & Troubleshooting (Developers)**

### Validation & Diagnostics

```
>> Validate this dashboard for PBRS compatibility
>> Check for PBRS Desktop warnings
>> Find visuals with missing data
>> Identify slow-performing queries
>> Show query performance analysis
```

### Data Issues

```
>> Find missing or null values in this column
>> Show records where Sales is empty
>> Identify duplicate customers
>> Find inconsistent category names
```

### Report Quality

```
>> Generate a data quality audit report
>> Create a metadata report showing all tables and columns
>> Generate documentation for this dashboard
>> Create a data dictionary for stakeholders
>> Make an HTML audit report with quality score
```

---

## **Layout & Canvas Management**

The orchestrator automatically:

✅ **Validates layout** - checks for overlaps, even spacing, grid alignment  
✅ **Adjusts canvas** - fits visuals to PBRS page size (8.5" x 11" standard)  
✅ **Handles responsive** - adjusts for Report Server Desktop viewport  
✅ **Manages spacing** - applies 10px grid, even gaps between visuals  
✅ **Prevents overflow** - warns if content exceeds page boundaries  
✅ **Auto-spaces** - distributes visuals evenly when requested  

### Layout Prompts

```
>> Validate the dashboard layout
   → Checks for overlaps, uneven spacing, alignment issues

>> Auto-space all visuals
   → Distributes charts evenly with consistent gaps

>> Fit everything on one page
   → Adjusts sizes to fit PBRS standard canvas

>> Check for canvas overflow
   → Shows if any visuals extend beyond page boundaries

>> Adjust layout for portrait orientation
   → Resizes for vertical layout (if needed)

>> Make this responsive for different screen sizes
   → Suggests responsive breakpoints
```

---

## **Multi-Step Workflows**

### Example 1: From Scratch to Dashboard

```
>> Inspect the model
   ↓ Shows tables: Orders, Products, Customers
   
>> Add a revenue measure
   ↓ Creates: Revenue = Sum(Orders[Amount])
   
>> Build a dashboard with KPI and chart
   ↓ Generates: Total Revenue card + Sales by Region chart
   
>> Make it professional: add a slicer and title
   ↓ Adds Region slicer, formats properly
   
>> Validate the layout
   ↓ Checks spacing, alignment, canvas fit
```

### Example 2: Executive Dashboard

```
>> Create an executive summary with 4 KPIs
   ↓ Cards: Total Sales, Total Profit, Customer Count, Avg Order
   
>> Add key charts: sales by region, category, trend
   ↓ 3-chart row below KPIs
   
>> Add a summary table
   ↓ Table with top customers/products
   
>> Fix layout and spacing
   ↓ Auto-aligns everything, checks for overlaps
   
>> Validate for PBRS Desktop
   ↓ Confirms compatibility and page fit
```

### Example 3: Multi-Page Analysis

```
>> Create page 1: Overview with KPIs and summary
>> Create page 2: Regional drill-down
>> Create page 3: Customer analysis
>> Add slicers to filter all pages
>> Validate all pages fit properly
```

---

## **Tips for Best Results**

1. **Start Simple** - Begin with "Build a dashboard with sales KPI and chart"
2. **Be Specific** - "bar chart by region" better than "chart"
3. **Iterate** - "Make the chart wider", "Add a slicer", "Change colors"
4. **Check Layout** - Ask "validate the layout" to catch spacing issues
5. **Test Desktop** - Always verify in Power BI Desktop for Report Server

---

## **Unsupported in PBRS Desktop** ⚠️

These visual types are unconfirmed on Report Server Desktop. Use only if required:
- Chart legends
- Combo charts
- KPI visuals (card recommended)
- Gauge/dials
- Scatter plots
- Waterfall charts
- Funnel charts

**Confirmed Safe:** Card, Slicer, Column/Bar/Line (no legend), Donut, Table, Matrix

---

## **API Mode vs Template Mode**

### With Claude API (`ANTHROPIC_API_KEY` set)
- Intelligent prompt understanding
- Complex workflows
- Multi-step reasoning
- Layout optimization

### Template-Guided Mode (No API)
- Pattern-based keywords
- Simple workflows
- Guided steps
- Still works offline

Both modes automatically handle layout validation and canvas management.
