#!/bin/bash
# start_render.sh — Render-specific startup script
# Bypasses supervisord and runs run_ui.py directly on port 10000
# Files are pre-copied to /a0 at Docker build time — no cp at runtime.
# This ensures Flask starts in <1 second, well within Render's health check window.

# Seed the persistent disk on first boot.
#
# Render mounts the disk at /a0/usr, which SHADOWS whatever the image baked in
# there. Those directories are empty in git, held open only by .gitkeep files,
# so it is tempting to conclude there is nothing to preserve. That is wrong:
# helpers/plugins.py:230 does Path(root).iterdir() on /a0/usr/plugins with no
# existence check, so a missing directory is a hard crash, not a fallback.
#
# Observed 2026-07-22 08:07, on the first boot after the disk was attached:
#   FileNotFoundError: [Errno 2] No such file or directory: '/a0/usr/plugins'
# The container then exited status 1 and restarted in a loop.
#
# /a0-usr-skel is a copy of the baked-in tree taken at build time, from OUTSIDE
# the mount point, so it survives the disk being mounted over /a0/usr.
# `cp -rn` is no-clobber: it fills an empty disk once and never overwrites real
# data on later boots. mkdir -p is belt and braces for a disk that already has
# some directories but not all.
if [ -d /a0-usr-skel ]; then
    cp -rn /a0-usr-skel/. /a0/usr/ 2>/dev/null || true
fi
mkdir -p /a0/usr/plugins /a0/usr/agents /a0/usr/skills /a0/usr/workdir \
         /a0/usr/knowledge/main /a0/usr/knowledge/solutions
echo "=== usr/ seeded: $(ls -1 /a0/usr | tr '\n' ' ') ==="

# Activate the pre-built venv directly
source /opt/venv-a0/bin/activate

echo "=== Starting Agent Zero on 0.0.0.0:10000 ==="
cd /a0
exec python /a0/run_ui.py \
    --host=0.0.0.0 \
    --port=10000 \
    --dockerized=true
