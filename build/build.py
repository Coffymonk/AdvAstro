#!/usr/bin/env python3
"""Build Advanced Astrophoto Analyzer for the platform this script runs on.

Usage (from the repository root or the build folder):

    python build/build.py               # test, build, package
    python build/build.py --skip-tests  # faster, for quick local builds
    python build/build.py --clean       # remove previous build output first
    python build/build.py --only gui    # only the desktop app

PyInstaller cannot cross-compile: build the Windows version on Windows, the
macOS version on a Mac and the Linux version on Linux. The GitHub Actions
release workflow runs this same script on all three.

Output:
    dist/<platform>/advastro[.exe]                        command-line tool
    dist/<platform>/Advanced Astrophoto Analyzer[.app]               desktop app
    dist/advastro-cli-<version>-<platform>.zip|.tar.gz    ready to upload
    dist/advastro-app-<version>-<platform>.zip|.tar.gz    ready to upload
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
WORK = BUILD / "work"  # PyInstaller temporary files (ignored by Git)
DIST = ROOT / "dist"
MIN_PYTHON = (3, 12)


def platform_tag() -> str:
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(
        machine, machine)
    return f"{system}-{arch}"


def version() -> str:
    sys.path.insert(0, str(ROOT / "src"))
    from advastro import __version__

    return __version__


def run(cmd: list[str]) -> None:
    print("  >", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def step(text: str) -> None:
    print(f"\n== {text}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--skip-tests", action="store_true", help="do not run pytest first")
    ap.add_argument("--skip-install", action="store_true",
                    help="do not pip install the project and build tools")
    ap.add_argument("--clean", action="store_true", help="delete earlier build output first")
    ap.add_argument("--only", choices=["all", "cli", "gui"], default="all",
                    help="build only the command-line tool or only the desktop app")
    args = ap.parse_args()

    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required "
              f"(this is {platform.python_version()}).")
        return 1

    tag = platform_tag()
    ver = version()
    out_dir = DIST / tag
    print(f"Advanced Astrophoto Analyzer {ver}  |  {tag}  |  Python {platform.python_version()}")

    if args.clean:
        step("Cleaning")
        for folder in (WORK, out_dir):
            shutil.rmtree(folder, ignore_errors=True)

    if not args.skip_install:
        step("Installing project and build tools")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])

    if not args.skip_tests:
        step("Running tests")
        run([sys.executable, "-m", "pytest", "-q"])

    targets = ["cli", "gui"] if args.only == "all" else [args.only]
    packages = []
    if "cli" in targets:
        packages.append(build_cli(out_dir, ver, tag))
    if "gui" in targets:
        packages.append(build_gui(out_dir, ver, tag))

    print("\nDone.")
    for archive in packages:
        print(f"  {archive.name}  ({archive.stat().st_size / 1e6:.0f} MB)  in {archive.parent}")
    if sys.platform == "darwin":
        print("  Unsigned: open the app with right-click > Open the first time, or allow it "
              "under System Settings > Privacy & Security.")
    return 0


# Distributions bundled into the executables; their licence files travel with every build.
BUNDLED = ["numpy", "scipy", "astropy", "pyerfa", "astropy-iers-data", "photutils", "pillow",
           "tifffile", "imagecodecs", "lz4", "zstandard", "PyYAML", "packaging"]
LICENSE_WORDS = ("LICENSE", "LICENCE", "COPYING", "NOTICE", "AUTHORS")


def collect_licenses(dest: Path, gui: bool) -> Path:
    """Copy CREDITS, our licence and every bundled library's licence files into dest/licenses."""
    from importlib import metadata

    lic = dest / "licenses"
    if lic.exists():
        shutil.rmtree(lic)
    lic.mkdir(parents=True)
    shutil.copy(ROOT / "LICENSE", lic / "AdvAstro-GPL-3.0.txt")
    shutil.copy(ROOT / "CREDITS.md", lic / "CREDITS.md")
    shutil.copy(ROOT / "src" / "advastro" / "data" / "OPENNGC.md", lic / "OpenNGC-CC-BY-SA-4.0.md")
    names = BUNDLED + (["PySide6-Essentials", "shiboken6"] if gui else [])
    for name in names:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        target = lic / f"{name}-{dist.version}"
        for f in dist.files or []:
            if any(w in f.name.upper() for w in LICENSE_WORDS):
                src = Path(dist.locate_file(f))
                if src.is_file():
                    target.mkdir(exist_ok=True)
                    # Keep the sub-path: several vendored parts use the same file name.
                    flat = str(f).replace("/", "_").replace("\\", "_")
                    shutil.copy(src, target / flat)
        meta = dist.metadata
        if not target.exists():           # no licence file shipped: record what the metadata says
            target.mkdir()
            licence = meta.get("License-Expression") or meta.get("License")
            (target / "LICENSE-INFO.txt").write_text(
                f"{name} {dist.version}\nLicence: {licence}\nHome: {meta.get('Home-page') or ''}\n",
                encoding="utf-8")
    if gui:                                # Qt for Python: LGPL-3.0
        shutil.copy(ROOT / "licenses" / "LGPL-3.0.txt", lic / "Qt-LGPL-3.0.txt")
    return lic


