#!/usr/bin/env bash
# Create and activate venv, then install required Python packages for backend
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install PyPDF2
pip install "sentence-transformers>=2.2.2"
# pinecone python package is published as `pinecone`
pip install "pinecone>=2.3.0"

echo "Virtualenv ready. Activate with: source backend/.venv/bin/activate"
