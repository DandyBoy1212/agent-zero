#!/bin/bash
# start_render.sh — Render-specific startup script
# Bypasses supervisord and runs run_ui.py directly on port 10000
# This is the correct approach for Render web services which expect
# a single process binding to a single port.

set -e

echo "=== Render startup: copying /git/agent-zero to /a0 ==="
if [ ! -f "/a0/run_ui.py" ]; then
    cp -rn --no-preserve=ownership,mode /git/agent-zero/. /a0
fi

echo "=== Activating venv ==="
. /ins/setup_venv.sh local

echo "=== Starting Agent Zero on 0.0.0.0:10000 ==="
cd /a0
exec python /a0/run_ui.py \
    --host=0.0.0.0 \
    --port=10000 \
    --dockerized=true
