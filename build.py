"""
build.py
--------
End-to-end script: reads a PBIX, builds the Layout with visuals defined in
visuals_config.py, and produces a patched PBIX ready to open in PBI Desktop.

Requirements:
    - Python 3.8+  (no pip installs needed — standard library only)
    - Regular PBI Desktop (same monthly version as your PBRS Desktop)

Usage:
    python build.py <input.pbix> <output.pbix>

Example:
    python build.py MyReport.pbix MyReport-WithVisuals.pbix

After running:
    1. Open <output.pbix> in regular PBI Desktop
    2. Verify visuals look correct
    3. File -> Save   (this regenerates SecurityBindings)
    4. Close Desktop
    5. Deploy the saved file to Power BI Report Server

Compatible with: PBI Desktop Sept 2024, May 2025, and later versions.
"""

import sys
import os
import tempfile

from layout_builder import build_layout
from pbix_patch import patch_pbix


def build(input_pbix: str, output_pbix: str) -> None:
    print("=" * 60)
    print("  PBIX Visual Builder")
    print("=" * 60)
    print(f"  Input:  {input_pbix}")
    print(f"  Output: {output_pbix}")
    print()

    if not os.path.exists(input_pbix):
        print(f"Error: Input file not found: {input_pbix}")
        sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".layout", delete=False) as tmp:
        layout_tmp = tmp.name

    try:
        print("Step 1/2  Building layout with visuals...")
        build_layout(input_pbix, layout_tmp)

        print("\nStep 2/2  Patching PBIX...")
        patch_pbix(input_pbix, layout_tmp, output_pbix)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

    finally:
        if os.path.exists(layout_tmp):
            os.remove(layout_tmp)

    print()
    print("=" * 60)
    print("  Done!")
    print()
    print("  Next steps:")
    print("  1. Open the output PBIX in regular PBI Desktop")
    print("  2. Verify visuals look correct")
    print("  3. File -> Save  (regenerates SecurityBindings)")
    print("  4. Deploy to Power BI Report Server")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        print("Usage: python build.py <input.pbix> <output.pbix>")
        sys.exit(1)

    build(sys.argv[1], sys.argv[2])
