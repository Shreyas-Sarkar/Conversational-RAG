#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/backend"

if [ -x ".venv/bin/ruff" ]; then
  ".venv/bin/ruff" check app
elif command -v ruff >/dev/null 2>&1; then
  ruff check app
else
  python3 -m ruff check app
fi
