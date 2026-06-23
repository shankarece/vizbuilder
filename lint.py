"""
lint.py
-------
Audit and fix Power BI PBIX visual layouts.

Checks for: overlapping visuals, misalignment, inconsistent sizing,
out-of-bounds visuals, missing titles, uneven spacing, and more.

Usage:
    python lint.py <file.pbix>                   # audit and print report
    python lint.py <file.pbix> --fix              # auto-fix and write corrected PBIX
    python lint.py <file.pbix> --report out.md    # save audit report as markdown
    python lint.py <file.pbix> --fix --open       # fix and auto-open in Desktop

Compatible with September 2024 and May 2025 PBRS Desktop versions.
"""

import sys
import os
import json
import math
import zipfile
import tempfile
from collections import defaultdict

from layout_builder import read_layout, write_layout
from pbix_patch import patch_pbix

# ── Canvas constants ─────────────────────────────────────────────────────────

CANVAS_W = 1280
CANVAS_H = 720
SNAP_GRID = 10
ALIGN_TOLERANCE = 8
MIN_VISUAL_W = 40
MIN_VISUAL_H = 30
MIN_MARGIN = 5


# ── Data extraction ──────────────────────────────────────────────────────────

def _extract_visuals(layout: dict) -> list:
    """Extract all visuals with position and metadata from all pages."""
    results = []
    for si, sec in enumerate(layout.get("sections", [])):
        page_name = sec.get("displayName", f"Page {si+1}")
        for vc in sec.get("visualContainers", []):
            pos = vc.get("position", {})
            config_str = vc.get("config", "{}")
            try:
                config = json.loads(config_str)
            except (json.JSONDecodeError, TypeError):
                config = {}

            sv = config.get("singleVisual", {})
            vtype = sv.get("visualType", "unknown")
            name = config.get("name", "?")

            vc_objs = sv.get("vcObjects", {})
            title_entries = vc_objs.get("title", [])
            has_title = False
            title_text = ""
            if title_entries:
                props = title_entries[0].get("properties", {})
                show = props.get("show", {}).get("expr", {}).get("Literal", {}).get("Value", "false")
                if show == "true":
                    has_title = True
                    text_expr = props.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "")
                    title_text = text_expr.strip("'")

            results.append({
                "page_index": si,
                "page_name": page_name,
                "id": vc.get("id", "?"),
                "name": name[:12],
                "type": vtype,
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "w": pos.get("width", 0),
                "h": pos.get("height", 0),
                "z": pos.get("z", 0),
                "has_title": has_title,
                "title_text": title_text,
                "_vc": vc,
                "_config": config,
            })
    return results


# ── Issue classes ────────────────────────────────────────────────────────────

class Issue:
    def __init__(self, severity, category, message, page, visuals=None, fix=None):
        self.severity = severity   # "error", "warning", "info"
        self.category = category   # "overlap", "alignment", "bounds", etc.
        self.message = message
        self.page = page
        self.visuals = visuals or []
        self.fix = fix             # callable(visual_list) -> None, or None

    def __repr__(self):
        icon = {"error": "X", "warning": "!", "info": "i"}[self.severity]
        return f"[{icon}] {self.category}: {self.message} (page: {self.page})"


# ── Check functions ──────────────────────────────────────────────────────────

def _rects_overlap(a, b) -> bool:
    return not (a["x"] + a["w"] <= b["x"] or
                b["x"] + b["w"] <= a["x"] or
                a["y"] + a["h"] <= b["y"] or
                b["y"] + b["h"] <= a["y"])


def _overlap_area(a, b) -> int:
    ox = max(0, min(a["x"]+a["w"], b["x"]+b["w"]) - max(a["x"], b["x"]))
    oy = max(0, min(a["y"]+a["h"], b["y"]+b["h"]) - max(a["y"], b["y"]))
    return ox * oy


