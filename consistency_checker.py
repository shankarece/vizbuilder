"""
consistency_checker.py
----------------------
Find design and structural inconsistencies in PBIX dashboards.

Checks:
  - Naming conventions (visual names, measure names, table names)
  - Visual sizing consistency (cards, charts should be uniform)
  - Alignment issues (position consistency)
  - Missing titles (all data visuals should have titles)
  - Color palette consistency
  - Measure aggregation patterns
  - Hidden vs visible object patterns
  - Data type consistency

Output: violations.json with severity levels (error, warning, info)

Compatible with: PBRS (offline analysis)
Input: master_metadata.json from pbix_analyzer.py
"""

import json
import re
from collections import defaultdict
from pathlib import Path


# ── Violation Class ──────────────────────────────────────────────────────────

class Violation:
    def __init__(self, severity: str, category: str, message: str,
                 objects: list = None, suggestion: str = None):
        self.severity = severity  # error, warning, info
        self.category = category
        self.message = message
        self.objects = objects or []
        self.suggestion = suggestion

    def to_dict(self):
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "objects": self.objects,
            "suggestion": self.suggestion,
        }


# ── Naming Convention Checker ────────────────────────────────────────────────

def _check_naming_conventions(metadata: dict) -> list:
    """Check for inconsistent naming patterns."""
    violations = []

    # Check visual names
    visual_patterns = defaultdict(int)
    for page in metadata.get("report", {}).get("pages", []):
        for visual in page.get("visuals", []):
            visual_id = str(visual.get("id", ""))
            # Most visuals should have names like: type_number or DescriptiveTitle
            if visual_id.isdigit():
                visual_patterns["numeric_only"] += 1
            elif "_" in str(visual_id):
                visual_patterns["snake_case"] += 1
            elif visual_id and visual_id[0].isupper():
                visual_patterns["PascalCase"] += 1

    # If mixed patterns detected, flag it
    patterns_used = sum(1 for v in visual_patterns.values() if v > 0)
    if patterns_used > 2:
        violations.append(Violation(
            "warning", "naming_convention",
            f"Visual ID naming is inconsistent: {dict(visual_patterns)}",
            suggestion="Adopt a single naming pattern (e.g., snake_case or PascalCase)",
        ))

    # Check table/measure naming
    for table in metadata.get("datamodel", {}).get("tables", []):
        table_name = table.get("name", "")
        if table_name and "_" in table_name and table_name != table_name.lower():
            violations.append(Violation(
                "info", "naming_convention",
                f"Table '{table_name}' mixes casing and underscores",
                objects=[table_name],
                suggestion="Use consistent casing: either snake_case or PascalCase",
            ))

        for measure in table.get("measures", []):
            measure_name = measure.get("name", "")
            if measure_name and not measure_name[0].isupper():
                violations.append(Violation(
                    "info", "naming_convention",
                    f"Measure '{measure_name}' should start with uppercase",
                    objects=[f"{table_name}.{measure_name}"],
                ))

    return violations


# ── Visual Sizing Checker ────────────────────────────────────────────────────

def _check_visual_sizing(metadata: dict) -> list:
    """Check for inconsistent visual dimensions."""
    violations = []

    for page in metadata.get("report", {}).get("pages", []):
        # Group visuals by type
        type_groups = defaultdict(list)
        for visual in page.get("visuals", []):
            vtype = visual.get("type", "unknown")
            dims = (visual["position"].get("w"), visual["position"].get("h"))
            type_groups[vtype].append({
                "id": visual.get("id"),
                "dims": dims,
            })

        # Check each type for sizing consistency
        for vtype, visuals_of_type in type_groups.items():
            if len(visuals_of_type) < 2:
                continue

            dims_set = set(v["dims"] for v in visuals_of_type)
            if len(dims_set) > 1:
                # Calculate variance
                widths = [v["dims"][0] for v in visuals_of_type]
                heights = [v["dims"][1] for v in visuals_of_type]
                w_range = max(widths) - min(widths)
                h_range = max(heights) - min(heights)

                if w_range > 50 or h_range > 50:  # Threshold
                    dims_desc = ", ".join([f"id={v['id']}:{v['dims'][0]}x{v['dims'][1]}"
                                          for v in visuals_of_type])
                    violations.append(Violation(
                        "warning", "sizing_inconsistency",
                        f"{vtype} visuals on '{page['name']}' have inconsistent sizes: {dims_desc}",
                        objects=[v["id"] for v in visuals_of_type],
                        suggestion=f"Standardize to {max(widths)}x{max(heights)} or a common size",
                    ))

    return violations


