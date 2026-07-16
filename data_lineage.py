"""
data_lineage.py
---------------
Trace data flow from source tables through measures to visuals.

Analyzes:
  - Visual → Data Role → Measure → Table dependencies
  - Orphaned/unused tables, columns, measures
  - Measure-to-measure dependencies (Measure A uses Measure B)
  - Impact analysis (if I change this table, which visuals break?)
  - Field usage inventory

Output: lineage_graph.json with complete dependency map

Compatible with: PBRS (offline analysis)
Input: master_metadata.json from pbix_analyzer.py
"""

import sys
import json
import re
from collections import defaultdict
from pathlib import Path


# ── DAX Parsing Utilities ────────────────────────────────────────────────────

def _extract_table_references(dax_expression: str) -> set:
    """Extract table/column names from DAX expression.

    Finds patterns like:
      - Table[Column]
      - Table.Column
      - RELATED(Table[Column])
      - VALUES(Table[Column])
    """
    if not dax_expression:
        return set()

    refs = set()

    # Pattern: Table[Column] or Table.Column
    pattern1 = r"(?:^|\W)([a-zA-Z_][a-zA-Z0-9_\.]*)\s*[\[\.]([a-zA-Z_][a-zA-Z0-9_\s]*)\]?"
    matches1 = re.findall(pattern1, dax_expression)
    for table, col in matches1:
        if table and col:
            refs.add(f"{table}.{col}")

    # Pattern: function(Table[Column]) like RELATED, VALUES, CALCULATE
    pattern2 = r"(?:RELATED|VALUES|CALCULATE|SUMX|FILTER|ALL)\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*[\[\.]"
    matches2 = re.findall(pattern2, dax_expression, re.IGNORECASE)
    for table in matches2:
        refs.add(table)

    return refs


def _parse_visual_bindings(visual_info: dict) -> dict:
    """Parse visual data role bindings into table.column references."""
    bindings = defaultdict(list)

    # From prototypeQuery if available
    if "prototypeQuery" in visual_info:
        proto = visual_info["prototypeQuery"]
        for select_item in proto.get("Select", []):
            name = select_item.get("Name", "")
            if name and "[" in name:
                # Extract Table[Column] or Table.Column
                match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]", name)
                if match:
                    table, col = match.groups()
                    bindings["fields"].append(f"{table}.{col}")

    # From data_roles_used (pre-extracted)
    if "data_roles_used" in visual_info:
        bindings["roles"] = visual_info["data_roles_used"]

    return dict(bindings)


# ── Lineage Analysis ────────────────────────────────────────────────────────