def check_overlaps(visuals: list) -> list:
    issues = []
    by_page = defaultdict(list)
    for v in visuals:
        by_page[v["page_index"]].append(v)

    for pi, vlist in by_page.items():
        for i in range(len(vlist)):
            for j in range(i+1, len(vlist)):
                a, b = vlist[i], vlist[j]
                if _rects_overlap(a, b):
                    area = _overlap_area(a, b)
                    if area > 100:
                        issues.append(Issue(
                            "error", "overlap",
                            f"{a['type']} (id={a['id']}) overlaps {b['type']} (id={b['id']}) "
                            f"by {area}sq-px",
                            a["page_name"], [a, b],
                        ))
                    elif area > 0:
                        issues.append(Issue(
                            "warning", "overlap",
                            f"{a['type']} (id={a['id']}) slightly overlaps {b['type']} (id={b['id']}) "
                            f"by {area}sq-px",
                            a["page_name"], [a, b],
                        ))
    return issues


def check_bounds(visuals: list) -> list:
    issues = []
    for v in visuals:
        problems = []
        if v["x"] < 0:
            problems.append(f"x={v['x']} < 0")
        if v["y"] < 0:
            problems.append(f"y={v['y']} < 0")
        if v["x"] + v["w"] > CANVAS_W:
            overshoot = v["x"] + v["w"] - CANVAS_W
            problems.append(f"right edge exceeds canvas by {overshoot}px")
        if v["y"] + v["h"] > CANVAS_H:
            overshoot = v["y"] + v["h"] - CANVAS_H
            problems.append(f"bottom edge exceeds canvas by {overshoot}px")
        if problems:
            issues.append(Issue(
                "error", "bounds",
                f"{v['type']} (id={v['id']}): {'; '.join(problems)}",
                v["page_name"], [v],
            ))
    return issues


def check_alignment(visuals: list) -> list:
    issues = []
    by_page = defaultdict(list)
    for v in visuals:
        if v["type"] != "textbox":
            by_page[v["page_index"]].append(v)

    for pi, vlist in by_page.items():
        if len(vlist) < 2:
            continue

        # Check for near-aligned tops (same row but slightly off)
        y_groups = defaultdict(list)
        for v in vlist:
            placed = False
            for gy in y_groups:
                if abs(v["y"] - gy) <= ALIGN_TOLERANCE and abs(v["y"] - gy) > 0:
                    y_groups[gy].append(v)
                    placed = True
                    break
            if not placed:
                y_groups[v["y"]].append(v)

        for gy, group in y_groups.items():
            ys = set(v["y"] for v in group)
            if len(ys) > 1:
                names = ", ".join(f"{v['type']}(id={v['id']},y={v['y']})" for v in group)
                issues.append(Issue(
                    "warning", "alignment",
                    f"Near-aligned tops (within {ALIGN_TOLERANCE}px): {names} --consider aligning to y={gy}",
                    group[0]["page_name"], group,
                ))

        # Check for near-aligned lefts (same column but slightly off)
        x_groups = defaultdict(list)
        for v in vlist:
            placed = False
            for gx in x_groups:
                if abs(v["x"] - gx) <= ALIGN_TOLERANCE and abs(v["x"] - gx) > 0:
                    x_groups[gx].append(v)
                    placed = True
                    break
            if not placed:
                x_groups[v["x"]].append(v)

        for gx, group in x_groups.items():
            xs = set(v["x"] for v in group)
            if len(xs) > 1:
                names = ", ".join(f"{v['type']}(id={v['id']},x={v['x']})" for v in group)
                issues.append(Issue(
                    "warning", "alignment",
                    f"Near-aligned lefts (within {ALIGN_TOLERANCE}px): {names} --consider aligning to x={gx}",
                    group[0]["page_name"], group,
                ))

    return issues


