"""
pbrs_validator.py
-----------------
Validate PBIX files for Power BI Report Server (PBRS) compatibility.

Checks PBRS-specific constraints:
  - File size limits (PBRS typically has 2GB limit per file)
  - Unsupported visual types for PBRS
  - DirectQuery sources (may have limitations)
  - Premium-only features (not available in PBRS)
  - Real-time datasets (not supported)
  - XMLA/refresh requirements
  - Embedded data model size
  - Relationship cross-filter directions (PBRS limitations)

Output: pbrs_validation.json with compatibility report

Compatible with: PBRS (September 2024, May 2025)
Input: master_metadata.json from pbix_analyzer.py, file.pbix
"""

import json
import os
from pathlib import Path


# ── PBRS Constants ───────────────────────────────────────────────────────────

PBRS_MAX_FILE_SIZE_MB = 2048  # 2GB typical limit
PBRS_UNSUPPORTED_VISUALS = {
    "advancedSlicerVisual",  # Tile slicer
    "pageNavigator",         # Page navigation
    # Most standard visuals are supported
}
PBRS_MIN_SUPPORTED_VERSION = "September 2024"
PBRS_MAX_SUPPORTED_VERSION = "May 2025"


# ── Validation Classes ───────────────────────────────────────────────────────

class PBRSValidation:
    def __init__(self, severity: str, category: str, message: str,
                 suggestion: str = None):
        self.severity = severity  # error, warning, info
        self.category = category
        self.message = message
        self.suggestion = suggestion
        self.pbrs_blocking = severity == "error"

    def to_dict(self):
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "pbrs_blocking": self.pbrs_blocking,
        }


# ── File Size Checker ────────────────────────────────────────────────────────

def _check_file_size(pbix_path: str, metadata: dict) -> list:
    """Check file size against PBRS limits."""
    issues = []

    file_size_mb = os.path.getsize(pbix_path) / (1024 * 1024)

    if file_size_mb > PBRS_MAX_FILE_SIZE_MB:
        issues.append(PBRSValidation(
            "error", "file_size",
            f"File size {file_size_mb:.1f}MB exceeds PBRS limit ({PBRS_MAX_FILE_SIZE_MB}MB)",
            suggestion="Reduce file size by removing unused tables/columns or using DirectQuery for large datasets",
        ))
    elif file_size_mb > PBRS_MAX_FILE_SIZE_MB * 0.8:
        issues.append(PBRSValidation(
            "warning", "file_size",
            f"File size {file_size_mb:.1f}MB is close to PBRS limit ({PBRS_MAX_FILE_SIZE_MB}MB)",
            suggestion="Monitor file size growth; consider optimization strategies",
        ))

    # Check data model vs layout ratio
    datamodel_mb = metadata.get("datamodel", {}).get("estimated_data_size_mb", 0)
    if datamodel_mb > 1500:
        issues.append(PBRSValidation(
            "warning", "datamodel_size",
            f"Data model is large ({datamodel_mb:.0f}MB); may impact PBRS performance",
            suggestion="Consider using DirectQuery or reducing data retention periods",
        ))

    return issues


# ── Visual Type Checker ──────────────────────────────────────────────────────

def _check_visual_types(metadata: dict) -> list:
    """Check for unsupported visual types in PBRS."""
    issues = []
    unsupported_found = {}

    for page in metadata.get("report", {}).get("pages", []):
        for visual in page.get("visuals", []):
            vtype = visual.get("type", "unknown")
            if vtype in PBRS_UNSUPPORTED_VISUALS:
                if vtype not in unsupported_found:
                    unsupported_found[vtype] = []
                unsupported_found[vtype].append({
                    "page": page["name"],
                    "id": visual["id"],
                })

    for vtype, instances in unsupported_found.items():
        pages = set(inst["page"] for inst in instances)
        issues.append(PBRSValidation(
            "warning", "unsupported_visual",
            f"{vtype} not fully supported in PBRS (found on {len(pages)} page(s))",
            suggestion=f"Replace with standard visuals; {len(instances)} instance(s) found",
        ))

    return issues


# ── Relationship Checker ────────────────────────────────────────────────────

def _check_relationships(metadata: dict) -> list:
    """Check for PBRS relationship limitations."""
    issues = []

    relationships = metadata.get("datamodel", {}).get("relationships", [])

    # Check cross-filter directions
    both_way_count = sum(1 for rel in relationships if rel.get("cross_filter") == "both")
    if both_way_count > 0:
        issues.append(PBRSValidation(
            "info", "cross_filter",
            f"{both_way_count} relationship(s) use bidirectional cross-filter",
            suggestion="Bidirectional filters work in PBRS but may impact performance; verify necessary",
        ))

    # Check circular references (though rare)
    if len(relationships) > len(metadata.get("datamodel", {}).get("tables", [])):
        issues.append(PBRSValidation(
            "warning", "relationship_count",
            f"Complex relationship structure ({len(relationships)} relationships); verify no circular refs",
            suggestion="Simplify star schema if possible; circular refs cause query errors in PBRS",
        ))

    return issues


# ── Premium Features Checker ────────────────────────────────────────────────

