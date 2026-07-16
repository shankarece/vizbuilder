"""
metadata_extractor.py
---------------------
Generate structured documentation from PBIX metadata.

Exports:
  - data_dictionary.json — Column/measure reference
  - measure_catalog.csv — Measures with DAX formulas
  - relationships.md — Relationship map
  - columns_registry.csv — All columns with types
  - visual_registry.json — All visuals with bindings
  - tables_summary.md — Table overview

Compatible with: PBRS (offline)
Input: master_metadata.json from pbix_analyzer.py
"""

import json
import csv
from pathlib import Path


# ── Data Dictionary Generation ───────────────────────────────────────────────

def _generate_data_dictionary(metadata: dict) -> dict:
    """Generate complete data dictionary."""
    dictionary = {
        "tables": {},
        "generated": metadata.get("analysis_timestamp"),
        "pbix_version": metadata.get("pbix_version"),
    }

    for table in metadata.get("datamodel", {}).get("tables", []):
        table_name = table.get("name", "Unknown")
        dictionary["tables"][table_name] = {
            "hidden": table.get("hidden", False),
            "columns": {},
            "measures": {},
        }

        # Columns
        for col in table.get("columns", []):
            dictionary["tables"][table_name]["columns"][col["name"]] = {
                "type": col.get("type", "unknown"),
                "hidden": col.get("hidden", False),
                "is_calculated": bool(col.get("expression")),
                "expression": col.get("expression", ""),
            }

        # Measures
        for measure in table.get("measures", []):
            dictionary["tables"][table_name]["measures"][measure["name"]] = {
                "expression": measure.get("expression", ""),
                "format_string": measure.get("format_string", ""),
                "hidden": measure.get("hidden", False),
            }

    return dictionary


# ── Measure Catalog CSV ──────────────────────────────────────────────────────

def _generate_measure_catalog(metadata: dict, output_path: str) -> None:
    """Generate CSV catalog of all measures."""
    rows = []

    for table in metadata.get("datamodel", {}).get("tables", []):
        for measure in table.get("measures", []):
            rows.append({
                "Table": table.get("name", ""),
                "Measure Name": measure.get("name", ""),
                "DAX Expression": measure.get("expression", "")[:200],  # Truncate
                "Format String": measure.get("format_string", ""),
                "Hidden": "Yes" if measure.get("hidden") else "No",
            })

    if rows:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


# ── Columns Registry CSV ─────────────────────────────────────────────────────

def _generate_columns_registry(metadata: dict, output_path: str) -> None:
    """Generate CSV registry of all columns."""
    rows = []

    for table in metadata.get("datamodel", {}).get("tables", []):
        for col in table.get("columns", []):
            rows.append({
                "Table": table.get("name", ""),
                "Column Name": col["name"],
                "Data Type": col.get("type", "unknown"),
                "Hidden": "Yes" if col.get("hidden") else "No",
                "Is Calculated": "Yes" if col.get("expression") else "No",
                "Expression": col.get("expression", "")[:100] if col.get("expression") else "",
            })

    if rows:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


# ── Relationships Markdown ───────────────────────────────────────────────────

