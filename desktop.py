"""
desktop.py
----------
Locate and launch Power BI Desktop for the --open flag of build.py and lint.py.

Two editions can be installed side by side:
    - Power BI Desktop for Report Server ("RS")  -> ...\\Microsoft Power BI Desktop RS\\bin
    - Regular Power BI Desktop                   -> ...\\Microsoft Power BI Desktop\\bin
                                                    or the Microsoft Store app

Because vizbuilder targets Power BI Report Server, the RS edition is preferred
when it is installed: saving in it produces a file the server always accepts.

Overrides:
    --rs            open in Power BI Desktop for Report Server only
    --regular       open in regular Power BI Desktop only
    PBI_DESKTOP_PATH=<path to PBIDesktop.exe>   use this exact executable
"""

import os
import subprocess

RS = "rs"
REGULAR = "regular"
AUTO = "auto"

EDITION_LABELS = {
    RS: "Power BI Desktop (Report Server)",
    REGULAR: "Power BI Desktop",
}


def _candidates(edition: str) -> list:
    pf = os.environ.get("ProgramFiles", "")
    pf86 = os.environ.get("ProgramFiles(x86)", "")
    local = os.environ.get("LOCALAPPDATA", "")
    if edition == RS:
        folder = "Microsoft Power BI Desktop RS"
        return [os.path.join(base, folder, "bin", "PBIDesktop.exe")
                for base in (pf, pf86) if base]
    folder = "Microsoft Power BI Desktop"
    paths = [os.path.join(base, folder, "bin", "PBIDesktop.exe")
             for base in (pf, pf86) if base]
    if local:
        paths.append(os.path.join(local, "Microsoft", "WindowsApps", "PBIDesktop.exe"))
    return paths


def find_desktop(prefer: str = AUTO) -> tuple:
    """Return (exe_path, label) for the Desktop to use, or ("", "") if none.

    prefer: "auto" (RS first, then regular), "rs", or "regular".
    """
    override = os.environ.get("PBI_DESKTOP_PATH", "")
    if override:
        if os.path.isfile(override):
            return override, f"PBI_DESKTOP_PATH ({override})"
        print(f"  Warning: PBI_DESKTOP_PATH not found: {override}")

    order = {RS: [RS], REGULAR: [REGULAR]}.get(prefer, [RS, REGULAR])
    for edition in order:
        for path in _candidates(edition):
            if os.path.isfile(path):
                return path, EDITION_LABELS[edition]
    return "", ""


def prefer_from_flags(flags: list) -> str:
    """Map command-line flags to a find_desktop() preference."""
    if "--rs" in flags:
        return RS
    if "--regular" in flags:
        return REGULAR
    return AUTO


def open_in_desktop(pbix_path: str, prefer: str = AUTO) -> bool:
    """Open pbix_path in Power BI Desktop. Returns True if a launch was started."""
    abs_path = os.path.abspath(pbix_path)
    exe, label = find_desktop(prefer)
    if exe:
        print(f"  Opening in {label}...")
        subprocess.Popen([exe, abs_path])
        return True

    if prefer == RS:
        print("  Power BI Desktop for Report Server not found.")
        print("  Install it from the Report Server download page, or set PBI_DESKTOP_PATH.")
        return False

    if hasattr(os, "startfile"):
        print("  Opening with the default app for .pbix...")
        os.startfile(abs_path)
        return True

    print(f"  Cannot open automatically on this OS. Open manually: {abs_path}")
    return False
