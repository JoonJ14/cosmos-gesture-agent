#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/executor"

python3 -m venv .venv
source .venv/bin/activate
pip install setuptools
pip install --no-build-isolation -e .

uvicorn executor.main:app --host 127.0.0.1 --port 8787 --reload
