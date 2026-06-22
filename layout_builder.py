"""
layout_builder.py
-----------------
Core engine: reads Report/Layout from a PBIX, injects visuals, and writes
the modified Layout file. Translates pbi-cli's PBIR binding approach into
the legacy PBIX Layout JSON format.

Supports pbi-cli's Table[Column] field reference syntax for easy binding.

Usage (standalone):
    python layout_builder.py <input.pbix> <output_layout_file>

Normally called by build.py — you don't need to run this directly.
To define your visuals, edit visuals_config.py only.
"""

import zipfile
import json
import sys
import os
import uuid

from visual_types import (
    resolve_visual_type,
    VISUAL_DATA_ROLES,
    ROLE_ALIASES,
    MEASURE_ROLES,
    DEFAULT_SIZES,
)


# ── Field reference parser (pbi-cli style) ───────────────────────────────────

def parse_field_ref(ref: str) -> tuple:
    """Parse 'Table[Column]' into (table, column).

    Examples:
        parse_field_ref("Orders[Sales]")      → ("Orders", "Sales")
        parse_field_ref("Orders[Order Date]") → ("Orders", "Order Date")
    """
    if "[" not in ref or not ref.endswith("]"):
        raise ValueError(
            f"Invalid field reference: '{ref}'. "
            f"Use Table[Column] format, e.g. 'Orders[Sales]'"
        )
    table, col = ref.split("[", 1)
    col = col.rstrip("]")
    return table.strip(), col.strip()


# ── Legacy PBIX query builders ────────────────────────────────────────────────

def _col_expr(table: str, prop: str, alias: str = "o"):
    return {
        "Column": {
            "Expression": {"SourceRef": {"Source": alias}},
            "Property": prop
        }
    }

def _agg_expr(table: str, prop: str, func: int = 0, alias: str = "o"):
    return {
        "Aggregation": {
            "Expression": {
                "Column": {
                    "Expression": {"SourceRef": {"Source": alias}},
                    "Property": prop
                }
            },
            "Function": func
        }
    }

def _build_select_item(table: str, column: str, is_measure: bool, alias: str = "o"):
    """Build a Select item for the prototypeQuery."""
    if is_measure:
        return {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": alias}},
                        "Property": column
                    }
                },
                "Function": 0
            },
            "Name": f"Sum({table}.{column})"
        }
    else:
        return {
            "Column": {
                "Expression": {"SourceRef": {"Source": alias}},
                "Property": column
            },
            "Name": f"{table}.{column}"
        }

def _build_projection(table: str, column: str, is_measure: bool):
    """Build a projection entry for singleVisual.projections."""
    query_ref = f"Sum({table}.{column})" if is_measure else f"{table}.{column}"
    proj = {"queryRef": query_ref}
    if not is_measure:
        proj["active"] = True
    return proj

def _build_selection(table: str, column: str, is_measure: bool, role: str):
    """Build a selection metadata entry for dataTransforms."""
    query_ref = f"Sum({table}.{column})" if is_measure else f"{table}.{column}"
    display   = f"Sum of {column}" if is_measure else column
    return {
        "referenceKey": query_ref,
        "displayName":  display,
        "dataType":     2 if is_measure else 1,
        "roleKind":     2 if is_measure else 1,
        "roles":        [role],
        "queryName":    query_ref
    }


# ── Formatting helpers ───────────────────────────────────────────────────────

_CHART_TYPES_WITH_AXES = frozenset({
    "barChart", "lineChart", "columnChart", "clusteredColumnChart",
    "clusteredBarChart", "stackedBarChart", "areaChart", "ribbonChart",
    "waterfallChart", "lineStackedColumnComboChart",
})

_CHART_TYPES_WITH_LEGEND = frozenset({
    "barChart", "lineChart", "columnChart", "clusteredColumnChart",
    "clusteredBarChart", "stackedBarChart", "areaChart", "ribbonChart",
    "donutChart", "scatterChart", "lineStackedColumnComboChart",
})

