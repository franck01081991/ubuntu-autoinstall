#!/usr/bin/env bash
set -euo pipefail
COMMIT="${1:-unknown}"
MARKER="/etc/anssi-profile"
STAMP="$(date --iso-8601=seconds)"
cat <<YAML >"${MARKER}"
profile: anssi
applied_at: "${STAMP}"
source_commit: "${COMMIT}"
YAML
chmod 0644 "${MARKER}"
