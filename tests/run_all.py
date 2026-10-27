"""Run every check in the repo, in order, and print one summary.

    python tests/run_all.py [--docs]

1. tokens: build_tokens.py --check (every stack's token file matches tokens.json)
2. png: no metadata chunks in any PNG or ICO
3. logo: rebuild the logo set from the reference image and byte-compare it
4. react: npm install, tsc --noEmit (strict), esbuild bundle          (skipped without npm)
5. web: Playwright checks of the demo page and the React smoke page
6. wpf: build the dictionaries, check fonts and keys, render offscreen  (skipped without dotnet)
7. winforms: compile, check fonts and GDI text, render offscreen        (skipped without dotnet)
8. netfx: the WinForms C# and WPF XAML build for .NET Framework 4.8      (skipped without dotnet)
9. grafana: examples rebuild, panel scripts parse, guards bite, panel logic in Chromium; plus a live Grafana run
   when RT_GRAFANA_URL and credentials are set (see tests/check_grafana.py)
--docs writes the screenshots to docs/screenshots/ instead of tests/output/.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"


def main():
    docs = "--docs" in sys.argv
    shots = ROOT / ("docs/screenshots" if docs else "tests/output")
    shots.mkdir(parents=True, exist_ok=True)
    npm = shutil.which("npm")
    dotnet = shutil.which("dotnet")
    py = sys.executable
    steps = [
        ("tokens", [py, str(ROOT / "tokens" / "build_tokens.py"), "--check"], ROOT, True),
        ("png", [py, str(TESTS / "check_png_chunks.py")], ROOT, True),
        ("logo", [py, str(TESTS / "check_logo.py")], ROOT, True),
        ("react install", [npm or "npm", "install", "--no-audit", "--no-fund"], TESTS / "react", bool(npm)),
        ("react typecheck", [npm or "npm", "run", "typecheck"], TESTS / "react", bool(npm)),
        ("react build", [npm or "npm", "run", "build"], TESTS / "react", bool(npm)),
        ("web", [py, str(TESTS / "check_web.py")] + (["--docs"] if docs else []), ROOT, True),
        ("wpf", [dotnet or "dotnet", "run", "-c", "Release", "--", str(shots / "wpf-sample.png")], TESTS / "wpf", bool(dotnet)),
        ("winforms", [dotnet or "dotnet", "run", "-c", "Release", "--", str(shots / "winforms-sample.png")], TESTS / "winforms", bool(dotnet)),
        ("netfx", [dotnet or "dotnet", "build", "-c", "Release"], TESTS / "netfx", bool(dotnet)),
        ("grafana", [py, str(TESTS / "check_grafana.py")] + (["--docs"] if docs else []), ROOT, True),
    ]
    results = []
    for name, cmd, cwd, available in steps:
        if not available:
            results.append((name, "SKIP (tool not installed)"))
            continue
        print(f"\n===== {name} =====", flush=True)
        # npm is a .cmd file on Windows, which needs the shell to start.
        code = subprocess.run(cmd, cwd=cwd, shell=(cmd[0] == npm and sys.platform == "win32")).returncode
        results.append((name, "PASS" if code == 0 else f"FAIL (exit {code})"))
        if name in ("wpf", "winforms") and code == 0:
            # The .NET PNG encoders add sRGB, gAMA and pHYs chunks; keep the screenshots pixel-data only.
            subprocess.run([py, str(TESTS / "check_png_chunks.py"), "--strip", str(shots / f"{name}-sample.png")])
    print("\n===== summary =====")
    for name, outcome in results:
        print(f"{outcome:<28} {name}")
    return 1 if any(o.startswith("FAIL") for _, o in results) else 0


if __name__ == "__main__":
    sys.exit(main())
