"""
build.py
--------
End-to-end script: reads a PBIX, builds the Layout with visuals defined in
visuals_config.py, and produces a patched PBIX ready to open in PBI Desktop.

Requirements:
    - Python 3.8+  (no pip installs needed — standard library only)
    - Power BI Desktop for Report Server (recommended), or regular
      PBI Desktop from the same monthly release as your Report Server

Usage:
    python build.py <input.pbix> <output.pbix> [--config my_dashboard.py]
                    [--open] [--rs | --regular]
    python build.py --version

Options:
    --config F  Use F as the dashboard definition instead of visuals_config.py.
                Keep your own copy outside the tool folder so upgrading the
                tool never overwrites your work.
    --open      Open the output PBIX in Power BI Desktop. Uses Power BI
                Desktop for Report Server when installed, else regular Desktop.
    --rs        With --open: only use Power BI Desktop for Report Server
    --regular   With --open: only use regular Power BI Desktop
    PBI_DESKTOP_PATH=<PBIDesktop.exe>  env var to force a specific executable

Example:
    python build.py MyReport.pbix MyReport-WithVisuals.pbix --open

Compatible with: PBI Desktop Sept 2024, May 2025, and later versions.
"""

import importlib.util
import sys
import os
import tempfile

from desktop import AUTO, open_in_desktop, prefer_from_flags
from layout_builder import build_layout, pbrs_visual_warnings
from pbix_patch import patch_pbix


def get_version() -> str:
    """Return the release version from the VERSION file ("unknown" if absent)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip() or "unknown"
    except OSError:
        return "unknown"


def load_config(path: str) -> None:
    """Load a dashboard definition file so layout_builder uses it.

    layout_builder does `import visuals_config` when it builds, so registering
    the module under that name is enough. Nothing is written to disk.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    spec = importlib.util.spec_from_file_location("visuals_config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["visuals_config"] = module


def build(input_pbix: str, output_pbix: str, auto_open: bool = False,
          prefer: str = AUTO, config_path: str = None) -> None:
    print("=" * 60)
    print(f"  PBIX Visual Builder  v{get_version()}")
    print("=" * 60)
    print(f"  Input:  {input_pbix}")
    print(f"  Output: {output_pbix}")
    if config_path:
        print(f"  Config: {config_path}")
    print()

    if not os.path.exists(input_pbix):
        print(f"Error: Input file not found: {input_pbix}")
        sys.exit(1)
    if os.path.abspath(input_pbix) == os.path.abspath(output_pbix):
        print("Error: Output must be a different file from the input.")
        sys.exit(1)

    if config_path:
        try:
            load_config(config_path)
        except Exception as e:
            print(f"Error: could not load config: {e}")
            sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".layout", delete=False) as tmp:
        layout_tmp = tmp.name

    try:
        print("Step 1/2  Building layout with visuals...")
        layout = build_layout(input_pbix, layout_tmp)

        warnings = pbrs_visual_warnings(layout)
        if warnings:
            print("\n  PBRS Desktop compatibility warnings:")
            for w in warnings:
                print(f"    ! {w}")

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
        auto_open = open_in_desktop(output_pbix, prefer)
        print()

    print("=" * 60)
    print("  Done!")
    if not auto_open:
        print()
        print("  Next steps:")
        print("  1. Open the output PBIX in Power BI Desktop for Report Server")
        print("     (or regular Desktop from the same monthly release)")
        print("  2. Verify visuals look correct")
        print("  3. File -> Save  (regenerates SecurityBindings)")
        print("  4. Deploy to Power BI Report Server")
    else:
        print()
        print("  The file is opening in Power BI Desktop.")
        print("  After verifying visuals: File -> Save -> deploy to PBRS.")
    print("=" * 60)


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if "--version" in argv:
        print(f"vizbuilder {get_version()}")
        return

    # --config takes the next argument as its value
    config_path = None
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--config":
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                print("Error: --config needs a file path.")
                sys.exit(1)
            config_path = argv[i + 1]
            i += 1
        else:
            rest.append(argv[i])
        i += 1

    args = [a for a in rest if not a.startswith("--")]
    flags = [a for a in rest if a.startswith("--")]

    if len(args) != 2:
        print(__doc__)
        print("Usage: python build.py <input.pbix> <output.pbix> "
              "[--config file.py] [--open] [--rs | --regular]")
        sys.exit(1)

    build(args[0], args[1], auto_open="--open" in flags,
          prefer=prefer_from_flags(flags), config_path=config_path)


if __name__ == "__main__":
    main()