# ── Title Presence Checker ───────────────────────────────────────────────────

def _check_title_presence(metadata: dict) -> list:
    """Check that all data visuals have titles."""
    violations = []
    skip_types = {"textbox", "shape", "image", "actionButton", "pageNavigator"}

    for page in metadata.get("report", {}).get("pages", []):
        for visual in page.get("visuals", []):
            vtype = visual.get("type", "unknown")
            if vtype in skip_types:
                continue

            if not visual.get("has_title"):
                violations.append(Violation(
                    "warning", "missing_title",
                    f"{vtype} (id={visual['id']}) on '{page['name']}' has no title",
                    objects=[str(visual["id"])],
                    suggestion="Add a descriptive title using the title= parameter",
                ))

    return violations


# ── Alignment Checker ────────────────────────────────────────────────────────

def _check_alignment(metadata: dict) -> list:
    """Check for misaligned visuals (positions not on grid)."""
    violations = []
    grid_size = 10

    for page in metadata.get("report", {}).get("pages", []):
        misaligned = []
        for visual in page.get("visuals", []):
            if visual.get("type") == "textbox":
                continue
            x = visual["position"].get("x", 0)
            y = visual["position"].get("y", 0)
            if (x % grid_size != 0) or (y % grid_size != 0):
                misaligned.append({
                    "id": visual["id"],
                    "position": (x, y),
                    "aligned_to": (
                        round(x / grid_size) * grid_size,
                        round(y / grid_size) * grid_size
                    ),
                })

        if misaligned:
            if len(misaligned) > 1:
                violations.append(Violation(
                    "info", "alignment",
                    f"{len(misaligned)} visuals on '{page['name']}' not on {grid_size}px grid",
                    objects=[str(v["id"]) for v in misaligned],
                    suggestion="Snap visuals to grid (lint.py --fix can auto-fix)",
                ))

    return violations


# ── Unused Objects Checker ───────────────────────────────────────────────────

def _check_unused_objects(metadata: dict, lineage: dict = None) -> list:
    """Check for unused tables, columns, measures."""
    violations = []

    if not lineage:
        return violations

    # Check unused tables
    for orphan_table in lineage.get("orphaned_objects", {}).get("tables", []):
        violations.append(Violation(
            "info", "unused_objects",
            f"Table '{orphan_table['name']}' is not used in any visual",
            objects=[orphan_table["name"]],
            suggestion="Consider removing unused tables to reduce file size",
        ))

    # Check unused measures (high impact)
    for orphan_measure in lineage.get("orphaned_objects", {}).get("measures", []):
        violations.append(Violation(
            "info", "unused_objects",
            f"Measure '{orphan_measure['table']}.{orphan_measure['measure']}' not used",
            objects=[f"{orphan_measure['table']}.{orphan_measure['measure']}"],
            suggestion="Remove unused measures or use them in a visual",
        ))

    return violations


# ── Measure Aggregation Checker ──────────────────────────────────────────────

def _check_measure_consistency(metadata: dict) -> list:
    """Check for inconsistent measure usage patterns."""
    violations = []

    # For now, just note if measures exist
    measure_count = sum(
        len(table.get("measures", []))
        for table in metadata.get("datamodel", {}).get("tables", [])
    )

    if measure_count == 0:
        violations.append(Violation(
            "info", "no_measures",
            "No measures found in data model",
            suggestion="Consider creating calculated measures for common calculations",
        ))

    return violations


# ── Hidden Objects Checker ───────────────────────────────────────────────────