def check_sizing(visuals: list) -> list:
    issues = []
    by_page = defaultdict(list)
    for v in visuals:
        if v["type"] not in ("textbox", "shape", "image", "actionButton"):
            by_page[v["page_index"]].append(v)

    for pi, vlist in by_page.items():
        # Check for too-small visuals
        for v in vlist:
            if v["w"] < MIN_VISUAL_W or v["h"] < MIN_VISUAL_H:
                issues.append(Issue(
                    "warning", "sizing",
                    f"{v['type']} (id={v['id']}) is very small: {v['w']}x{v['h']}px",
                    v["page_name"], [v],
                ))

        # Check for inconsistent card sizes
        type_groups = defaultdict(list)
        for v in vlist:
            type_groups[v["type"]].append(v)

        for vtype, group in type_groups.items():
            if len(group) < 2:
                continue
            sizes = set((v["w"], v["h"]) for v in group)
            if len(sizes) > 1:
                desc = ", ".join(f"id={v['id']}:{v['w']}x{v['h']}" for v in group)
                issues.append(Issue(
                    "info", "consistency",
                    f"{vtype} visuals have inconsistent sizes: {desc}",
                    group[0]["page_name"], group,
                ))

    return issues


def check_spacing(visuals: list) -> list:
    issues = []
    by_page = defaultdict(list)
    for v in visuals:
        if v["type"] not in ("textbox", "shape", "image"):
            by_page[v["page_index"]].append(v)

    for pi, vlist in by_page.items():
        if len(vlist) < 2:
            continue

        # Check for visuals too close to canvas edge
        for v in vlist:
            if 0 < v["x"] < MIN_MARGIN:
                issues.append(Issue(
                    "info", "spacing",
                    f"{v['type']} (id={v['id']}) is only {v['x']}px from left edge",
                    v["page_name"], [v],
                ))
            right_margin = CANVAS_W - (v["x"] + v["w"])
            if 0 < right_margin < MIN_MARGIN:
                issues.append(Issue(
                    "info", "spacing",
                    f"{v['type']} (id={v['id']}) is only {right_margin}px from right edge",
                    v["page_name"], [v],
                ))

        # Check for uneven horizontal gaps between visuals in the same row
        rows = defaultdict(list)
        for v in vlist:
            row_key = v["y"] // 30
            rows[row_key].append(v)

        for rk, row in rows.items():
            if len(row) < 3:
                continue
            row_sorted = sorted(row, key=lambda v: v["x"])
            gaps = []
            for i in range(len(row_sorted) - 1):
                gap = row_sorted[i+1]["x"] - (row_sorted[i]["x"] + row_sorted[i]["w"])
                gaps.append(gap)
            if len(set(gaps)) > 1:
                gap_desc = ", ".join(f"{g}px" for g in gaps)
                issues.append(Issue(
                    "info", "spacing",
                    f"Uneven horizontal gaps in row (y~{row_sorted[0]['y']}): [{gap_desc}]",
                    row_sorted[0]["page_name"], row_sorted,
                ))

    return issues


def check_titles(visuals: list) -> list:
    issues = []
    skip_types = {"textbox", "shape", "image", "actionButton", "pageNavigator"}
    for v in visuals:
        if v["type"] in skip_types:
            continue
        if not v["has_title"]:
            issues.append(Issue(
                "warning", "title",
                f"{v['type']} (id={v['id']}) has no title",
                v["page_name"], [v],
            ))
    return issues


def check_grid_snap(visuals: list) -> list:
    issues = []
    for v in visuals:
        if v["type"] in ("textbox",):
            continue
        off_x = v["x"] % SNAP_GRID
        off_y = v["y"] % SNAP_GRID
        if off_x != 0 or off_y != 0:
            issues.append(Issue(
                "info", "grid",
                f"{v['type']} (id={v['id']}) not on {SNAP_GRID}px grid: "
                f"({v['x']},{v['y']}) ->suggest ({_snap(v['x'])},{_snap(v['y'])})",
                v["page_name"], [v],
            ))
    return issues


def _snap(val: int) -> int:
    return round(val / SNAP_GRID) * SNAP_GRID


# ── Auto-fix ─────────────────────────────────────────────────────────────────

