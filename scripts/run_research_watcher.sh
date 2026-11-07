#!/bin/zsh

# CuSelect-AI — Scheduled Research Watcher
#
# PSEUDOCODE
# 1. Find the CuSelect-AI project directory.
# 2. Switch to the project directory.
# 3. Set Python's module search path.
# 4. Execute the Research Watcher in save-and-record mode.
# 5. Propagate errors to the macOS scheduler.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT/src"

exec /opt/anaconda3/envs/cuselect/bin/python \
    -m cuselect.watcher_cli \
    --save \
    --record
