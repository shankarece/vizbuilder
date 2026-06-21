"""
pbix_patch.py
-------------
Core engine: strips SecurityBindings from a PBIX and injects a modified
Report/Layout. Works with any PBI Desktop version (Sept 2024, May 2025, etc).

Why SecurityBindings must be removed:
    PBI Desktop stores a DPAPI-encrypted integrity hash in SecurityBindings.
    Any external change to the PBIX — even 1 byte — causes MashupValidationError
    on open. Removing SecurityBindings bypasses this check. PBI Desktop
    regenerates it automatically on the next File → Save.

Usage (standalone):
    python pbix_patch.py <input.pbix> <layout_file> <output.pbix>

Normally called by build.py — you don't need to run this directly.
"""

import zipfile
import os
import sys


# These entries are stored uncompressed inside the PBIX zip.
# DataModel is already internally compressed (AS XPress9 format).
STORED_ENTRIES = {"DataModel"}


def patch_pbix(input_path: str, layout_path: str, output_path: str) -> None:
    """
    Build a new PBIX from input_path with:
      - SecurityBindings removed
      - Report/Layout replaced with the contents of layout_path
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input PBIX not found: {input_path}")
    if not os.path.exists(layout_path):
        raise FileNotFoundError(f"Layout file not found: {layout_path}")

    new_layout_bytes = open(layout_path, "rb").read()

    with zipfile.ZipFile(input_path, "r") as src, \
         zipfile.ZipFile(output_path, "w") as dst:

        entries = src.infolist()
        if not entries:
            raise ValueError("Input PBIX appears to be empty or invalid.")

        for item in entries:
            # Strip the integrity binding — Desktop regenerates on Save
            if item.filename == "SecurityBindings":
                print(f"  Removed:  {item.filename}")
                continue

            name   = os.path.basename(item.filename)
            method = zipfile.ZIP_STORED if name in STORED_ENTRIES \
                     else zipfile.ZIP_DEFLATED

            info              = zipfile.ZipInfo(item.filename)
            info.date_time    = item.date_time
            info.compress_type = method

            if item.filename == "Report/Layout":
                dst.writestr(info, new_layout_bytes)
                print(f"  Replaced: {item.filename}  ({len(new_layout_bytes):,} bytes)")
            else:
                dst.writestr(info, src.read(item.filename))
                print(f"  Copied:   {item.filename}")

    size_kb = os.path.getsize(output_path) // 1024
    print(f"\n  Output:  {output_path}  ({size_kb:,} KB)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        print("Usage: python pbix_patch.py <input.pbix> <layout_file> <output.pbix>")
        sys.exit(1)

    try:
        patch_pbix(sys.argv[1], sys.argv[2], sys.argv[3])
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
