#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-}"
if [ -z "$HOST" ]; then
  echo "Usage: $0 <HOST>"; exit 1
fi
OUTDIR="autoinstall/generated/${HOST}"
[ -d "$OUTDIR" ] || { echo "Missing $OUTDIR. Run: make gen HOST=${HOST}"; exit 1; }
USER_DATA="${OUTDIR}/user-data"
META_DATA="${OUTDIR}/meta-data"
ISO="${OUTDIR}/seed-${HOST}.iso"
xorriso -as mkisofs -V CIDATA -o "${ISO}" -J -l "${USER_DATA}" "${META_DATA}"
echo "Created ${ISO}"
