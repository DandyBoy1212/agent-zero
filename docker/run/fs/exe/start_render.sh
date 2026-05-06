#!/bin/bash
# start_render.sh — Render-specific startup script
# Bypasses supervisord and runs run_ui.py directly on port 10000
# Files are pre-copied to /a0 at Docker build time — no cp at runtime.
# This ensures Flask starts in <1 second, well within Render's health check window.

# Activate the pre-built venv directly
source /opt/venv-a0/bin/activate

echo "=== Starting Agent Zero on 0.0.0.0:10000 ==="
cd /a0
exec python /a0/run_ui.py \
    --host=0.0.0.0 \
    --port=10000 \
    --dockerized=true
