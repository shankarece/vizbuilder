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
import re
import sys
import os
import uuid

from visual_types import (
    resolve_visual_type,
    VISUAL_DATA_ROLES,
    ROLE_ALIASES,
    MEASURE_ROLES,
    PLAIN_VALUE_TYPES,
    DEFAULT_SIZES,
    PBRS_VISUAL_NOTES,
)

# ── Container helpers (read layouts written by vizbuilder OR by Desktop) ─────
#
# vizbuilder stores a container's position under "position"; Power BI Desktop
# (and other tools) store x/y/z/width/height directly on the container and often
# have no "id". Anything that reads a saved report must cope with both.

_POS_KEYS = ("x", "y", "z", "width", "height", "tabOrder")
_TOP_LEVEL_POS_KEYS = ("x", "y", "width", "height")


def container_position(vc: dict) -> dict:
    """Return a container's position dict, however the file stores it."""
    nested = vc.get("position")
    if isinstance(nested, dict) and any(k in nested for k in _TOP_LEVEL_POS_KEYS):
        return dict(nested)
    top = {k: vc[k] for k in _POS_KEYS if k in vc}
    if top:
        return top
    try:
        layouts = json.loads(vc.get("config") or "{}").get("layouts") or []
    except (TypeError, ValueError, AttributeError):
        layouts = []
    if layouts and isinstance(layouts[0].get("position"), dict):
        return dict(layouts[0]["position"])
    return {}


def set_container_position(vc: dict, pos: dict) -> None:
    """Write a position back to every place this container keeps one."""
    has_top = any(k in vc for k in _TOP_LEVEL_POS_KEYS)
    if has_top:
        for k in _POS_KEYS:
            if k in pos:
                vc[k] = pos[k]
    if isinstance(vc.get("position"), dict) or not has_top:
        vc["position"] = dict(pos)


def container_id(vc: dict, index: int = 0):
    """A stable id for a container: its "id", else its config name, else #index."""
    if vc.get("id") is not None:
        return vc["id"]
    try:
        name = json.loads(vc.get("config") or "{}").get("name")
    except (TypeError, ValueError, AttributeError):
        name = None
    return name or f"#{index}"


# ── Dashboard title helper ───────────────────────────────────────────────────

def add_title(text: str, x: int = 0, y: int = 0, w: int = 1280, h: int = 50,
              font_size: int = 20, vid: int = 9000) -> dict:
    """Add a dashboard/page title as a textbox visual across the top."""
    guid = str(uuid.uuid4())
    pos = {"x": x, "y": y, "z": 10000, "width": w, "height": h, "tabOrder": 0}
    config = {
        "name": guid,
        "layouts": [{"id": 0, "position": pos}],
        "singleVisual": {
            "visualType": "textbox",
            "objects": {
                "general": [{
                    "properties": {
                        "paragraphs": [{
                            "textRuns": [{
                                "value": text,
                                "textStyle": {
                                    "fontWeight": "bold",
                                    "fontSize": f"{font_size}px",
                                }
                            }],
                            "horizontalTextAlignment": "center",
                        }]
                    }
                }]
            },
            "vcObjects": {},
        }
    }
    return {
        "id": vid,
        "position": pos,
        **{k: pos[k] for k in _POS_KEYS},
        "config": json.dumps(config, separators=(",", ":")),
        "filters": "[]",
        "query": "",
        "dataTransforms": "",
    }


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


def parse_field(ref: str) -> tuple:
    """Parse a binding into (table, name, is_measure).

    'Orders[Sales]'         -> ('Orders', 'Sales', False)      a column
    'Orders[[Total Sales]]' -> ('Orders', 'Total Sales', True) a model measure

    A column in a value role is summed (like Desktop's implicit sum). A measure
    is referenced by name and used as the model defines it (ratios, YTD, ...).
    """
    if "[" not in ref or not ref.endswith("]"):
        raise ValueError(
            f"Invalid field reference: '{ref}'. "
            f"Use Table[Column] for a column or Table[[Measure]] for a measure, "
            f"e.g. 'Orders[Sales]' or 'Orders[[Total Sales]]'"
        )
    table, rest = ref.split("[", 1)
    if rest.startswith("[") and rest.endswith("]]"):
        name, is_measure = rest[1:-2].strip(), True
    else:
        name, is_measure = rest.rstrip("]").strip(), False
    if not table.strip() or not name:
        raise ValueError(
            f"Invalid field reference: '{ref}'. Table and field names cannot be empty."
        )
    return table.strip(), name, is_measure


