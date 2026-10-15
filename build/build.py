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

Installers (made automatically after the app is built; --no-installer skips them):
    Windows  dist/AdvancedAstrophotoAnalyzer-<version>-windows-x64-setup.exe
             (needs Inno Setup 6: winget install JRSoftware.InnoSetup)
    macOS    dist/AdvancedAstrophotoAnalyzer-<version>-macos-arm64.dmg  (drag to Applications)
             dist/AdvancedAstrophotoAnalyzer-<version>-macos-arm64.pkg  (installer wizard)
             (uses hdiutil and pkgbuild, which come with macOS)
"""

from __future__ import annotations

import argparse
import os
import platform
import plistlib
import re
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
APP_NAME = "Advanced Astrophoto Analyzer"
INSTALLER_BASE = "AdvancedAstrophotoAnalyzer"
BUNDLE_ID = "se.miklosoft.advastro"


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
    ap.add_argument("--no-installer", action="store_true",
                    help="skip the Windows Setup.exe / macOS .dmg and .pkg")
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
        if not args.no_installer:
            if sys.platform == "win32":
                packages += build_windows_installer(out_dir, ver, tag)
            elif sys.platform == "darwin":
                packages += build_macos_installers(out_dir, ver, tag)

    print("\nDone.")
    for archive in packages:
        print(f"  {archive.name}  ({archive.stat().st_size / 1e6:.0f} MB)  in {archive.parent}")
    if sys.platform == "darwin":
        print("  Unsigned: open the app (or the .pkg) with right-click > Open the first time, "
              "or allow it under System Settings > Privacy & Security.")
    elif sys.platform == "win32":
        print("  Unsigned: in the SmartScreen dialog choose More info > Run anyway.")
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


SYSTEM_ACCOUNTS = ("root", "runner", "runneradmin", "builder")


def private_strings() -> list[bytes]:
    """The source folder, home folder and user name of this machine, as they could appear
    inside a build. Shared system and CI accounts (root, runner) are not personal and are
    left out: library wheels are often built under /root."""
    texts = {str(ROOT), ROOT.as_posix()}
    home = Path.home()
    if home.name.lower() not in SYSTEM_ACCOUNTS:
        texts |= {str(home), home.as_posix()}
        if len(home.name) >= 4:
            texts |= {f"Users/{home.name}", f"Users\\{home.name}", f"home/{home.name}"}
    out = []
    for t in texts:
        out += [t.encode("utf-8"), t.encode("utf-16-le")]
        if "\\" in t:
            out.append(t.replace("\\", "\\\\").encode("utf-8"))   # escaped, as in JSON
    return out


def check_private(paths: list[Path]) -> None:
    """Stop the build if a file in it contains this machine's home folder or user name."""
    step("Privacy check (no local paths or user name in the build)")
    needles = private_strings()
    bad = []
    for root in paths:
        files = [root] if root.is_file() else [f for f in root.rglob("*") if f.is_file()]
        for f in files:
            data = f.read_bytes()
            if any(n in data for n in needles):
                bad.append(str(f))
            if f.suffix.lower() in (".exe", "") and data[:4] in (b"MZ\x90\x00", b"\x7fELF") \
                    or f.parent.name == "MacOS":
                bad += [f"{f} > {h}" for h in _exe_private_hits(f, needles)]
    if bad:
        raise SystemExit("Build stopped: these files contain your home folder or user name:\n  "
                         + "\n  ".join(bad[:20]))
    print("  clean")


def _exe_private_hits(exe: Path, needles: list[bytes]) -> list[str]:
    """Files packed (compressed) inside a PyInstaller executable that contain a needle."""
    import tempfile

    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

    try:
        reader = CArchiveReader(str(exe))
    except Exception:          # not a PyInstaller executable
        return []
    bad = []
    for name in reader.toc:
        data = reader.extract(name)
        if not data:
            continue
        if name.endswith(".pyz"):  # the compiled Python modules, each compressed on its own
            with tempfile.TemporaryDirectory() as tmp:
                pyz = Path(tmp) / "x.pyz"
                pyz.write_bytes(data)
                zr = ZlibArchiveReader(str(pyz))
                for mod in zr.toc:
                    code = zr.extract(mod, raw=True)
                    if code and any(n in code for n in needles):
                        bad.append(f"{name}:{mod}")
        elif any(n in data for n in needles):
            bad.append(name)
    return bad


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
    check_private([exe])

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
    name = APP_NAME
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
    check_private([app_dir])

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