class DataLineageAnalyzer:
    def __init__(self, metadata: dict):
        self.metadata = metadata
        self.tables = {}
        self.measures = {}
        self.visuals = {}
        self.field_usage = defaultdict(list)
        self.orphaned = {"tables": [], "columns": [], "measures": []}

    def _build_lookup_tables(self):
        """Build lookups for quick access."""
        # Tables and columns
        for table_info in self.metadata.get("datamodel", {}).get("tables", []):
            table_name = table_info.get("name", "")
            self.tables[table_name] = {
                "columns": {c["name"]: c for c in table_info.get("columns", [])},
                "measures": {m["name"]: m for m in table_info.get("measures", [])},
                "hidden": table_info.get("hidden", False),
            }
            # Track column usage
            for col in table_info.get("columns", []):
                self.field_usage[f"{table_name}.{col['name']}"] = []
            # Track measure usage
            for measure in table_info.get("measures", []):
                self.field_usage[f"{table_name}.{measure['name']}"] = []

        # Visuals
        for page_info in self.metadata.get("report", {}).get("pages", []):
            for visual in page_info.get("visuals", []):
                visual_key = f"{page_info['name']}:{visual['id']}"
                self.visuals[visual_key] = {
                    "page": page_info["name"],
                    "id": visual["id"],
                    "type": visual.get("type"),
                    "fields": [],
                }

    def _trace_visual_lineage(self):
        """Trace data flow from tables through visuals."""
        lineages = []

        for visual_key, visual_info in self.visuals.items():
            page_name, visual_id = visual_key.split(":")

            # Extract bindings from visual
            for page in self.metadata.get("report", {}).get("pages", []):
                if page["name"] == page_name:
                    for visual in page.get("visuals", []):
                        if visual["id"] == int(visual_id):
                            # Parse field references
                            for binding in visual.get("bindings", []):
                                query_ref = binding.get("query_ref", "")
                                if query_ref:
                                    # Try to extract table.column
                                    match = re.search(
                                        r"([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]|([a-zA-Z_][a-zA-Z0-9_]*)",
                                        query_ref
                                    )
                                    if match:
                                        table = match.group(1) or match.group(3)
                                        col = match.group(2)
                                        if table:
                                            field_key = f"{table}.{col}" if col else table
                                            self.field_usage[field_key].append({
                                                "visual": visual_key,
                                                "role": binding.get("role"),
                                            })
                                            visual_info["fields"].append(field_key)

                                            lineages.append({
                                                "source_table": table,
                                                "source_column": col,
                                                "target_visual": visual_key,
                                                "target_page": page_name,
                                                "role": binding.get("role"),
                                            })

        return lineages

    def _find_orphaned_objects(self):
        """Identify unused tables, columns, measures."""
        # Unused tables (no columns used in any visual)
        for table_name, table_info in self.tables.items():
            cols_used = [f"{table_name}.{c}" for c in table_info["columns"].keys()
                        if any(self.field_usage.get(f"{table_name}.{c}"))]
            if not cols_used and not table_info.get("hidden"):
                self.orphaned["tables"].append({
                    "name": table_name,
                    "reason": "No columns used in any visual",
                    "column_count": len(table_info["columns"]),
                })

        # Unused columns (in tables that have some usage)
        for field_key, usage in self.field_usage.items():
            if not usage and "[" not in field_key:  # Skip if no usage
                parts = field_key.split(".")
                if len(parts) == 2:
                    table, col = parts
                    if table in self.tables and not self.tables[table].get("hidden"):
                        self.orphaned["columns"].append({
                            "table": table,
                            "column": col,
                            "reason": "Not used in any visual",
                        })

        # Unused measures
        for table_name, table_info in self.tables.items():
            for measure_name, measure_info in table_info["measures"].items():
                field_key = f"{table_name}.{measure_name}"
                if not self.field_usage.get(field_key) and not measure_info.get("hidden"):
                    self.orphaned["measures"].append({
                        "table": table_name,
                        "measure": measure_name,
                        "reason": "Not used in any visual",
                    })

    def _find_measure_dependencies(self):
        """Find Measure-to-Measure dependencies."""
        dependencies = []

        for table_name, table_info in self.tables.items():
            for measure_name, measure_info in table_info["measures"].items():
                expression = measure_info.get("expression", "")
                # Find references to other measures
                refs = _extract_table_references(expression)
                for ref in refs:
                    if "." in ref:
                        ref_table, ref_col = ref.split(".", 1)
                        # Check if it's a measure in another table
                        if ref_table in self.tables:
                            if ref_col in self.tables[ref_table]["measures"]:
                                dependencies.append({
                                    "measure": f"{table_name}.{measure_name}",
                                    "depends_on_measure": f"{ref_table}.{ref_col}",
                                })

        return dependencies

    def analyze(self) -> dict:
        """Run complete lineage analysis."""
        self._build_lookup_tables()
        lineages = self._trace_visual_lineage()
        self._find_orphaned_objects()
        dependencies = self._find_measure_dependencies()

        result = {
            "analysis_timestamp": self.metadata.get("analysis_timestamp"),

            "lineages": lineages,
            "lineage_count": len(lineages),

            "field_usage": dict(self.field_usage),
            "fields_used": len([f for f, usage in self.field_usage.items() if usage]),
            "fields_unused": len([f for f, usage in self.field_usage.items() if not usage]),

            "orphaned_objects": self.orphaned,
            "total_orphaned": (
                len(self.orphaned["tables"]) +
                len(self.orphaned["columns"]) +
                len(self.orphaned["measures"])
            ),

            "measure_dependencies": dependencies,
            "has_circular_refs": self._check_circular_dependencies(dependencies),

            "impact_summary": self._generate_impact_summary(),
        }

        return result

    def _check_circular_dependencies(self, dependencies: list) -> bool:
        """Check if there are circular measure dependencies."""
        # Build graph
        graph = defaultdict(set)
        for dep in dependencies:
            measure = dep["measure"]
            depends_on = dep["depends_on_measure"]
            graph[measure].add(depends_on)

        # Simple cycle detection
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        visited = set()
        for node in graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    return True
        return False

    def _generate_impact_summary(self) -> dict:
        """Generate impact analysis summary."""
        return {
            "tables_with_usage": len([t for t in self.tables if t in
                                     [l["source_table"] for l in self.field_usage]]),
            "tables_unused": len(self.orphaned["tables"]),
            "measures_with_usage": len([m for m in self.field_usage
                                       if self.field_usage[m]]),
            "measures_unused": len(self.orphaned["measures"]),
            "visuals_connected": len(self.visuals),
            "isolated_visuals": len([v for v in self.visuals if not self.visuals[v].get("fields")]),
        }


# ── Main ─────────────────────────────────────────────────────────────────────

def analyze_lineage(metadata_path: str, output_path: str = None) -> dict:
    """
    Analyze data lineage from metadata JSON.

    Parameters
    ----------
    metadata_path : str
        Path to master_metadata.json from pbix_analyzer.py
    output_path : str, optional
        Path to save lineage JSON

    Returns
    -------
    dict : Lineage analysis results
    """
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"\n  Analyzing lineage from {Path(metadata_path).name}...")

    analyzer = DataLineageAnalyzer(metadata)
    result = analyzer.analyze()

    print(f"  Lineages traced: {result['lineage_count']}")
    print(f"  Fields used: {result['fields_used']} / {result['fields_used'] + result['fields_unused']}")
    print(f"  Orphaned objects: {result['total_orphaned']}")
    if result["has_circular_refs"]:
        print(f"  ⚠️ WARNING: Circular measure dependencies detected")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Lineage saved: {output_path}")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python data_lineage.py <metadata.json> [output.json]")
        sys.exit(1)

    metadata_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        print("=" * 60)
        print("  Data Lineage Analyzer")
        print("=" * 60)

        result = analyze_lineage(metadata_path, output_path)

        print("\n" + "=" * 60)
        print("  Analysis complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
