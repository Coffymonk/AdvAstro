#!/usr/bin/env bash
# Build Advanced Astrophoto Analyzer on macOS (Apple Silicon) or Linux.
#
#     ./build/build_macos.sh   or   ./build/build_linux.sh
# Extra options are passed on, e.g.  ./build/build_linux.sh --skip-tests
#
# Creates build/.venv on first run (needs Python 3.12+), then runs
# build/build.py inside it.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
VENV="$HERE/.venv"

find_python() {
    for candidate in python3.13 python3.12 python3; do
        if command -v "$candidate" >/dev/null 2>&1 &&
           "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

if [ ! -x "$VENV/bin/python" ]; then
    PY="$(find_python)" || {
        echo "Python 3.12 or newer was not found."
        echo "  macOS: brew install python@3.12   (or the installer from python.org)"
        echo "  Linux: sudo apt install python3.12 python3.12-venv   (or your distro's equivalent)"
        exit 1
    }
    echo "Creating build environment in $VENV with $PY"
    "$PY" -m venv "$VENV"
fi

cd "$ROOT"
exec "$VENV/bin/python" "$HERE/build.py" "$@"