def numeric_version(ver: str) -> str:
    """'0.1.0.dev0' -> '0.1.0.0': the four plain numbers Windows wants."""
    nums = [int(n) for n in re.findall(r"\d+", ver.split("dev")[0].split("rc")[0])][:4]
    return ".".join(str(n) for n in (nums + [0, 0, 0, 0])[:4])


def find_iscc() -> Path | None:
    """Inno Setup's compiler: on PATH, or in its usual install folders."""
    found = shutil.which("iscc") or shutil.which("ISCC.exe")
    if found:
        return Path(found)
    roots = [os.environ.get(k) for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    for root in filter(None, roots):
        for sub in ("Inno Setup 6", r"Programs\Inno Setup 6"):
            exe = Path(root) / sub / "ISCC.exe"
            if exe.is_file():
                return exe
    return None


def build_windows_installer(out_dir: Path, ver: str, tag: str) -> list[Path]:
    step("Windows installer (Inno Setup)")
    iscc = find_iscc()
    if iscc is None:
        print("  Inno Setup 6 was not found, so no Setup.exe this time (the zip is still made).\n"
              "  Install it once with:  winget install JRSoftware.InnoSetup\n"
              "  or from https://jrsoftware.org/isdl.php, then build again.")
        return []
    name = f"{INSTALLER_BASE}-{ver}-{tag}-setup"
    cmd = [str(iscc), "/Qp",
           f"/DAppVersion={ver}", f"/DNumericVersion={numeric_version(ver)}",
           f"/DAppDir={out_dir / APP_NAME}", f"/DRootDir={ROOT}",
           f"/DOutputDir={DIST}", f"/DOutputName={name}"]
    cli = out_dir / "advastro.exe"
    if cli.is_file():
        cmd.append(f"/DCliExe={cli}")
    cmd.append(str(BUILD / "installer" / "windows" / "AdvAstro.iss"))
    run(cmd)
    setup = DIST / f"{name}.exe"
    if not setup.is_file():
        raise SystemExit(f"Installer failed: {setup} was not created.")
    return [setup]


def build_macos_installers(out_dir: Path, ver: str, tag: str) -> list[Path]:
    """A drag-to-Applications disk image and a standard installer package."""
    app = out_dir / f"{APP_NAME}.app"
    stage = WORK / "macos-installer"
    shutil.rmtree(stage, ignore_errors=True)
    made = []

    step("macOS disk image (.dmg)")
    dmg_root = stage / "dmg"
    dmg_root.mkdir(parents=True)
    # ditto copies the bundle with its symlinks, permissions and extended attributes.
    run(["ditto", str(app), str(dmg_root / app.name)])
    (dmg_root / "Applications").symlink_to("/Applications")
    shutil.copy(ROOT / "LICENSE", dmg_root / "LICENSE.txt")
    dmg = DIST / f"{INSTALLER_BASE}-{ver}-{tag}.dmg"
    dmg.unlink(missing_ok=True)
    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", str(dmg_root),
         "-fs", "HFS+", "-format", "UDZO", "-imagekey", "zlib-level=9", "-ov", str(dmg)])
    made.append(dmg)

    step("macOS installer package (.pkg)")
    pkg_root = stage / "pkg"
    pkg_root.mkdir(parents=True)
    run(["ditto", str(app), str(pkg_root / app.name)])
    plist = stage / "component.plist"
    run(["pkgbuild", "--analyze", "--root", str(pkg_root), str(plist)])
    with open(plist, "rb") as fh:
        comps = plistlib.load(fh)
    for c in comps:                 # always install into /Applications, never "move" an old copy
        c["BundleIsRelocatable"] = False
    with open(plist, "wb") as fh:
        plistlib.dump(comps, fh)
    pkg = DIST / f"{INSTALLER_BASE}-{ver}-{tag}.pkg"
    pkg.unlink(missing_ok=True)
    run(["pkgbuild", "--root", str(pkg_root), "--component-plist", str(plist),
         "--install-location", "/Applications", "--identifier", BUNDLE_ID,
         "--version", numeric_version(ver), str(pkg)])
    made.append(pkg)
    return made


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nBuild stopped: command failed with exit code {exc.returncode}.")
        raise SystemExit(exc.returncode) from None
