"""
doctor.py
---------
Check that this machine is ready to use vizbuilder, in plain language.

    python doctor.py                       check the machine
    python doctor.py "C:\\work\\Sales.pbix"  also check a report you plan to use

Everything runs locally; nothing is sent anywhere. It never changes your files.
The result is [OK] (fine), [!!] (works, but read the note) or [XX] (fix this
first). Exit code 0 means nothing needs fixing.
"""

import contextlib
import importlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import zipfile

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_DIR)

OK, WARN, FAIL = "OK", "WARN", "FAIL"
ICON = {OK: "[OK]", WARN: "[!!]", FAIL: "[XX]"}
MIN_PYTHON = (3, 8)
ENGINE_MODULES = ("build", "lint", "analyze", "layout_builder", "visual_types",
                  "pbix_patch", "pbix_analyzer", "data_lineage",
                  "consistency_checker", "pbrs_validator", "desktop")
SYNCED_FOLDER_HINTS = ("onedrive", "dropbox", "google drive", "sharepoint", "icloud")


class Check:
    def __init__(self, status, name, detail="", fix=""):
        self.status, self.name, self.detail, self.fix = status, name, detail, fix


# ── Machine checks ───────────────────────────────────────────────────────────

def check_python() -> Check:
    found = sys.version_info[:3]
    text = ".".join(str(n) for n in found)
    if found[:2] >= MIN_PYTHON:
        return Check(OK, "Python", f"version {text}")
    return Check(FAIL, "Python", f"version {text} is too old",
                 f"Install Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer.")


def check_version() -> Check:
    try:
        with open(os.path.join(REPO_DIR, "VERSION"), encoding="utf-8") as f:
            return Check(OK, "vizbuilder", f"version {f.read().strip()}")
    except OSError:
        return Check(WARN, "vizbuilder", "VERSION file missing",
                     "Re-unzip the package you were given.")


def check_modules() -> Check:
    missing = []
    for name in ENGINE_MODULES:
        try:
            importlib.import_module(name)
        except Exception as e:  # any import problem means a broken install
            missing.append(f"{name} ({type(e).__name__})")
    if missing:
        return Check(FAIL, "Program files", "cannot load: " + ", ".join(missing),
                     "Re-unzip the package into a fresh folder.")
    return Check(OK, "Program files", f"all {len(ENGINE_MODULES)} modules load")


def check_desktop() -> Check:
    import desktop
    exe, label = desktop.find_desktop(desktop.RS)
    if exe:
        return Check(OK, "Power BI Desktop for Report Server", exe)
    exe, label = desktop.find_desktop(desktop.REGULAR)
    if exe:
        return Check(WARN, "Power BI Desktop for Report Server",
                     f"not found; regular Desktop found at {exe}",
                     "Prefer the Report Server edition. Set PBI_DESKTOP_PATH if it "
                     "is installed somewhere unusual.")
    return Check(WARN, "Power BI Desktop for Report Server", "not found",
                 "You can still build files; open the result by hand. If it is "
                 "installed, set PBI_DESKTOP_PATH to its PBIDesktop.exe.")


def check_self_test() -> Check:
    """Build, lint and read a tiny report end to end, in a temp folder."""
    import build as build_module
    import layout_builder
    tmp = tempfile.mkdtemp(prefix="vizbuilder-doctor-")
    saved_config = sys.modules.get("visuals_config")
    try:
        source, output = os.path.join(tmp, "in.pbix"), os.path.join(tmp, "out.pbix")
        layout = {"id": 0, "config": "{}", "sections": [{
            "id": 0, "name": "s0", "displayName": "Page 1", "filters": "[]",
            "ordinal": 0, "visualContainers": [], "config": "{}",
            "displayOption": 1, "width": 1280, "height": 720}]}
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("Version", "1.28".encode("utf-16-le"))
            z.writestr("DataModel", b"\x00model\xff" * 8, compress_type=zipfile.ZIP_STORED)
            z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))
            z.writestr("SecurityBindings", b"binding")

        config = types.ModuleType("visuals_config")
        config.PAGE_NAME, config.DASHBOARD_TITLE = "Self test", "Self test"
        config.build_visuals = lambda: [
            layout_builder.add_visual("card", {"value": "Sales[Revenue]"},
                                      x=20, y=60, w=290, h=100, vid=1, title="Revenue"),
            layout_builder.add_visual("bar", {"category": "Sales[Region]", "value": "Sales[[Margin]]"},
                                      x=20, y=180, w=600, h=290, vid=2, title="By region")]
        sys.modules["visuals_config"] = config

        with contextlib.redirect_stdout(io.StringIO()):
            build_module.build(source, output)
            import lint
            issues, visuals, _ = lint.lint(output)
        with zipfile.ZipFile(output) as z:
            if "SecurityBindings" in z.namelist():
                return Check(FAIL, "Self-test build", "output still has SecurityBindings")
            if z.read("DataModel") != b"\x00model\xff" * 8:
                return Check(FAIL, "Self-test build", "the data model was altered")
        errors = [i for i in issues if i.severity == "error"]
        if len(visuals) != 3 or errors:  # title + 2 visuals
            return Check(FAIL, "Self-test build",
                         f"expected 3 visuals and no lint errors, got {len(visuals)} / {len(errors)}")
        return Check(OK, "Self-test build",
                     "built, checked and read back a test report (data model untouched)")
    except SystemExit:
        return Check(FAIL, "Self-test build", "the build stopped early",
                     "Run python -m unittest discover tests and share the output.")
    except Exception as e:
        return Check(FAIL, "Self-test build", f"{type(e).__name__}: {e}",
                     "Run python -m unittest discover tests and share the output.")
    finally:
        if saved_config is not None:
            sys.modules["visuals_config"] = saved_config
        else:
            sys.modules.pop("visuals_config", None)
        shutil.rmtree(tmp, ignore_errors=True)


