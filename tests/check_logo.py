"""Rebuild the logo set from logo/reference/original-bird.png and byte-compare it with the shipped logo/ folders.

    python tests/check_logo.py

Runs neon_logo.py, render_lockups.py and export_brand.py into a temporary folder (the repo is not touched) and
compares every file in normal/, inverted/ and web/ byte for byte, including missing and extra files. Exit 1 on any
difference. Byte equality holds for the pinned versions in logo/tools/requirements.txt on Windows; other versions or
platforms may differ in PNG compression or font rasterising while the image stays the same, so a difference here is a
prompt to look, not proof of a broken pipeline.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "logo" / "tools"
FOLDERS = ("normal", "inverted", "web")


def run(script, *args):
    result = subprocess.run([sys.executable, str(TOOLS / script), *args], capture_output=True, text=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(f"FAIL: {script} exited {result.returncode}")


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        work, out = Path(tmp) / "work", Path(tmp) / "out"
        run("neon_logo.py", "--work", str(work))
        run("render_lockups.py", "--work", str(work))
        run("export_brand.py", "--work", str(work), "--out", str(out))
        compared = 0
        for folder in FOLDERS:
            shipped = {p.name: p for p in (ROOT / "logo" / folder).iterdir() if p.is_file()}
            built = {p.name: p for p in (out / folder).iterdir() if p.is_file()}
            for name in sorted(set(shipped) | set(built)):
                if name not in built:
                    print(f"FAIL  {folder}/{name}: shipped but not rebuilt")
                    failures += 1
                elif name not in shipped:
                    print(f"FAIL  {folder}/{name}: rebuilt but not shipped")
                    failures += 1
                elif shipped[name].read_bytes() != built[name].read_bytes():
                    print(f"FAIL  {folder}/{name}: bytes differ")
                    failures += 1
                else:
                    compared += 1
        print(f"{compared} files byte-identical to the shipped set")
        if compared == 0:
            failures += 1
            print("FAIL  nothing was compared")
    print("ALL PASS" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
