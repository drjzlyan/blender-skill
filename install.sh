#!/usr/bin/env bash
# Thin wrapper around the Python installer.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -eq 0 ]; then
  set -- setup --harness auto
fi
exec python3 "$ROOT/scripts/blender_skill.py" "$@"
