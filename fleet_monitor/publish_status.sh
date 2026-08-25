#!/usr/bin/env bash
# Validate and atomically publish the private fleet snapshot into the web root.
# This is run as root by a short-lived systemd oneshot service.

set -euo pipefail

CONFIG="/etc/jmu_tb4/fleet-monitor.conf"

if [ ! -r "$CONFIG" ]; then
    echo "ERROR: Fleet monitor config not found: $CONFIG" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG"

if [ ! -s "$STATUS_FILE" ]; then
    echo "No fleet status file to publish yet: $STATUS_FILE"
    exit 0
fi

now=$(date +%s)
mtime=$(stat -c %Y "$STATUS_FILE")
age=$((now - mtime))

if (( age > MAX_PUBLISH_AGE_SECONDS )); then
    echo "Not publishing stale fleet status: ${age}s old (limit ${MAX_PUBLISH_AGE_SECONDS}s)"
    exit 0
fi

# Do not replace the last known-good public snapshot with malformed JSON.
python3 -m json.tool "$STATUS_FILE" >/dev/null

install -d -o root -g root -m 0755 "$WEB_ROOT"

# Copy to a temporary file INSIDE the web directory, then rename it atomically.
# Apache/nginx therefore sees either the old complete status.json or the new
# complete status.json, never a partially-written file.
tmp="${WEB_STATUS_FILE}.new.$$"
trap 'rm -f "$tmp"' EXIT

install -o root -g root -m 0644 "$STATUS_FILE" "$tmp"
mv -f "$tmp" "$WEB_STATUS_FILE"

trap - EXIT
