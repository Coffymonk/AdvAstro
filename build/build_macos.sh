#!/usr/bin/env bash
# Build Advanced Astrophoto Analyzer on macOS (Apple Silicon). See build/README.md.
exec "$(dirname "${BASH_SOURCE[0]}")/build_unix.sh" "$@"