# Aggregations a binding can ask for: name -> (query function code, select-name
# prefix, display prefix). Codes follow Power BI's QueryAggregateFunction
# (Sum=0, Avg=1, CountNonNull=5), as used in Desktop-authored reports.
AGGREGATIONS = {
    "sum":     (0, "Sum", "Sum of"),
    "avg":     (1, "Avg", "Average of"),
    "average": (1, "Avg", "Average of"),
    "count":   (5, "CountNonNull", "Count of"),
}
_FUNCTION_WRAPPER = re.compile(r"^\s*([A-Za-z]+)\s*\(\s*(.+?)\s*\)\s*$")


def parse_binding(ref: str) -> dict:
    """Parse one binding into {table, name, measure, function}.

    'Orders[Region]'             plain column (or summed on a value axis)
    'Sum(Orders[Sales])'         column with an explicit aggregation
    'Avg(Orders[Discount])'      Sum, Avg or Count
    'Orders[[Profit Ratio]]'     a measure defined in the model
    """
    function = None
    wrapped = _FUNCTION_WRAPPER.match(ref)
    inner = ref
    if wrapped and wrapped.group(1).lower() in AGGREGATIONS:
        function, inner = wrapped.group(1).lower(), wrapped.group(2)
    table, name, is_measure = parse_field(inner)
    if function and is_measure:
        raise ValueError(
            f"'{ref}': a model measure is already aggregated; "
            f"use '{inner}' without {wrapped.group(1)}(...)"
        )
    return {"table": table, "name": name, "measure": is_measure, "function": function}


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

def _measure_expr(column: str, alias: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Source": alias}},
                        "Property": column}}


def _build_select_item(table: str, column: str, is_measure: bool, alias: str = "o",
                       model_measure: bool = False, function: str = "sum"):
    """Build a Select item for the prototypeQuery.

    is_measure    -> a column aggregated on a value axis (function: sum/avg/count)
    model_measure -> a measure defined in the model (Measure reference)
    """
    if model_measure:
        item = _measure_expr(column, alias)
        item["Name"] = f"{table}.{column}"
        item["NativeReferenceName"] = column
        return item
    if is_measure:
        return {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": alias}},
                        "Property": column
                    }
                },
                "Function": AGGREGATIONS[function][0]
            },
            "Name": f"{AGGREGATIONS[function][1]}({table}.{column})"
        }
    else:
        return {
            "Column": {
                "Expression": {"SourceRef": {"Source": alias}},
                "Property": column
            },
            "Name": f"{table}.{column}"
        }

def _build_projection(table: str, column: str, is_measure: bool,
                      model_measure: bool = False, function: str = "sum"):
    """Build a projection entry for singleVisual.projections.

    queryRef must equal the matching Select item's Name or the visual is blank.
    """
    if model_measure:
        return {"queryRef": f"{table}.{column}"}
    query_ref = (f"{AGGREGATIONS[function][1]}({table}.{column})"
                 if is_measure else f"{table}.{column}")
    proj = {"queryRef": query_ref}
    if not is_measure:
        proj["active"] = True
    return proj

