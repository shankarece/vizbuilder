"""
make_release.py
---------------
Build one versioned zip of vizbuilder to hand to colleagues.

    python make_release.py                 tests, then dist/vizbuilder-<version>.zip
    python make_release.py --skip-tests    package without running the tests
    python make_release.py --out D:\\share  write the zip somewhere else

The version comes from the VERSION file (bump it, add a CHANGELOG.md entry,
then run this). The zip unpacks to one folder, vizbuilder-<version>/, and a
matching .sha256 file is written so the recipient can check the download.

Only files a colleague needs are included: the scripts, .bat launchers,
skills/, demo/, tests/ and the docs. Working notes, caches and git data are left
out, and so is every .pbix file except the two made-up samples in demo/verify/.
.bat files are written with Windows line endings.
"""

import hashlib
import os
import subprocess
import sys
import zipfile

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# Top-level files that are working notes, not part of a release.
EXCLUDED_FILES = {"REVIEW_SUMMARY.md", "DEVIN_TASK.md"}
INCLUDED_SUFFIXES = (".py", ".bat", ".md", ".txt")
INCLUDED_FILES = {"VERSION"}
INCLUDED_DIRS = ("skills", "tests", "demo")
SKIPPED_PARTS = {"__pycache__", ".git", "dist"}
SKIPPED_SUFFIXES = (".pyc", ".pyo", ".pbix", ".pbit", ".layout")
# The only .pbix files that ship: made-up Northwind data for the Desktop check.
ALLOWED_SAMPLES = ("demo/verify/northwind_sample.pbix", "demo/verify/Northwind-check.pbix")


def read_version(repo_dir: str = REPO_DIR) -> str:
    with open(os.path.join(repo_dir, "VERSION"), encoding="utf-8") as f:
        version = f.read().strip()
    if not version:
        raise ValueError("VERSION file is empty")
    return version


def collect_files(repo_dir: str = REPO_DIR) -> list:
    """Return the release's files as sorted repo-relative posix paths."""
    files = []
    for name in os.listdir(repo_dir):
        path = os.path.join(repo_dir, name)
        if os.path.isfile(path):
            wanted = name in INCLUDED_FILES or name.endswith(INCLUDED_SUFFIXES)
            if wanted and name not in EXCLUDED_FILES:
                files.append(name)

    for top in INCLUDED_DIRS:
        for root, dirs, names in os.walk(os.path.join(repo_dir, top)):
            dirs[:] = [d for d in dirs if d not in SKIPPED_PARTS]
            for name in names:
                rel = os.path.relpath(os.path.join(root, name), repo_dir).replace(os.sep, "/")
                if name.endswith(SKIPPED_SUFFIXES) and rel not in ALLOWED_SAMPLES:
                    continue
                files.append(rel)
    return sorted(files)


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release(out_dir: str = None, repo_dir: str = REPO_DIR,
                  run_tests: bool = True) -> str:
    """Write the release zip and its .sha256; return the zip path."""
    version = read_version(repo_dir)

    if run_tests:
        print("  Running tests before packaging...")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "tests"],
            cwd=repo_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr.strip()[-2000:])
            raise RuntimeError("Tests failed; release not built.")

    out_dir = out_dir or os.path.join(repo_dir, "dist")
    os.makedirs(out_dir, exist_ok=True)
    root_name = f"vizbuilder-{version}"
    zip_path = os.path.join(out_dir, f"{root_name}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in collect_files(repo_dir):
            source = os.path.join(repo_dir, *rel.split("/"))
            if rel.endswith(".bat"):
                with open(source, "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                z.writestr(f"{root_name}/{rel}", data)
            else:
                z.write(source, f"{root_name}/{rel}")

    digest = sha256_of(zip_path)
    with open(zip_path + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{digest}  {os.path.basename(zip_path)}\n")
    return zip_path


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out_dir = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            print("Error: --out needs a folder path.")
            return 1
        out_dir = argv[i + 1]

    try:
        zip_path = build_release(out_dir, run_tests="--skip-tests" not in argv)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"Error: {e}")
        return 1

    size_kb = os.path.getsize(zip_path) // 1024
    print(f"\n  Release: {zip_path}  ({size_kb:,} KB)")
    print(f"  SHA-256: {sha256_of(zip_path)}")
    print("  Share the .zip (and the .sha256 next to it).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
