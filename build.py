"""
build.py
--------
End-to-end script: reads a PBIX, builds the Layout with visuals defined in
visuals_config.py, and produces a patched PBIX ready to open in PBI Desktop.

Requirements:
    - Python 3.8+  (no pip installs needed — standard library only)
    - Regular PBI Desktop (same monthly version as your PBRS Desktop)

Usage:
    python build.py <input.pbix> <output.pbix> [--open]

Options:
    --open   Automatically open the output PBIX in Power BI Desktop

Example:
    python build.py MyReport.pbix MyReport-WithVisuals.pbix --open

Compatible with: PBI Desktop Sept 2024, May 2025, and later versions.
"""

import sys
import os
import tempfile
import subprocess

from layout_builder import build_layout
from pbix_patch import patch_pbix


def _find_pbi_desktop() -> str:
    """Find Power BI Desktop executable."""
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft Power BI Desktop", "bin", "PBIDesktop.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft Power BI Desktop", "bin", "PBIDesktop.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "PBIDesktop.exe"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""


def build(input_pbix: str, output_pbix: str, auto_open: bool = False) -> None:
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

    if auto_open:
        abs_path = os.path.abspath(output_pbix)
        pbi = _find_pbi_desktop()
        if pbi:
            print(f"  Opening in Power BI Desktop...")
            subprocess.Popen([pbi, abs_path])
        else:
            print(f"  Opening with default app...")
            os.startfile(abs_path)
        print()

    print("=" * 60)
    print("  Done!")
    if not auto_open:
        print()
        print("  Next steps:")
        print("  1. Open the output PBIX in regular PBI Desktop")
        print("  2. Verify visuals look correct")
        print("  3. File -> Save  (regenerates SecurityBindings)")
        print("  4. Deploy to Power BI Report Server")
    else:
        print()
        print("  The file is opening in Power BI Desktop.")
        print("  After verifying visuals: File -> Save -> deploy to PBRS.")
    print("=" * 60)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if len(args) != 2:
        print(__doc__)
        print("Usage: python build.py <input.pbix> <output.pbix> [--open]")
        sys.exit(1)

    build(args[0], args[1], auto_open="--open" in flags)
