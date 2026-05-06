#!/bin/bash
# start_render.sh — Render-specific startup script
# Bypasses supervisord and runs run_ui.py directly on port 10000
# Activates the pre-built venv directly (no setup_venv.sh sourcing overhead)
set -e

# Activate the pre-built venv directly (faster than sourcing setup_venv.sh)
source /opt/venv-a0/bin/activate

# Copy fork files to /a0 if not already done
if [ ! -f "/a0/run_ui.py" ]; then
    echo "=== Copying /git/agent-zero to /a0 ==="
    cp -rn --no-preserve=ownership,mode /git/agent-zero/. /a0
fi

echo "=== Starting Agent Zero on 0.0.0.0:10000 ==="
cd /a0
exec python /a0/run_ui.py \
    --host=0.0.0.0 \
    --port=10000 \
    --dockerized=true