def pyinstaller(spec: str, out_dir: Path) -> None:
    run([sys.executable, "-m", "PyInstaller", str(BUILD / spec), "--noconfirm",
         "--distpath", str(out_dir), "--workpath", str(WORK)])


def build_cli(out_dir: Path, ver: str, tag: str) -> Path:
    step("Building the command-line tool")
    pyinstaller("advastro-cli.spec", out_dir)
    exe = out_dir / ("advastro.exe" if sys.platform == "win32" else "advastro")
    if not exe.is_file():
        raise SystemExit(f"Build failed: {exe} was not created.")
    step("Smoke test: command-line tool")
    run([str(exe), "--version"])

    base = f"advastro-cli-{ver}-{tag}"
    extras = [ROOT / "LICENSE", ROOT / "README.md", ROOT / "CREDITS.md"]
    lic = collect_licenses(out_dir / "cli-licenses", gui=False)
    if sys.platform == "win32":
        archive = DIST / f"{base}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe, f"{base}/{exe.name}")
            for f in extras:
                zf.write(f, f"{base}/{f.name}")
            for f in lic.rglob("*"):
                zf.write(f, f"{base}/licenses/{f.relative_to(lic)}")
    else:
        archive = DIST / f"{base}.tar.gz"
        with tarfile.open(archive, "w:gz") as tf:
            tf.add(exe, f"{base}/{exe.name}")  # keeps the executable bit
            for f in extras:
                tf.add(f, f"{base}/{f.name}")
            tf.add(lic, f"{base}/licenses")
    return archive


def build_gui(out_dir: Path, ver: str, tag: str) -> Path:
    step("Building the desktop app")
    pyinstaller("advastro-gui.spec", out_dir)
    name = "Advanced Astrophoto Analyzer"
    if sys.platform == "darwin":
        app_dir = out_dir / f"{name}.app"
        exe = app_dir / "Contents" / "MacOS" / name
    else:
        app_dir = out_dir / name
        exe = app_dir / (f"{name}.exe" if sys.platform == "win32" else name)
    if not exe.is_file():
        raise SystemExit(f"Build failed: {exe} was not created.")

    step("Smoke test: desktop app (opens and closes the main window off-screen)")
    run([str(exe), "--smoke-test"])

    # Licences next to the program (inside Contents/Resources on macOS).
    collect_licenses(app_dir / "Contents" / "Resources" if sys.platform == "darwin" else app_dir,
                     gui=True)

    base = f"advastro-app-{ver}-{tag}"
    if sys.platform == "darwin":
        # ditto keeps the app bundle's symlinks and metadata intact.
        archive = DIST / f"{base}.zip"
        run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app_dir),
             str(archive)])
    elif sys.platform == "win32":
        archive = DIST / f"{base}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in app_dir.rglob("*"):
                zf.write(f, f"{name}/{f.relative_to(app_dir)}")
    else:
        archive = DIST / f"{base}.tar.gz"
        with tarfile.open(archive, "w:gz") as tf:
            tf.add(app_dir, name)
    return archive


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nBuild stopped: command failed with exit code {exc.returncode}.")
        raise SystemExit(exc.returncode) from None
