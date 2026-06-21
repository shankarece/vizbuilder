"""
layout_builder.py
-----------------
Core engine: reads Report/Layout from a PBIX, injects visuals defined in
visuals_config.py, and writes a modified Layout file (UTF-16 LE encoded).

Works with any PBI Desktop version — Sept 2024, May 2025, or later.

Usage (standalone):
    python layout_builder.py <input.pbix> <output_layout_file> [page_name]

Normally called by build.py — you don't need to run this directly.
To define your own visuals, edit visuals_config.py only.
"""

import zipfile
import json
import sys
import os
import uuid


# ── Query builder helpers (used by visuals_config.py) ────────────────────────

def col_select(prop: str, name: str, alias: str = "o") -> dict:
    """A SELECT item for a plain column (grouping/axis field)."""
    return {
        "Column": {
            "Expression": {"SourceRef": {"Source": alias}},
            "Property": prop
        },
        "Name": name
    }


def agg_select(prop: str, name: str, func: int = 0, alias: str = "o") -> dict:
    """A SELECT item for an aggregated column.
    func: 0=Sum, 1=Avg, 2=Min, 3=Max, 4=Count
    """
    return {
        "Aggregation": {
            "Expression": {
                "Column": {
                    "Expression": {"SourceRef": {"Source": alias}},
                    "Property": prop
                }
            },
            "Function": func
        },
        "Name": name
    }


def order_by_agg(prop: str, direction: int = 2, alias: str = "o") -> list:
    """An ORDER BY clause on an aggregated column.
    direction: 1=Ascending, 2=Descending
    """
    return [{
        "Direction": direction,
        "Expression": {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": alias}},
                        "Property": prop
                    }
                },
                "Function": 0
            }
        }
    }]


def sel(ref_key: str, display_name: str, data_type: int,
        role_kind: int, roles: list) -> dict:
    """A selection metadata entry that binds a field to a visual role.

    data_type:  1=Text/Category  2=Decimal/Number  4=DateTime
    role_kind:  1=Grouping (axis/legend)  2=Measure (values)
    roles:      visual-type-specific role name, e.g. ["Category"], ["Y"], ["Values"]
    """
    return {
        "referenceKey":  ref_key,
        "displayName":   display_name,
        "dataType":      data_type,
        "roleKind":      role_kind,
        "roles":         roles,
        "queryName":     ref_key
    }


def make_visual(vid: int, tab_order: int,
                x: int, y: int, w: int, h: int,
                visual_type: str,
                projections: dict,
                selects: list,
                selections: list,
                table: str,
                order_by: list = None) -> dict:
    """
    Build a complete visualContainer dict for the Report/Layout.

    Parameters
    ----------
    vid         : unique integer id for this visual on the page
    tab_order   : tab/z-order index (0 = first)
    x, y        : position in pixels from top-left of canvas
    w, h        : width and height in pixels
    visual_type : PBI internal chart type string (see visuals_config.py)
    projections : dict mapping role names to query field references
    selects     : list of col_select / agg_select items
    selections  : list of sel() metadata items
    table       : data model table name
    order_by    : optional order_by_agg() list
    """
    guid  = str(uuid.uuid4())
    pos   = {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": tab_order}
    query = {
        "Version": 2,
        "From": [{"Name": "o", "Entity": table, "Type": 0}],
        "Select": selects
    }
    if order_by:
        query["OrderBy"] = order_by

    config = {
        "name": guid,
        "layouts": [{"id": 0, "position": pos}],
        "singleVisual": {
            "visualType":     visual_type,
            "projections":    projections,
            "prototypeQuery": query,
            "objects":        {}
        }
    }

    data_transforms = {
        "selectionMetadata": {
            "version":        6,
            "selectionsCount": len(selections),
            "selections":     selections
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

    # Layout is UTF-16 LE, with or without BOM
    text = raw.decode("utf-16-le").lstrip("﻿")
    return json.loads(text)


def write_layout(layout: dict, output_path: str) -> None:
    """Serialise layout dict and write as UTF-16 LE (no BOM)."""
    out_json  = json.dumps(layout, separators=(",", ":"), ensure_ascii=False)
    out_bytes = out_json.encode("utf-16-le")
    open(output_path, "wb").write(out_bytes)


def build_layout(pbix_path: str, output_path: str,
                 page_name: str = "Page 1") -> None:
    """
    Read layout from pbix_path, inject visuals from visuals_config,
    and write to output_path.
    """
    from visuals_config import PAGE_NAME, TABLE, build_visuals

    layout   = read_layout(pbix_path)
    sections = layout.get("sections", [])

    if not sections:
        raise ValueError("No pages (sections) found in Report/Layout.")

    effective_page = page_name if page_name != "Page 1" else PAGE_NAME
    sections[0]["displayName"]      = effective_page
    sections[0]["visualContainers"] = build_visuals(TABLE)

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