def _lit(value) -> dict:
    """Build a Power BI literal expression."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = f"'{value}'"
    return {"expr": {"Literal": {"Value": v}}}


def _auto_title(vtype: str, resolved: list) -> str:
    """Generate a descriptive title from visual type and bound fields."""
    measures = [col for (role, tbl, col, is_m) in resolved if is_m]
    categories = [col for (role, tbl, col, is_m) in resolved if not is_m]

    type_labels = {
        "barChart": "Bar Chart", "lineChart": "Line Chart",
        "columnChart": "Column Chart", "clusteredColumnChart": "Column Chart",
        "clusteredBarChart": "Bar Chart", "stackedBarChart": "Stacked Bar",
        "areaChart": "Area Chart", "ribbonChart": "Ribbon Chart",
        "donutChart": "Donut Chart", "waterfallChart": "Waterfall",
        "funnelChart": "Funnel", "scatterChart": "Scatter Plot",
        "lineStackedColumnComboChart": "Combo Chart", "treemap": "Treemap",
        "card": "", "cardNew": "", "cardVisual": "",
        "multiRowCard": "Details", "tableEx": "Table", "pivotTable": "Matrix",
        "slicer": "Slicer", "kpi": "KPI", "gauge": "Gauge",
        "azureMap": "Map",
    }
    label = type_labels.get(vtype, vtype)

    if measures and categories:
        return f"{', '.join(measures)} by {', '.join(categories)}"
    elif measures:
        if label:
            return f"{', '.join(measures)} — {label}"
        return f"Total {', '.join(measures)}"
    elif categories:
        return f"{label} — {', '.join(categories)}" if label else ', '.join(categories)
    return label or vtype


def _build_formatting_objects(vtype: str, show_labels: bool) -> dict:
    """Build singleVisual.objects with chart formatting."""
    objects = {}

    if vtype in _CHART_TYPES_WITH_AXES:
        objects["categoryAxis"] = [{"properties": {
            "show": _lit(True),
            "showAxisTitle": _lit(True),
        }}]
        objects["valueAxis"] = [{"properties": {
            "show": _lit(True),
            "showAxisTitle": _lit(True),
        }}]
        objects["labels"] = [{"properties": {
            "show": _lit(show_labels),
        }}]

    if vtype in _CHART_TYPES_WITH_LEGEND:
        objects["legend"] = [{"properties": {
            "show": _lit(True),
            "position": _lit("Right"),
        }}]

    if vtype in ("donutChart",):
        objects["labels"] = [{"properties": {
            "show": _lit(True),
            "labelStyle": _lit("Both"),
        }}]

    if vtype in ("card", "cardNew", "cardVisual"):
        objects["labels"] = [{"properties": {
            "show": _lit(True),
        }}]

    if vtype in ("gauge",):
        objects["labels"] = [{"properties": {
            "show": _lit(True),
        }}]

    return objects


def _build_vc_objects(title: str) -> dict:
    """Build singleVisual.vcObjects — the container chrome (title bar)."""
    if not title:
        return {}
    return {
        "title": [{
            "properties": {
                "show": _lit(True),
                "text": _lit(title),
                "fontSize": _lit(12),
            }
        }],
    }


# ── High-level visual builder ────────────────────────────────────────────────

def add_visual(visual_type: str, bindings: dict,
               x: int = None, y: int = None,
               w: int = None, h: int = None,
               vid: int = 0, tab_order: int = 0,
               title: str = None,
               show_labels: bool = False) -> dict:
    """
    Build a complete legacy PBIX visualContainer with formatting.

    Parameters
    ----------
    visual_type : str
        Chart type — canonical name or alias.
    bindings : dict
        Maps role names to field references using Table[Column] syntax.
    x, y : int, optional
        Position in pixels from top-left.
    w, h : int, optional
        Dimensions in pixels.
    vid : int
        Unique visual id on the page.
    tab_order : int
        Tab/z-order index.
    title : str, optional
        Visual title text. Auto-generated from bindings if not provided.
    show_labels : bool
        Show data labels on chart. Default False.

    Returns
    -------
    dict : A visualContainer ready to insert into sections[n].visualContainers
    """
    vtype = resolve_visual_type(visual_type)
    dw, dh = DEFAULT_SIZES.get(vtype, (400, 300))
    x = x if x is not None else 50
    y = y if y is not None else 50
    w = w if w is not None else dw
    h = h if h is not None else dh

    aliases = ROLE_ALIASES.get(vtype, {})

    # Resolve bindings: friendly name → PBIR role name → parsed field ref
    resolved = []  # list of (role, table, column, is_measure)
    tables_seen = {}  # table → alias

    for user_role, field_ref in bindings.items():
        role = aliases.get(user_role.lower(), user_role)
        table, column = parse_field_ref(field_ref)
        is_measure = role in MEASURE_ROLES

        if table not in tables_seen:
            alias = chr(ord("a") + len(tables_seen))
            tables_seen[table] = alias
        resolved.append((role, table, column, is_measure))

    # Use first alias for single-table (most common case)
    alias_map = tables_seen

    # Build From clause
    from_clause = []
    for tbl, als in alias_map.items():
        from_clause.append({"Name": als, "Entity": tbl, "Type": 0})

    # Build projections, selects, selections, order_by
    projections = {}
    selects     = []
    selections  = []
    order_by    = []

    for role, table, column, is_measure in resolved:
        alias = alias_map[table]
        proj  = _build_projection(table, column, is_measure)
        sel   = _build_select_item(table, column, is_measure, alias)
        meta  = _build_selection(table, column, is_measure, role)

        projections.setdefault(role, []).append(proj)
        selects.append(sel)
        selections.append(meta)

        if is_measure:
            order_by.append({
                "Direction": 2,
                "Expression": {
                    "Aggregation": {
                        "Expression": {
                            "Column": {
                                "Expression": {"SourceRef": {"Source": alias}},
                                "Property": column
                            }
                        },
                        "Function": 0
                    }
                }
            })

    # Build query
    query = {"Version": 2, "From": from_clause, "Select": selects}
    if order_by:
        query["OrderBy"] = order_by

    # Auto-generate title from bindings if not provided
    if title is None:
        title = _auto_title(vtype, resolved)

    # Build formatting objects
    objects = _build_formatting_objects(vtype, show_labels)
    vc_objects = _build_vc_objects(title)

    # Build config
    guid = str(uuid.uuid4())
    pos  = {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": tab_order}

    config = {
        "name": guid,
        "layouts": [{"id": 0, "position": pos}],
        "singleVisual": {
            "visualType":     vtype,
            "projections":    projections,
            "prototypeQuery": query,
            "drillFilterOtherVisuals": True,
            "objects":        objects,
            "vcObjects":      vc_objects,
        }
    }

    data_transforms = {
        "selectionMetadata": {
            "version":         6,
            "selectionsCount": len(selections),
            "selections":      selections
        }
    }

    return {
        "id":             vid,
        "position":       pos,
        "config":         json.dumps(config,          separators=(",", ":")),
        "filters":        "[]",
        "query":          json.dumps(query,            separators=(",", ":")),
        "dataTransforms": json.dumps(data_transforms,  separators=(",", ":"))
    }


# ── Layout read / write ───────────────────────────────────────────────────────

def read_layout(pbix_path: str) -> dict:
    """Extract and parse Report/Layout from a PBIX file."""
    with zipfile.ZipFile(pbix_path, "r") as z:
        raw = z.read("Report/Layout")
    text = raw.decode("utf-16-le").lstrip("﻿")
    return json.loads(text)


def write_layout(layout: dict, output_path: str) -> None:
    """Serialise layout dict and write as UTF-16 LE."""
    out_json  = json.dumps(layout, separators=(",", ":"), ensure_ascii=False)
    out_bytes = out_json.encode("utf-16-le")
    with open(output_path, "wb") as f:
        f.write(out_bytes)


def build_layout(pbix_path: str, output_path: str,
                 page_name: str = "Page 1") -> None:
    """Read layout from PBIX, inject visuals from visuals_config, write out."""
    from visuals_config import PAGE_NAME, build_visuals

    layout   = read_layout(pbix_path)
    sections = layout.get("sections", [])

    if not sections:
        raise ValueError("No pages (sections) found in Report/Layout.")

    effective_page = page_name if page_name != "Page 1" else PAGE_NAME
    sections[0]["displayName"]      = effective_page
    sections[0]["visualContainers"] = build_visuals()

    write_layout(layout, output_path)

    count = len(sections[0]["visualContainers"])
    print(f"  Page:    {effective_page}")
    print(f"  Visuals: {count}")
    print(f"  Layout:  {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        print("Usage: python layout_builder.py <input.pbix> <output_layout_file> [page_name]")
        sys.exit(1)

    pbix_path   = sys.argv[1]
    output_path = sys.argv[2]
    page_name   = sys.argv[3] if len(sys.argv) > 3 else "Page 1"

    if not os.path.exists(pbix_path):
        print(f"Error: PBIX not found: {pbix_path}")
        sys.exit(1)

    try:
        build_layout(pbix_path, output_path, page_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
