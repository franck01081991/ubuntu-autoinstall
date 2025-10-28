#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-}"; ISO_IN="${2:-}"
if [ -z "$HOST" ] || [ -z "$ISO_IN" ]; then
  echo "Usage: $0 <HOST> <UBUNTU_ISO>"; exit 1
fi
OUTDIR="autoinstall/generated/${HOST}"
[ -d "$OUTDIR" ] || { echo "Missing $OUTDIR. Run: make gen HOST=${HOST}"; exit 1; }
[ -f "$ISO_IN" ] || { echo "Missing source ISO: $ISO_IN"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ISO_OUT="${OUTDIR}/ubuntu-autoinstall-${HOST}.iso"

# Prepare NoCloud payload
mkdir -p "$TMP/nocloud"
cp "${OUTDIR}/user-data" "${OUTDIR}/meta-data" "$TMP/nocloud/"

# Extract and patch GRUB to append autoinstall + NoCloud path
GRUB_CFG="$TMP/grub.cfg"
if ! xorriso -osirrox on -indev "$ISO_IN" -extract /boot/grub/grub.cfg "$GRUB_CFG" >/dev/null; then
  echo "Unable to extract /boot/grub/grub.cfg from $ISO_IN" >&2
  exit 1
fi
if [ ! -s "$GRUB_CFG" ]; then
  echo "Extracted grub.cfg is empty" >&2
  exit 1
fi
PATCH_ARGS="autoinstall ds=nocloud;s=/cdrom/nocloud/"
if ! grep -q "$PATCH_ARGS" "$GRUB_CFG"; then
  sed -i "s#---#--- ${PATCH_ARGS}#g" "$GRUB_CFG"
fi

# Repack ISO by replaying original boot parameters
xorriso \
  -indev "$ISO_IN" \
  -outdev "$ISO_OUT" \
  -map "$TMP/grub.cfg" /boot/grub/grub.cfg \
  -map "$TMP/nocloud" /nocloud \
  -boot_image any replay \
  >/dev/null

echo "Created ${ISO_OUT}"