def _generate_relationships_markdown(metadata: dict, output_path: str) -> None:
    """Generate markdown documentation of relationships."""
    lines = ["# Relationships\n"]

    relationships = metadata.get("datamodel", {}).get("relationships", [])

    if not relationships:
        lines.append("No relationships defined.\n")
    else:
        for rel in relationships:
            lines.append(f"## {rel.get('from_table')} → {rel.get('to_table')}\n")
            lines.append(f"- **From:** {rel.get('from_table')}.{rel.get('from_column')}\n")
            lines.append(f"- **To:** {rel.get('to_table')}.{rel.get('to_column')}\n")
            lines.append(f"- **Cardinality:** {rel.get('cardinality', 'Unknown')}\n")
            lines.append(f"- **Cross-filter:** {rel.get('cross_filter', 'Unknown')}\n\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ── Tables Summary Markdown ──────────────────────────────────────────────────

def _generate_tables_summary(metadata: dict, output_path: str) -> None:
    """Generate markdown summary of tables."""
    lines = ["# Tables Summary\n\n"]
    lines.append("| Table | Columns | Measures | Hidden | Size (Rows) |\n")
    lines.append("|---|---|---|---|---|\n")

    for table in metadata.get("datamodel", {}).get("tables", []):
        table_name = table.get("name", "Unknown")
        col_count = len(table.get("columns", []))
        measure_count = len(table.get("measures", []))
        hidden = "Yes" if table.get("hidden") else "No"
        # Estimate from data model
        size = "(unknown)"

        lines.append(f"| {table_name} | {col_count} | {measure_count} | {hidden} | {size} |\n")

    lines.append("\n## Details\n\n")

    for table in metadata.get("datamodel", {}).get("tables", []):
        table_name = table.get("name", "Unknown")
        lines.append(f"### {table_name}\n\n")
        lines.append("**Columns:**\n")
        for col in table.get("columns", []):
            hidden_marker = " (hidden)" if col.get("hidden") else ""
            lines.append(f"- {col['name']}: {col.get('type', 'unknown')}{hidden_marker}\n")

        if table.get("measures"):
            lines.append("\n**Measures:**\n")
            for measure in table.get("measures", []):
                hidden_marker = " (hidden)" if measure.get("hidden") else ""
                lines.append(f"- {measure['name']}{hidden_marker}\n")

        lines.append("\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ── Visual Registry JSON ─────────────────────────────────────────────────────

def _generate_visual_registry(metadata: dict, output_path: str) -> None:
    """Generate JSON registry of all visuals."""
    registry = {
        "pages": [],
        "total_visuals": 0,
    }

    for page in metadata.get("report", {}).get("pages", []):
        page_entry = {
            "name": page.get("name"),
            "visuals": [],
        }

        for visual in page.get("visuals", []):
            visual_entry = {
                "id": visual.get("id"),
                "type": visual.get("type"),
                "title": visual.get("title", "(no title)"),
                "position": visual.get("position"),
                "has_title": visual.get("has_title"),
                "data_roles": visual.get("data_roles_used", []),
            }
            page_entry["visuals"].append(visual_entry)

        registry["pages"].append(page_entry)
        registry["total_visuals"] += len(page_entry["visuals"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


# ── Main Extraction Function ────────────────────────────────────────────────

def extract_metadata(metadata_path: str, output_dir: str = None) -> dict:
    """
    Extract and export metadata in multiple formats.

    Parameters
    ----------
    metadata_path : str
        Path to metadata.json from pbix_analyzer
    output_dir : str, optional
        Directory to save exports. If None, uses same dir as metadata.

    Returns
    -------
    dict : Paths to generated files
    """
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    if output_dir is None:
        output_dir = str(Path(metadata_path).parent)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    base_name = Path(metadata_path).stem.replace("_metadata", "")

    print(f"\n  Generating metadata exports to {output_dir}...")

    files = {}

    # Data Dictionary JSON
    dd_path = Path(output_dir) / f"{base_name}_data_dictionary.json"
    dictionary = _generate_data_dictionary(metadata)
    with open(dd_path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=2)
    files["data_dictionary"] = str(dd_path)
    print(f"  [OK] Data dictionary: {dd_path.name}")

    # Measure Catalog CSV
    mc_path = Path(output_dir) / f"{base_name}_measures.csv"
    _generate_measure_catalog(metadata, str(mc_path))
    files["measure_catalog"] = str(mc_path)
    print(f"  [OK] Measure catalog: {mc_path.name}")

    # Columns Registry CSV
    cr_path = Path(output_dir) / f"{base_name}_columns.csv"
    _generate_columns_registry(metadata, str(cr_path))
    files["columns_registry"] = str(cr_path)
    print(f"  [OK] Columns registry: {cr_path.name}")

    # Relationships Markdown
    rel_path = Path(output_dir) / f"{base_name}_relationships.md"
    _generate_relationships_markdown(metadata, str(rel_path))
    files["relationships"] = str(rel_path)
    print(f"  [OK] Relationships: {rel_path.name}")

    # Tables Summary Markdown
    ts_path = Path(output_dir) / f"{base_name}_tables.md"
    _generate_tables_summary(metadata, str(ts_path))
    files["tables_summary"] = str(ts_path)
    print(f"  [OK] Tables summary: {ts_path.name}")

    # Visual Registry JSON
    vr_path = Path(output_dir) / f"{base_name}_visuals.json"
    _generate_visual_registry(metadata, str(vr_path))
    files["visual_registry"] = str(vr_path)
    print(f"  [OK] Visual registry: {vr_path.name}")

    return files


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python metadata_extractor.py <metadata.json> [output_dir]")
        sys.exit(1)

    metadata_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        print("=" * 60)
        print("  Metadata Extractor")
        print("=" * 60)

        files = extract_metadata(metadata_path, output_dir)

        print("\n" + "=" * 60)
        print("  Export complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