def check_optional_tools() -> list:
    checks = []
    try:
        importlib.import_module("pbixray")
        checks.append(Check(OK, "pbixray (optional)", "installed: tables, columns and "
                            "measures can be read from a .pbix offline"))
    except ImportError:
        checks.append(Check(OK, "pbixray (optional)", "not installed (fine). Without it, "
                            "field names come from the Desktop Data pane or your modeling tool"))
    checks.append(Check(OK, "Network", "vizbuilder never connects to the network"))
    return checks


def check_skills_installed() -> Check:
    skills_dir = os.path.join(os.path.expanduser("~"), ".claude", "skills")
    found = []
    if os.path.isdir(skills_dir):
        found = [d for d in os.listdir(skills_dir) if d.startswith("vizbuilder-")]
    if found:
        return Check(OK, "Assistant skills", f"{len(found)} installed in {skills_dir}")
    return Check(WARN, "Assistant skills", "not installed",
                 "Only needed if you use an AI assistant. Run: python install_skill.py")


# ── Report-file checks ───────────────────────────────────────────────────────

def check_report_file(path: str) -> list:
    checks = []
    if not os.path.isfile(path):
        return [Check(FAIL, "Report file", f"not found: {path}",
                      "Check the path. Use quotes if it has spaces.")]
    size_mb = os.path.getsize(path) / (1024 * 1024)
    checks.append(Check(OK, "Report file", f"{os.path.basename(path)} ({size_mb:.1f} MB)"))

    lowered = os.path.abspath(path).lower()
    if lowered.startswith("\\\\") or any(h in lowered for h in SYNCED_FOLDER_HINTS):
        checks.append(Check(WARN, "Report location", "a network or synced folder",
                            "Work on a copy in a plain local folder such as C:\\work\\ "
                            "(sync tools can lock the file or slow the build)."))
    else:
        checks.append(Check(OK, "Report location", "local folder"))

    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "Report/Layout" not in names:
                return checks + [Check(FAIL, "Report contents",
                                       "no Report/Layout inside; this is not a classic .pbix",
                                       "Open it in Power BI Desktop for Report Server and "
                                       "File -> Save, or use a different file.")]
            if "DataModel" not in names:
                checks.append(Check(WARN, "Report contents", "no data model inside",
                                    "Visuals can be built, but they will show no data."))
            else:
                checks.append(Check(OK, "Report contents", "report layout and data model present"))
            if "SecurityBindings" not in names:
                checks.append(Check(WARN, "Saved in Desktop?", "no SecurityBindings",
                                    "Fine as an input if you will open and save the result in "
                                    "Desktop before deploying."))
    except zipfile.BadZipFile:
        return checks + [Check(FAIL, "Report contents", "not a valid .pbix (not a zip file)",
                               "Re-copy the file; it may be damaged or still syncing.")]

    try:
        import layout_builder
        layout = layout_builder.read_layout(path)
        pages = layout.get("sections", [])
        visuals = sum(len(s.get("visualContainers", [])) for s in pages)
        checks.append(Check(OK, "Pages", f"{len(pages)} page(s), {visuals} visual(s)"))
        if not pages:
            checks.append(Check(FAIL, "Pages", "the report has no pages",
                                "Open it in Desktop, add a page, and save."))
    except Exception as e:
        checks.append(Check(FAIL, "Pages", f"cannot read the layout: {e}"))
    return checks


# ── Runner ───────────────────────────────────────────────────────────────────

def run_checks(pbix_path: str = None) -> list:
    checks = [check_python(), check_version(), check_modules()]
    if checks[-1].status == OK:
        checks += [check_desktop(), check_self_test()]
    checks += check_optional_tools()
    checks.append(check_skills_installed())
    if pbix_path:
        checks += check_report_file(pbix_path)
    return checks


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pbix_path = next((a for a in argv if not a.startswith("--")), None)

    print("=" * 60)
    print("  vizbuilder environment check")
    print("=" * 60)
    checks = run_checks(pbix_path)
    for c in checks:
        print(f"  {ICON[c.status]} {c.name}: {c.detail}")
        if c.status != OK and c.fix:
            print(f"       -> {c.fix}")

    fails = [c for c in checks if c.status == FAIL]
    warns = [c for c in checks if c.status == WARN]
    print("-" * 60)
    if fails:
        print(f"  {len(fails)} thing(s) to fix before using vizbuilder (marked [XX]).")
    elif warns:
        print(f"  Ready to use. {len(warns)} note(s) marked [!!] are worth a look.")
    else:
        print("  All good. You are ready to use vizbuilder.")
    print("=" * 60)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