def auto_fix(layout: dict) -> tuple:
    """Apply automatic fixes to layout. Returns (fixed_layout, fix_log)."""
    fixes = []

    for si, sec in enumerate(layout.get("sections", [])):
        page_name = sec.get("displayName", f"Page {si+1}")
        vcs = sec.get("visualContainers", [])

        parsed = []
        for vc in vcs:
            pos = vc.get("position", {})
            config_str = vc.get("config", "{}")
            try:
                config = json.loads(config_str)
            except (json.JSONDecodeError, TypeError):
                config = {}
            parsed.append({
                "vc": vc, "pos": pos, "config": config,
                "type": config.get("singleVisual", {}).get("visualType", "unknown"),
                "id": vc.get("id", "?"),
            })

        # Fix 1: Snap to grid
        for p in parsed:
            ox, oy = p["pos"].get("x", 0), p["pos"].get("y", 0)
            nx, ny = _snap(ox), _snap(oy)
            if nx != ox or ny != oy:
                p["pos"]["x"] = nx
                p["pos"]["y"] = ny
                fixes.append(f"[{page_name}] {p['type']}(id={p['id']}): snapped ({ox},{oy}) ->({nx},{ny})")

        # Fix 2: Clamp to canvas bounds
        for p in parsed:
            changed = False
            if p["pos"].get("x", 0) < 0:
                p["pos"]["x"] = 0
                changed = True
            if p["pos"].get("y", 0) < 0:
                p["pos"]["y"] = 0
                changed = True
            w = p["pos"].get("width", 0)
            h = p["pos"].get("height", 0)
            if p["pos"]["x"] + w > CANVAS_W:
                p["pos"]["x"] = CANVAS_W - w
                if p["pos"]["x"] < 0:
                    p["pos"]["x"] = 0
                    p["pos"]["width"] = CANVAS_W
                changed = True
            if p["pos"]["y"] + h > CANVAS_H:
                p["pos"]["y"] = CANVAS_H - h
                if p["pos"]["y"] < 0:
                    p["pos"]["y"] = 0
                    p["pos"]["height"] = CANVAS_H
                changed = True
            if changed:
                fixes.append(f"[{page_name}] {p['type']}(id={p['id']}): clamped to canvas bounds")

        # Fix 3: Align near-aligned visuals (snap to majority position)
        non_text = [p for p in parsed if p["type"] != "textbox"]
        if len(non_text) >= 2:
            # Align tops
            y_groups = defaultdict(list)
            for p in non_text:
                placed = False
                for gy in list(y_groups.keys()):
                    if abs(p["pos"]["y"] - gy) <= ALIGN_TOLERANCE:
                        y_groups[gy].append(p)
                        placed = True
                        break
                if not placed:
                    y_groups[p["pos"]["y"]].append(p)

            for gy, group in y_groups.items():
                ys = [p["pos"]["y"] for p in group]
                if len(set(ys)) > 1:
                    target_y = _snap(round(sum(ys) / len(ys)))
                    for p in group:
                        if p["pos"]["y"] != target_y:
                            old_y = p["pos"]["y"]
                            p["pos"]["y"] = target_y
                            fixes.append(f"[{page_name}] {p['type']}(id={p['id']}): aligned y={old_y} ->{target_y}")

            # Align lefts
            x_groups = defaultdict(list)
            for p in non_text:
                placed = False
                for gx in list(x_groups.keys()):
                    if abs(p["pos"]["x"] - gx) <= ALIGN_TOLERANCE:
                        x_groups[gx].append(p)
                        placed = True
                        break
                if not placed:
                    x_groups[p["pos"]["x"]].append(p)

            for gx, group in x_groups.items():
                xs = [p["pos"]["x"] for p in group]
                if len(set(xs)) > 1:
                    target_x = _snap(round(sum(xs) / len(xs)))
                    for p in group:
                        if p["pos"]["x"] != target_x:
                            old_x = p["pos"]["x"]
                            p["pos"]["x"] = target_x
                            fixes.append(f"[{page_name}] {p['type']}(id={p['id']}): aligned x={old_x} ->{target_x}")

        # Fix 4: Equalize sizes of same-type visuals
        type_groups = defaultdict(list)
        for p in non_text:
            type_groups[p["type"]].append(p)

        for vtype, group in type_groups.items():
            if len(group) < 2:
                continue
            sizes = set((p["pos"].get("width", 0), p["pos"].get("height", 0)) for p in group)
            if len(sizes) > 1:
                widths = [p["pos"].get("width", 0) for p in group]
                heights = [p["pos"].get("height", 0) for p in group]
                w_diff = max(widths) - min(widths)
                h_diff = max(heights) - min(heights)
                if w_diff <= 30 and h_diff <= 30:
                    target_w = _snap(round(sum(widths) / len(widths)))
                    target_h = _snap(round(sum(heights) / len(heights)))
                    for p in group:
                        ow, oh = p["pos"].get("width"), p["pos"].get("height")
                        if ow != target_w or oh != target_h:
                            p["pos"]["width"] = target_w
                            p["pos"]["height"] = target_h
                            fixes.append(f"[{page_name}] {p['type']}(id={p['id']}): equalized size {ow}x{oh} ->{target_w}x{target_h}")

        # Fix 5: Even out horizontal gaps for visuals in the same row
        rows = defaultdict(list)
        for p in non_text:
            row_key = p["pos"]["y"] // 30
            rows[row_key].append(p)

        for rk, row in rows.items():
            if len(row) < 3:
                continue
            row_sorted = sorted(row, key=lambda p: p["pos"]["x"])
            first_x = row_sorted[0]["pos"]["x"]
            total_visual_w = sum(p["pos"].get("width", 0) for p in row_sorted)
            last_right = row_sorted[-1]["pos"]["x"] + row_sorted[-1]["pos"].get("width", 0)
            total_span = last_right - first_x
            total_gap = total_span - total_visual_w
            if total_gap > 0 and len(row_sorted) > 1:
                even_gap = _snap(total_gap // (len(row_sorted) - 1))
                cursor = first_x
                for p in row_sorted:
                    if p["pos"]["x"] != cursor:
                        old_x = p["pos"]["x"]
                        p["pos"]["x"] = cursor
                        fixes.append(f"[{page_name}] {p['type']}(id={p['id']}): evened gap x={old_x} ->{cursor}")
                    cursor += p["pos"].get("width", 0) + even_gap

        # Write back positions into config + vc
        for p in parsed:
            pos = p["pos"]
            p["vc"]["position"] = pos
            cfg = p["config"]
            if "layouts" in cfg and cfg["layouts"]:
                cfg["layouts"][0]["position"] = pos
            p["vc"]["config"] = json.dumps(cfg, separators=(",", ":"))

    return layout, fixes


# ── Report generation ────────────────────────────────────────────────────────

def generate_report(visuals: list, issues: list, fixes: list = None) -> str:
    """Generate a markdown audit report."""
    lines = []
    lines.append("# PBIX Layout Audit Report\n")

    # Summary
    errors   = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos    = sum(1 for i in issues if i.severity == "info")
    lines.append(f"**Visuals scanned:** {len(visuals)}  ")
    lines.append(f"**Issues found:** {errors} errors, {warnings} warnings, {infos} info\n")

    # Visual inventory
    lines.append("## Visual Inventory\n")
    lines.append("| Page | ID | Type | Position | Size | Title |")
    lines.append("|---|---|---|---|---|---|")
    for v in visuals:
        title = v["title_text"] if v["has_title"] else "(none)"
        lines.append(
            f"| {v['page_name']} | {v['id']} | {v['type']} | "
            f"({v['x']},{v['y']}) | {v['w']}x{v['h']} | {title} |"
        )
    lines.append("")

    # Issues by category
    if issues:
        lines.append("## Issues\n")
        cats = defaultdict(list)
        for i in issues:
            cats[i.category].append(i)

        severity_icon = {"error": "ERROR", "warning": "WARN", "info": "INFO"}
        for cat, cat_issues in cats.items():
            lines.append(f"### {cat.title()}\n")
            for i in cat_issues:
                icon = severity_icon[i.severity]
                lines.append(f"- **[{icon}]** {i.message}")
            lines.append("")
    else:
        lines.append("## Issues\n")
        lines.append("No issues found. Layout looks clean!\n")

    # Fixes applied
    if fixes:
        lines.append("## Fixes Applied\n")
        for f in fixes:
            lines.append(f"- {f}")
        lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def lint(pbix_path: str, do_fix: bool = False, report_path: str = None,
         auto_open: bool = False) -> tuple:
    """Run all checks on a PBIX file. Returns (issues, visuals, fixes)."""

    layout = read_layout(pbix_path)
    visuals = _extract_visuals(layout)

    print(f"\n  Scanning {len(visuals)} visuals across "
          f"{len(layout.get('sections', []))} page(s)...\n")

    # Run all checks
    issues = []
    issues.extend(check_overlaps(visuals))
    issues.extend(check_bounds(visuals))
    issues.extend(check_alignment(visuals))
    issues.extend(check_sizing(visuals))
    issues.extend(check_spacing(visuals))
    issues.extend(check_titles(visuals))
    issues.extend(check_grid_snap(visuals))

    # Sort by severity
    severity_order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_order[i.severity])

    # Print summary
    errors   = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos    = sum(1 for i in issues if i.severity == "info")

    for i in issues:
        icon = {"error": "X", "warning": "!", "info": "i"}[i.severity]
        print(f"  [{icon}] {i.category}: {i.message}")

    print(f"\n  Summary: {errors} errors, {warnings} warnings, {infos} info")

    # Auto-fix
    fixes = []
    if do_fix:
        layout = read_layout(pbix_path)
        layout, fixes = auto_fix(layout)

        if fixes:
            out_path = pbix_path.replace(".pbix", "-fixed.pbix")
            with tempfile.NamedTemporaryFile(suffix=".layout", delete=False) as tmp:
                layout_tmp = tmp.name
            write_layout(layout, layout_tmp)
            patch_pbix(pbix_path, layout_tmp, out_path)
            os.remove(layout_tmp)

            print(f"\n  Applied {len(fixes)} fixes:")
            for f in fixes:
                print(f"    - {f}")
            print(f"\n  Fixed file: {out_path}")

            if auto_open:
                import subprocess
                abs_path = os.path.abspath(out_path)
                os.startfile(abs_path)
                print(f"  Opening in Desktop...")
        else:
            print(f"\n  No fixes needed --layout is clean.")

    # Generate report
    if report_path:
        report = generate_report(visuals, issues, fixes)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  Report saved: {report_path}")

    return issues, visuals, fixes


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        print(__doc__)
        print("Usage: python lint.py <file.pbix> [--fix] [--report out.md] [--open]")
        sys.exit(1)

    pbix_path = args[0]
    if not os.path.exists(pbix_path):
        print(f"Error: File not found: {pbix_path}")
        sys.exit(1)

    do_fix = "--fix" in flags
    auto_open = "--open" in flags
    report_path = None
    for i, f in enumerate(flags):
        if f == "--report" and i + 1 < len(flags):
            report_path = flags[i + 1]
        elif f == "--report":
            report_path = args[0].replace(".pbix", "-audit.md")

    # Handle --report path from positional args
    if "--report" in flags and report_path is None:
        report_path = pbix_path.replace(".pbix", "-audit.md")
    if "--report" in flags and report_path and report_path.startswith("--"):
        report_path = pbix_path.replace(".pbix", "-audit.md")

    # If --report has a value in the next arg position
    for i, a in enumerate(sys.argv):
        if a == "--report" and i + 1 < len(sys.argv) and not sys.argv[i+1].startswith("--"):
            report_path = sys.argv[i+1]

    print("=" * 60)
    print("  PBIX Layout Linter")
    print("=" * 60)
    print(f"  File: {pbix_path}")

    lint(pbix_path, do_fix=do_fix, report_path=report_path, auto_open=auto_open)

    print("=" * 60)