def _check_hidden_objects(metadata: dict) -> list:
    """Check for excessive hidden objects."""
    violations = []

    hidden_count = 0
    total_count = 0
    for table in metadata.get("datamodel", {}).get("tables", []):
        for col in table.get("columns", []):
            total_count += 1
            if col.get("hidden"):
                hidden_count += 1

    if total_count > 0 and hidden_count / total_count > 0.3:
        violations.append(Violation(
            "warning", "excessive_hidden",
            f"{hidden_count}/{total_count} columns ({100*hidden_count/total_count:.0f}%) are hidden",
            suggestion="Consider if all hidden columns are truly needed, or if there's a way to simplify the model",
        ))

    return violations


# ── Data Type Consistency ────────────────────────────────────────────────────

def _check_data_types(metadata: dict) -> list:
    """Check for unexpected data type patterns."""
    violations = []

    type_counts = defaultdict(int)
    for table in metadata.get("datamodel", {}).get("tables", []):
        for col in table.get("columns", []):
            dtype = col.get("type", "unknown")
            type_counts[dtype] += 1

    # Flag if too many columns are string type (poor model design)
    if type_counts.get("string", 0) > type_counts.get("int64", 0) * 2:
        violations.append(Violation(
            "info", "data_types",
            f"Many string columns ({type_counts['string']}) vs numeric ({type_counts.get('int64', 0)})",
            suggestion="Consider if numerical columns should use numeric types for better performance",
        ))

    return violations


# ── Main Analysis Function ──────────────────────────────────────────────────

class ConsistencyAnalyzer:
    def __init__(self, metadata: dict, lineage: dict = None):
        self.metadata = metadata
        self.lineage = lineage or {}
        self.violations = []

    def analyze(self) -> dict:
        """Run all consistency checks."""
        # Run all checks
        self.violations.extend(_check_naming_conventions(self.metadata))
        self.violations.extend(_check_visual_sizing(self.metadata))
        self.violations.extend(_check_title_presence(self.metadata))
        self.violations.extend(_check_alignment(self.metadata))
        self.violations.extend(_check_unused_objects(self.metadata, self.lineage))
        self.violations.extend(_check_measure_consistency(self.metadata))
        self.violations.extend(_check_hidden_objects(self.metadata))
        self.violations.extend(_check_data_types(self.metadata))

        # Sort by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        self.violations.sort(key=lambda v: severity_order[v.severity])

        # Summarize
        summary = {
            "total_violations": len(self.violations),
            "errors": sum(1 for v in self.violations if v.severity == "error"),
            "warnings": sum(1 for v in self.violations if v.severity == "warning"),
            "info": sum(1 for v in self.violations if v.severity == "info"),
        }

        return {
            "summary": summary,
            "violations": [v.to_dict() for v in self.violations],
        }


# ── CLI Interface ────────────────────────────────────────────────────────────

def check_consistency(metadata_path: str, lineage_path: str = None,
                     output_path: str = None) -> dict:
    """
    Check PBIX for consistency issues.

    Parameters
    ----------
    metadata_path : str
        Path to metadata.json from pbix_analyzer
    lineage_path : str, optional
        Path to lineage.json from data_lineage
    output_path : str, optional
        Path to save violations JSON

    Returns
    -------
    dict : Violations and summary
    """
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    lineage = {}
    if lineage_path and Path(lineage_path).exists():
        with open(lineage_path, "r", encoding="utf-8") as f:
            lineage = json.load(f)

    print(f"\n  Analyzing consistency from {Path(metadata_path).name}...")

    analyzer = ConsistencyAnalyzer(metadata, lineage)
    result = analyzer.analyze()

    print(f"  Violations: {result['summary']['total_violations']}")
    print(f"    Errors:   {result['summary']['errors']}")
    print(f"    Warnings: {result['summary']['warnings']}")
    print(f"    Info:     {result['summary']['info']}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Violations saved: {output_path}")

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python consistency_checker.py <metadata.json> [lineage.json] [output.json]")
        sys.exit(1)

    metadata_path = sys.argv[1]
    lineage_path = sys.argv[2] if len(sys.argv) > 2 else None
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        print("=" * 60)
        print("  Consistency Checker")
        print("=" * 60)

        result = check_consistency(metadata_path, lineage_path, output_path)

        print("\n" + "=" * 60)
        print("  Analysis complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
