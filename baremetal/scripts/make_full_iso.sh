#!/usr/bin/env bash
set -euo pipefail; umask 077
: "${TMPDIR:=$PWD/.cache/tmp}"; mkdir -p "$TMPDIR"; chmod 700 "$TMPDIR"
HOST="${1:-}"; ISO_IN="${2:-}"
[ -n "${HOST}" ] && [ -n "${ISO_IN}" ] || { echo "Usage: $0 <HOST> <UBUNTU_ISO>" >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BARE="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTDIR="${BARE}/autoinstall/generated/${HOST}"
[ -d "$OUTDIR" ] || { echo "Missing $OUTDIR. Run: make gen HOST=${HOST}" >&2; exit 1; }
[ -f "$ISO_IN" ] || { echo "Missing ISO: $ISO_IN" >&2; exit 1; }
ISO_OUT="${OUTDIR}/ubuntu-autoinstall-${HOST}.iso"
PATCH="autoinstall ds=nocloud;s=/cdrom/nocloud/"
WORK="$(mktemp -d -p "$TMPDIR" autoinstall.XXXXXX)"; trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/nocloud"
cp "${OUTDIR}/user-data" "${OUTDIR}/meta-data" "$WORK/nocloud/"
write_grub() {
  local p="$1"
  cat > "$p" <<EOF
set default=0
set timeout_style=hidden
set timeout=0
menuentry 'Auto Install Ubuntu Server' {
    linux   /casper/vmlinuz ${PATCH} ---
    initrd  /casper/initrd
}
EOF
}
declare -a MAP
GRUB="$WORK/grub.cfg"; write_grub "$GRUB"; MAP+=("-map" "$GRUB" /boot/grub/grub.cfg)
LOOP="$WORK/loopback.cfg"; write_grub "$LOOP"; MAP+=("-map" "$LOOP" /boot/grub/loopback.cfg)
MAP+=("-map" "$WORK/nocloud" /nocloud)
rm -f "$ISO_OUT"
xorriso -indev "$ISO_IN" -outdev "$ISO_OUT" "${MAP[@]}" -boot_image any replay >/dev/null
REL="$(realpath --relative-to="${BARE}" "${ISO_OUT}" 2>/dev/null || echo "${ISO_OUT}")"
echo "Created ${REL}"