def _build_selection(table: str, column: str, is_measure: bool, role: str,
                     model_measure: bool = False, function: str = "sum"):
    """Build a selection metadata entry for dataTransforms."""
    if model_measure:
        query_ref, display = f"{table}.{column}", column
    elif is_measure:
        prefix, shown = AGGREGATIONS[function][1], AGGREGATIONS[function][2]
        query_ref, display = f"{prefix}({table}.{column})", f"{shown} {column}"
    else:
        query_ref, display = f"{table}.{column}", column
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

    # Resolve bindings: friendly name → PBIR role name → parsed field ref.
    # A role may hold one field or a list (e.g. the columns of a table).
    resolved = []  # list of (role, table, column, is_measure)
    field_kinds = []  # parallel: (model_measure: bool, function: str)
    tables_seen = {}  # table → alias

    for user_role, field_refs in bindings.items():
        role = aliases.get(user_role.lower(), user_role)
        if isinstance(field_refs, (list, tuple)):
            refs = list(field_refs)
        else:
            refs = [field_refs]
        for field_ref in refs:
            spec = parse_binding(field_ref)
            table, column = spec["table"], spec["name"]
            if spec["measure"]:
                model_measure, function = True, "sum"
                is_measure = True
            elif spec["function"]:
                model_measure, function = False, spec["function"]
                is_measure = True
            else:
                # Slicers and tables list plain columns; other value roles are
                # aggregated (summed) like Desktop's implicit sum.
                model_measure, function = False, "sum"
                is_measure = role in MEASURE_ROLES and vtype not in PLAIN_VALUE_TYPES
            field_kinds.append((model_measure, function))

            if table not in tables_seen:
                tables_seen[table] = chr(ord("a") + len(tables_seen))
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

    for (role, table, column, is_measure), (model_measure, function) in zip(resolved, field_kinds):
        alias = alias_map[table]
        proj  = _build_projection(table, column, is_measure, model_measure, function)
        sel   = _build_select_item(table, column, is_measure, alias, model_measure, function)
        meta  = _build_selection(table, column, is_measure, role, model_measure, function)

        projections.setdefault(role, []).append(proj)
        selects.append(sel)
        selections.append(meta)

        if model_measure:
            order_by.append({"Direction": 2, "Expression": _measure_expr(column, alias)})
        elif is_measure:
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
                        "Function": AGGREGATIONS[function][0]
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
        **{k: pos[k] for k in _POS_KEYS},
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


def pbrs_visual_warnings(layout: dict) -> list:
    """Return one message per visual whose type may not open in PBRS Desktop."""
    warnings = []
    for sec in layout.get("sections", []):
        page = sec.get("displayName", "?")
        for vc in sec.get("visualContainers", []):
            try:
                sv = json.loads(vc.get("config", "{}")).get("singleVisual", {})
            except (TypeError, ValueError):
                continue
            vtype = sv.get("visualType", "")
            if vtype in PBRS_VISUAL_NOTES:
                reason, instead = PBRS_VISUAL_NOTES[vtype]
                warnings.append(f"{page}: {vtype} -- {reason}; consider {instead}")
    return warnings


def build_layout(pbix_path: str, output_path: str,
                 page_name: str = "Page 1") -> dict:
    """Read layout from PBIX, inject visuals from visuals_config, write out.

    Supports multi-page dashboards via build_pages() in visuals_config.py.
    Falls back to single-page build_visuals() for backwards compatibility.
    Returns the written layout dict.
    """
    import visuals_config as vc

    layout   = read_layout(pbix_path)
    sections = layout.get("sections", [])

    if not sections:
        raise ValueError("No pages (sections) found in Report/Layout.")

    # Multi-page support: if visuals_config defines build_pages(), use it
    if hasattr(vc, "build_pages"):
        pages = vc.build_pages()
        for i, page_def in enumerate(pages):
            pname    = page_def["name"]
            pvisuals = page_def["visuals"]
            ptitle   = page_def.get("title")

            if i < len(sections):
                sec = sections[i]
            else:
                sec = _new_section(i)
                sections.append(sec)

            sec["displayName"] = pname

            containers = []
            if ptitle:
                containers.append(add_title(ptitle, vid=9000 + i))
            containers.extend(pvisuals)
            sec["visualContainers"] = containers

            print(f"  Page {i+1}: {pname}  ({len(pvisuals)} visuals)")

        layout["sections"] = sections
    else:
        # Single-page backwards compatibility
        effective_page = page_name if page_name != "Page 1" else vc.PAGE_NAME
        sections[0]["displayName"] = effective_page

        containers = []
        dashboard_title = getattr(vc, "DASHBOARD_TITLE", None)
        if dashboard_title:
            containers.append(add_title(dashboard_title))
        containers.extend(vc.build_visuals())
        sections[0]["visualContainers"] = containers

        total = len(containers)
        print(f"  Page:    {effective_page}")
        print(f"  Visuals: {total}")

    write_layout(layout, output_path)
    print(f"  Layout:  {output_path}")
    return layout


def _new_section(index: int) -> dict:
    """Create a new blank page/section for multi-page support."""
    return {
        "id": index,
        "name": str(uuid.uuid4()).replace("-", ""),
        "displayName": f"Page {index + 1}",
        "filters": "[]",
        "ordinal": index,
        "visualContainers": [],
        "config": json.dumps({
            "layouts": [{"id": 0, "position": {}}],
            "name": str(uuid.uuid4()),
        }, separators=(",", ":")),
        "displayOption": 1,
        "width": 1280,
        "height": 720,
    }


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
