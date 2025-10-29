#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-}"
if [ -z "$HOST" ]; then
  echo "Usage: $0 <HOST>"; exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BAREMETAL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTOINSTALL_DIR="${BAREMETAL_ROOT}/autoinstall"
OUTDIR="${AUTOINSTALL_DIR}/generated/${HOST}"
[ -d "$OUTDIR" ] || { echo "Missing $OUTDIR. Run: make baremetal/gen HOST=${HOST}"; exit 1; }
USER_DATA="${OUTDIR}/user-data"
META_DATA="${OUTDIR}/meta-data"
ISO="${OUTDIR}/seed-${HOST}.iso"
xorriso -as mkisofs -V CIDATA -o "${ISO}" -J -l "${USER_DATA}" "${META_DATA}"
REL_ISO="$(realpath --relative-to="${BAREMETAL_ROOT}" "${ISO}" 2>/dev/null || echo "${ISO}")"
echo "Created ${REL_ISO}"