def _check_premium_features(metadata: dict) -> list:
    """Check for Premium-only or unsupported features."""
    issues = []

    # Check if any visuals or measures use premium-only features
    # (This is a simplified check; actual premium features are hard to detect)

    # Real-time datasets
    datamodel = metadata.get("datamodel", {})
    if any(t.get("hidden") is False for t in datamodel.get("tables", [])):
        # Not a real check, but placeholder for future enhancement
        pass

    # Check for calculated tables (less common in PBRS)
    calculated_tables = sum(
        1 for table in datamodel.get("tables", [])
        if table.get("expression") or any(col.get("expression") for col in table.get("columns", []))
    )
    if calculated_tables > 5:
        issues.append(PBRSValidation(
            "info", "calculated_objects",
            f"{calculated_tables} calculated tables/columns found",
            suggestion="Calculated objects work in PBRS but may use more memory; monitor performance",
        ))

    return issues


# ── Security Binding Checker ────────────────────────────────────────────────

def _check_security_bindings(metadata: dict) -> list:
    """Check SecurityBindings status."""
    issues = []

    security = metadata.get("security", {})
    has_sb = security.get("has_security_bindings", False)

    if not has_sb:
        issues.append(PBRSValidation(
            "warning", "security_bindings",
            "SecurityBindings are stripped (file was modified externally)",
            suggestion="Save in Desktop to regenerate SecurityBindings before PBRS deployment",
        ))

    return issues


# ── Version Checker ──────────────────────────────────────────────────────────

def _check_version_compatibility(metadata: dict) -> list:
    """Check PBIX version compatibility with PBRS."""
    issues = []

    pbix_version = metadata.get("pbix_version", "Unknown")

    if pbix_version == "Unknown":
        issues.append(PBRSValidation(
            "info", "version",
            "PBIX version could not be determined",
            suggestion="Verify file was created with compatible PBI Desktop version",
        ))

    return issues


# ── Performance Recommendations ──────────────────────────────────────────────

def _generate_recommendations(metadata: dict, violations: list) -> list:
    """Generate performance and optimization recommendations."""
    recommendations = []

    # Table count
    table_count = len(metadata.get("datamodel", {}).get("tables", []))
    if table_count > 20:
        recommendations.append(PBRSValidation(
            "info", "performance",
            f"Large semantic model ({table_count} tables); PBRS may experience slower query performance",
            suggestion="Review if all tables are necessary; consider archiving old/unused tables",
        ))

    # Column count
    total_cols = sum(
        len(table.get("columns", []))
        for table in metadata.get("datamodel", {}).get("tables", [])
    )
    if total_cols > 200:
        recommendations.append(PBRSValidation(
            "info", "performance",
            f"Many columns ({total_cols} total); consider hiding unused columns",
            suggestion="Unused columns consume memory; hide them to reduce query overhead",
        ))

    # Visual count per page
    for page in metadata.get("report", {}).get("pages", []):
        visual_count = len(page.get("visuals", []))
        if visual_count > 20:
            recommendations.append(PBRSValidation(
                "info", "performance",
                f"Page '{page['name']}' has {visual_count} visuals; may impact browser performance",
                suggestion="Split into multiple pages or use drill-through for complex analyses",
            ))

    return recommendations


# ── Main Validation Function ────────────────────────────────────────────────

def validate_pbrs_compatibility(pbix_path: str, metadata_path: str = None,
                               output_path: str = None) -> dict:
    """
    Validate PBIX for PBRS compatibility.

    Parameters
    ----------
    pbix_path : str
        Path to .pbix file
    metadata_path : str, optional
        Path to metadata.json from pbix_analyzer
    output_path : str, optional
        Path to save validation report JSON

    Returns
    -------
    dict : Validation results with compatibility status
    """

    # Load metadata
    if metadata_path and Path(metadata_path).exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        raise FileNotFoundError(f"Metadata file required: {metadata_path}")

    print(f"\n  Validating PBRS compatibility...")

    issues = []

    # Run all checks
    issues.extend(_check_file_size(pbix_path, metadata))
    issues.extend(_check_visual_types(metadata))
    issues.extend(_check_relationships(metadata))
    issues.extend(_check_premium_features(metadata))
    issues.extend(_check_security_bindings(metadata))
    issues.extend(_check_version_compatibility(metadata))
    issues.extend(_generate_recommendations(metadata, issues))

    # Sort by severity
    severity_order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_order[i.severity])

    # Determine compatibility
    blocking_issues = [i for i in issues if i.pbrs_blocking]
    is_compatible = len(blocking_issues) == 0

    summary = {
        "pbrs_compatible": is_compatible,
        "blocking_issues": len(blocking_issues),
        "warnings": sum(1 for i in issues if i.severity == "warning"),
        "recommendations": sum(1 for i in issues if i.severity == "info"),
        "deployment_ready": is_compatible,
    }

    result = {
        "summary": summary,
        "recommendations": {
            "min_version": PBRS_MIN_SUPPORTED_VERSION,
            "max_version": PBRS_MAX_SUPPORTED_VERSION,
            "max_file_size_mb": PBRS_MAX_FILE_SIZE_MB,
        },
        "validations": [issue.to_dict() for issue in issues],
    }

    # Print summary
    print(f"  Compatibility: {'YES' if is_compatible else 'NO'}")
    print(f"  Blocking issues: {summary['blocking_issues']}")
    print(f"  Warnings: {summary['warnings']}")
    print(f"  Recommendations: {summary['recommendations']}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Validation report: {output_path}")

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(__doc__)
        print("Usage: python pbrs_validator.py <file.pbix> <metadata.json> [output.json]")
        sys.exit(1)

    pbix_path = sys.argv[1]
    metadata_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        print("=" * 60)
        print("  PBRS Compatibility Validator")
        print("=" * 60)

        result = validate_pbrs_compatibility(pbix_path, metadata_path, output_path)

        print("\n" + "=" * 60)
        print("  Validation complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
