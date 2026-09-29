"""
format_tools.py
---------------
Find inconsistent formatting in an existing PBIX and bulk-restyle it.

Works on the legacy Report/Layout JSON (PBRS-compatible, offline, stdlib only).

Usage:
    python format_tools.py <file.pbix>                       # audit formatting
    python format_tools.py <file.pbix> --theme theme.json    # audit against a theme
    python format_tools.py <file.pbix> --restyle --theme theme.json
                                        # write <file>-restyled.pbix (original untouched)
    python format_tools.py <file.pbix> --report fmt.json     # save findings as JSON

Theme file (all keys optional):
    {"fontFamily": "Segoe UI",
     "palette": ["#E60012", "#333333", "#7F7F7F"],
     "titleFontSize": 14, "titleFontColor": "#333333"}
"""

import sys
import os
import json
import tempfile
from collections import Counter, defaultdict

from layout_builder import read_layout, write_layout
from pbix_patch import patch_pbix

FONT_KEYS = {"fontFamily"}
COLOR_KEYS = {"fontColor", "color", "fill", "background", "labelColor", "lineColor"}
NUMFMT_KEYS = {"labelDisplayUnits", "labelPrecision", "valuesPrecision", "displayUnits", "precision"}
DEFAULT_FONT_SIZE_KEYS = {"fontSize"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _literal(node):
    """Return the Literal value string from an expr node, or None."""
    if isinstance(node, dict):
        return node.get("expr", {}).get("Literal", {}).get("Value")
    return None


_WEIGHTS = (" Bold", " Semibold", " Semilight", " Light", " Black")


def _font_base(v):
    """'Segoe UI Bold'', wf_segoe-ui_bold, arial' -> ('Segoe UI', ' Bold')."""
    primary = v.strip("'\"").split(",")[0].strip().strip("'\" ")
    for w in _WEIGHTS:
        if primary.endswith(w):
            return primary[: -len(w)], w
    return primary, ""


def _norm_color(v):
    return v.strip("'\"").upper() if isinstance(v, str) else v


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _nearest(color, palette):
    rgb = _hex_to_rgb(color)
    if rgb is None:
        return None
    best, best_d = None, None
    for p in palette:
        prgb = _hex_to_rgb(p)
        if prgb is None:
            continue
        d = sum((a - b) ** 2 for a, b in zip(rgb, prgb))
        if best_d is None or d < best_d:
            best, best_d = p.upper(), d
    return best


def _walk(node, path=()):
    """Yield (path, key, value_node, parent) for every property leaf holding a Literal."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict) and "expr" in v and "Literal" in v.get("expr", {}):
                yield path, k, v, node
            elif isinstance(v, dict) and "solid" in v:
                col = v["solid"].get("color")
                if isinstance(col, dict) and "Literal" in col.get("expr", {}):
                    yield path, k, col, v["solid"]
            else:
                yield from _walk(v, path + (k,))
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item, path)


def _visual_configs(layout):
    for si, sec in enumerate(layout.get("sections", [])):
        page = sec.get("displayName", f"Page {si + 1}")
        for vc in sec.get("visualContainers", []):
            try:
                config = json.loads(vc.get("config", "{}"))
            except (json.JSONDecodeError, TypeError):
                continue
            sv = config.get("singleVisual", {})
            yield page, vc, config, sv.get("visualType", "unknown"), config.get("name", "?")


def _leaves(sv):
    """All (kind, key, raw_value, node) formatting leaves of a single visual."""
    out = []
    for section in ("objects", "vcObjects"):
        for path, key, node, parent in _walk(sv.get(section, {})):
            val = _literal(node)
            if val is None:
                continue
            kind = ("font" if key in FONT_KEYS else
                    "color" if (key in COLOR_KEYS or key == "color") else
                    "numfmt" if key in NUMFMT_KEYS else
                    "fontsize" if key in DEFAULT_FONT_SIZE_KEYS else None)
            if kind:
                out.append((kind, key, val, node, section, path))
    return out


# ── Audit ────────────────────────────────────────────────────────────────────

def audit(layout: dict, theme: dict = None) -> dict:
    theme = theme or {}
    fonts, colors, numfmts, sizes = Counter(), Counter(), defaultdict(Counter), Counter()
    per_visual = []

    for page, vc, config, vtype, name in _visual_configs(layout):
        sv = config.get("singleVisual", {})
        rec = {"page": page, "visual": name[:12], "type": vtype,
               "fonts": set(), "colors": set()}
        for kind, key, val, _, _, _ in _leaves(sv):
            v = val.strip("'\"")
            if kind == "font":
                v = _font_base(v)[0]
                fonts[v] += 1
                rec["fonts"].add(v)
            elif kind == "color":
                c = _norm_color(val)
                if c.startswith("#"):
                    colors[c] += 1
                    rec["colors"].add(c)
            elif kind == "numfmt":
                numfmts[key][v] += 1
            elif kind == "fontsize":
                sizes[v] += 1
        per_visual.append(rec)

    findings = []
    dom_font = _font_base(theme["fontFamily"])[0] if theme.get("fontFamily") else (
        fonts.most_common(1)[0][0] if fonts else None)
    if len(fonts) > 1 or (theme.get("fontFamily") and fonts and set(fonts) != {dom_font}):
        odd = [r for r in per_visual if r["fonts"] - {dom_font}]
        findings.append({
            "severity": "warning", "category": "font_inconsistency",
            "message": f"{len(fonts)} fonts in use ({', '.join(fonts)}); expected '{dom_font}'",
            "visuals": [f"{r['page']}/{r['type']}:{r['visual']}" for r in odd],
            "fix": f"restyle to '{dom_font}'"})

    palette = [c.upper() for c in theme.get("palette", [])]
    if palette:
        off = {c: n for c, n in colors.items() if c not in palette}
        if off:
            findings.append({
                "severity": "warning", "category": "off_palette_color",
                "message": f"{len(off)} colours not in theme palette: {', '.join(sorted(off))}",
                "visuals": [f"{r['page']}/{r['type']}:{r['visual']}"
                            for r in per_visual if r["colors"] - set(palette)],
                "fix": "restyle maps each to nearest palette colour"})
    elif len(colors) > 8:
        findings.append({
            "severity": "info", "category": "too_many_colors",
            "message": f"{len(colors)} distinct hard-coded colours; consider a theme palette",
            "visuals": [], "fix": "supply --theme with a palette"})

    for key, cnt in numfmts.items():
        if len(cnt) > 1:
            findings.append({
                "severity": "warning", "category": "number_format_inconsistency",
                "message": f"'{key}' set to different values: {dict(cnt)}",
                "visuals": [], "fix": "standardise manually or via theme"})

    if len(sizes) > 3:
        findings.append({
            "severity": "info", "category": "font_size_variety",
            "message": f"{len(sizes)} different font sizes: {dict(sizes)}",
            "visuals": [], "fix": "limit to 3 sizes (title / label / body)"})

    return {"fonts": dict(fonts), "colors": dict(colors),
            "findings": findings, "visual_count": len(per_visual)}


# ── Restyle ──────────────────────────────────────────────────────────────────

def restyle(layout: dict, theme: dict) -> list:
    """Apply theme to every visual in-place. Returns list of change descriptions."""
    changes = []
    font = theme.get("fontFamily")
    palette = theme.get("palette", [])

    for page, vc, config, vtype, name in _visual_configs(layout):
        sv = config.get("singleVisual", {})
        n = 0
        for kind, key, val, node, _, _ in _leaves(sv):
            if kind == "font" and font and _font_base(val)[0] != _font_base(font)[0]:
                node["expr"]["Literal"]["Value"] = f"'{_font_base(font)[0]}{_font_base(val)[1]}'"
                n += 1
            elif kind == "color" and palette:
                c = _norm_color(val)
                if c.startswith("#") and c not in [p.upper() for p in palette]:
                    new = _nearest(c, palette)
                    if new:
                        node["expr"]["Literal"]["Value"] = f"'{new}'"
                        n += 1
        if n:
            vc["config"] = json.dumps(config, separators=(",", ":"))
            changes.append(f"{page}/{vtype}:{name[:12]} - {n} property change(s)")
    return changes


# ── CLI ──────────────────────────────────────────────────────────────────────

def run(pbix_path, theme_path=None, do_restyle=False, report_path=None):
    theme = {}
    if theme_path:
        with open(theme_path, "r", encoding="utf-8") as f:
            theme = json.load(f)

    layout = read_layout(pbix_path)
    result = audit(layout, theme)

    print(f"\n  Formatting audit: {result['visual_count']} visuals")
    print(f"  Fonts:   {result['fonts'] or 'none set explicitly'}")
    print(f"  Colours: {len(result['colors'])} distinct")
    if not result["findings"]:
        print("  [OK] No formatting inconsistencies found.")
    for f in result["findings"]:
        print(f"  [{f['severity'].upper()}] {f['category']}: {f['message']}")
        if f["visuals"]:
            print(f"      visuals: {', '.join(f['visuals'][:6])}"
                  f"{' ...' if len(f['visuals']) > 6 else ''}")

    if do_restyle:
        if not theme:
            print("\n  [ERROR] --restyle needs --theme theme.json")
            return result
        changes = restyle(layout, theme)
        if changes:
            out = pbix_path.replace(".pbix", "-restyled.pbix")
            with tempfile.NamedTemporaryFile(suffix=".layout", delete=False) as tmp:
                tmp_path = tmp.name
            write_layout(layout, tmp_path)
            patch_pbix(pbix_path, tmp_path, out)
            os.remove(tmp_path)
            print(f"\n  Restyled {len(changes)} visual(s); original untouched:")
            for c in changes:
                print(f"    - {c}")
            print(f"  Output: {out}")
        else:
            print("\n  Nothing to restyle - already matches the theme.")

    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Report saved: {report_path}")
    return result


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    def _opt(name):
        return flags[flags.index(name) + 1] if name in flags and flags.index(name) + 1 < len(flags) else None

    try:
        run(args[0], _opt("--theme"), "--restyle" in flags, _opt("--report"))
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
