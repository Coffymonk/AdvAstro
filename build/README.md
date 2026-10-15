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
| Windows 10/11 | `build\build_windows.bat` (or double-click it) | `advastro-app-…-windows-x64.zip`, `advastro-cli-…-windows-x64.zip` |
| macOS (Apple Silicon) | `./build/build_macos.sh` | `advastro-app-…-macos-arm64.zip` (contains the .app), `advastro-cli-…-macos-arm64.tar.gz` |
| Linux | `./build/build_linux.sh` | `advastro-app-…-linux-x64.tar.gz`, `advastro-cli-…-linux-x64.tar.gz` |

The unpacked app and tool are also left in `dist/<platform>/`. On Windows, start the app
with `dist\windows-x64\Advanced Astrophoto Analyzer\Advanced Astrophoto Analyzer.exe`.

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

## Releases on GitHub

Push a version tag and GitHub Actions builds all three platforms with this same
script, then publishes a release with the packages and the source code:

```
git tag v0.1.0
git push origin v0.1.0
```

## Not signed yet

Builds are not code-signed. On Windows choose *More info → Run anyway* in the
SmartScreen dialog. On macOS right-click the file and choose *Open*, or allow it
under *System Settings → Privacy & Security*.

## Files in this folder

| File | Purpose |
| --- | --- |
| `build.py` | The build logic, shared by all platforms and by GitHub Actions |
| `advastro-gui.spec` | PyInstaller recipe for the desktop app (folder build; `.app` on macOS) |
| `advastro-cli.spec` | PyInstaller recipe for the command-line executable |
| `entry_gui.py`, `entry_cli.py` | Entry points bundled into the app and the tool |
| `icons/` | App icon: `src/*.svg` drawings, `png/` at 16–1024 px, `.ico` (Windows), `.icns` (macOS), `advastro.svg` (Linux). Regenerate with `python build/icons/make_icons.py` |
| `hooks/` | PyInstaller hooks for astropy and photutils |
| `build_windows.ps1` / `.bat` | Windows launchers |
| `build_unix.sh` | Shared macOS/Linux launcher |
| `build_macos.sh`, `build_linux.sh` | Named shortcuts to `build_unix.sh` |

Proper installers (an `.exe` setup for Windows, a `.dmg` for macOS, an AppImage for Linux)
come later; for now the app is delivered as a zipped folder.
