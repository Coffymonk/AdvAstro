# Building Advanced Astrophoto Analyzer

One build script, `build.py`, builds both the desktop app and the command-line tool on
every platform. The launchers
below create a private Python environment in `build/.venv` the first time, then
run it. Each build runs the tests, builds a standalone executable with
PyInstaller, checks that it starts, and packages it.

PyInstaller cannot cross-compile, so build each version on its own system.
GitHub Actions does all three automatically when you push a version tag.

| Platform | Command (from the repository folder) | Result in `dist/` |
| --- | --- | --- |
| Windows 10/11 | `build\build_windows.bat` (or double-click it) | **`AdvancedAstrophotoAnalyzer-…-windows-x64-setup.exe`**, `advastro-app-…-windows-x64.zip`, `advastro-cli-…-windows-x64.zip` |
| macOS (Apple Silicon) | `./build/build_macos.sh` | **`AdvancedAstrophotoAnalyzer-…-macos-arm64.dmg`**, **`…-macos-arm64.pkg`**, `advastro-app-…-macos-arm64.zip` (contains the .app), `advastro-cli-…-macos-arm64.tar.gz` |
| Linux | `./build/build_linux.sh` | `advastro-app-…-linux-x64.tar.gz`, `advastro-cli-…-linux-x64.tar.gz` |

The unpacked app and tool are also left in `dist/<platform>/`. On Windows, start the app
with `dist\windows-x64\Advanced Astrophoto Analyzer\Advanced Astrophoto Analyzer.exe`.

## Installers

The installers are made automatically after the app is built and checked.

**Windows: `…-setup.exe`** is made with [Inno Setup 6](https://jrsoftware.org/isinfo.php)
(free). If it is not installed, `build_windows.bat` offers to install it with
`winget install JRSoftware.InnoSetup`; without it you still get the zip files. The
installer:

- installs for all users in *Program Files*, or just for the current user without
  administrator rights (the user chooses);
- adds a Start-menu entry, an optional desktop shortcut and an uninstaller
  (*Settings › Apps*);
- installs the command-line tool in `cli\` and can add it to the user's PATH (removed again
  on uninstall);
- shows the GPL licence, speaks English or Swedish, and upgrades an earlier version in
  place.

The script is `installer/windows/AdvAstro.iss`. Its `AppId` identifies the program for
upgrades: never change it.

**macOS: `.dmg` and `.pkg`** are made with `hdiutil` and `pkgbuild`, which come with macOS.
The disk image holds the app and a shortcut to *Applications* to drag it onto. The package
is a standard installer wizard that puts the app in `/Applications`
(identifier `se.miklosoft.advastro`).

Use `--no-installer` to skip them.

## User manual as PDF

`python build/make_manual.py` writes the manual in English and Swedish to
`dist/AdvancedAstrophotoAnalyzer-<version>-manual-en.pdf` and `…-sv.pdf`, with a cover,
contents and page numbers. It uses the same text as the manual in the app
(`src/advastro/help/`). It needs `pip install markdown playwright` and
`python -m playwright install chromium` once. The release workflow does this for you.

## Privacy check

Every build is checked for the build computer's home folder and user name (including inside
the packed executables), and stops if they turn up. The package metadata is bundled without
`direct_url.json`, which pip fills with the local source folder.

## Requirements

- Python 3.12 or newer
  - Windows: installer from python.org (tick "Add python.exe to PATH")
  - macOS: `brew install python@3.12` or the python.org installer
  - Linux: `sudo apt install python3.12 python3.12-venv` (or your distro's equivalent)
- Internet access on the first run, to install the dependencies

On macOS and Linux, make the scripts executable once after cloning:
`chmod +x build/*.sh`

## Options

Options go after the launcher, e.g. `build\build_windows.bat --skip-tests`.

| Option | Effect |
| --- | --- |
| `--skip-tests` | Skip pytest (faster local builds) |
| `--skip-install` | Do not reinstall dependencies |
| `--clean` | Delete earlier build output first |
| `--only gui` / `--only cli` | Build only the desktop app or only the command-line tool |
| `--no-installer` | Skip the Windows Setup.exe and the macOS .dmg and .pkg |

## Releases on GitHub

Push a version tag and GitHub Actions builds all three platforms with this same
script, then publishes a release with the packages and the source code:

```
git tag v1.0.0
git push origin v1.0.0
```

## Not signed yet

Builds and installers are not code-signed. On Windows choose *More info → Run anyway*
in the SmartScreen dialog. On macOS right-click the app or the `.pkg` and choose *Open*,
or allow it under *System Settings → Privacy & Security*. Signing needs a code-signing
certificate (Windows) and an Apple Developer ID with notarization (macOS); both can be
added to `build.py` later without changing anything else.

## Files in this folder

| File | Purpose |
| --- | --- |
| `build.py` | The build logic, shared by all platforms and by GitHub Actions |
| `advastro-gui.spec` | PyInstaller recipe for the desktop app (folder build; `.app` on macOS) |
| `advastro-cli.spec` | PyInstaller recipe for the command-line executable |
| `entry_gui.py`, `entry_cli.py` | Entry points bundled into the app and the tool |
| `make_manual.py` | The user manual as PDF files |
| `specutil.py` | Helpers for the spec files (package metadata without local paths) |
| `installer/windows/AdvAstro.iss` | Inno Setup script for the Windows installer |
| `icons/` | App icon: `src/*.svg` drawings, `png/` at 16–1024 px, `.ico` (Windows), `.icns` (macOS), `advastro.svg` (Linux). Regenerate with `python build/icons/make_icons.py` |
| `hooks/` | PyInstaller hooks for astropy and photutils |
| `build_windows.ps1` / `.bat` | Windows launchers |
| `build_unix.sh` | Shared macOS/Linux launcher |
| `build_macos.sh`, `build_linux.sh` | Named shortcuts to `build_unix.sh` |
