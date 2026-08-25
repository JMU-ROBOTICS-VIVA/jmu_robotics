#!/usr/bin/env bash
# Atomically publish a TurtleBot fleet status JSON file over SSH.
#
# Usage:
#   publish_status.sh LOCAL_JSON REMOTE_HOST REMOTE_PATH
#
# Example:
#   publish_status.sh /var/lib/jmu_tb4/status.json webuser@www.example.edu \
#       /var/www/html/turtlebot/status.json

set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 LOCAL_JSON REMOTE_HOST REMOTE_PATH" >&2
    exit 2
fi

LOCAL_JSON="$1"
REMOTE_HOST="$2"
REMOTE_PATH="$3"
REMOTE_TMP="${REMOTE_PATH}.new"

test -r "$LOCAL_JSON"

# Copy to a temporary name first, then rename on the remote host.  rename(2)
# is atomic when source and destination are on the same filesystem.
rsync -q --chmod=F644 "$LOCAL_JSON" "${REMOTE_HOST}:${REMOTE_TMP}"
ssh -q "$REMOTE_HOST" "mv -- '$REMOTE_TMP' '$REMOTE_PATH'"
