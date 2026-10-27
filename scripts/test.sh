#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
(cd backend && ../.venv/bin/python -m pytest -q)
(cd frontend && npm test && npm run build)
