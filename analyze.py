"""
analyze.py
----------
Orchestrate all PBIX analyzers: metadata extraction, lineage, reports.

Usage:
    python analyze.py <file.pbix>                    Full analysis
    python analyze.py <file.pbix> --output reports/  Save all outputs
    python analyze.py <file.pbix> --metadata-only    Extract metadata only
    python analyze.py <file.pbix> --lineage-only     Lineage analysis only

Compatible with: PBRS (offline analysis)
"""

import sys
import os
import json
import tempfile
from pathlib import Path

from pbix_analyzer import analyze_pbix
from data_lineage import analyze_lineage


def analyze(pbix_path: str, output_dir: str = None, metadata_only: bool = False,
            lineage_only: bool = False) -> dict:
    """
    Run complete PBIX analysis pipeline.

    Parameters
    ----------
    pbix_path : str
        Path to .pbix file
    output_dir : str, optional
        Directory to save outputs. If None, uses temp directory.
    metadata_only : bool
        Only extract metadata
    lineage_only : bool
        Only analyze lineage (requires metadata.json)

    Returns
    -------
    dict : Analysis results {metadata, lineage}
    """

    if not os.path.exists(pbix_path):
        raise FileNotFoundError(f"PBIX not found: {pbix_path}")

    # Setup output directory
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    else:
        os.makedirs(output_dir, exist_ok=True)

    pbix_name = Path(pbix_path).stem
    metadata_file = os.path.join(output_dir, f"{pbix_name}_metadata.json")
    lineage_file = os.path.join(output_dir, f"{pbix_name}_lineage.json")

    results = {}

    # Phase 1: Extract Metadata
    if not lineage_only:
        print(f"\nPhase 1/2: Extracting metadata...")
        metadata = analyze_pbix(pbix_path, metadata_file)
        results["metadata"] = metadata
        print(f"[OK] Metadata extracted: {metadata_file}")

    if metadata_only:
        return results

    # Phase 2: Analyze Lineage
    print(f"\nPhase 2/2: Analyzing lineage...")
    if not os.path.exists(metadata_file):
        raise FileNotFoundError(f"Metadata file not found. Run without --lineage-only first.")
    lineage = analyze_lineage(metadata_file, lineage_file)
    results["lineage"] = lineage
    print(f"[OK] Lineage analyzed: {lineage_file}")

    return results


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        print(__doc__)
        sys.exit(1)

    pbix_path = args[0]
    output_dir = None
    metadata_only = "--metadata-only" in flags
    lineage_only = "--lineage-only" in flags

    # Parse --output flag
    if "--output" in flags:
        idx = flags.index("--output")
        if idx + 1 < len(flags) and not flags[idx + 1].startswith("--"):
            output_dir = flags[idx + 1]
        else:
            output_dir = "./pbix_analysis"

    print("=" * 60)
    print("  PBIX Analyzer Suite")
    print("=" * 60)
    print(f"  File: {pbix_path}")
    if output_dir:
        print(f"  Output: {output_dir}")

    try:
        results = analyze(pbix_path, output_dir, metadata_only, lineage_only)

        print("\n" + "=" * 60)
        print("  Analysis complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
