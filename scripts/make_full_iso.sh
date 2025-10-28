#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-}"; ISO_IN="${2:-}"
if [ -z "$HOST" ] || [ -z "$ISO_IN" ]; then
  echo "Usage: $0 <HOST> <UBUNTU_ISO>"; exit 1
fi
OUTDIR="autoinstall/generated/${HOST}"
[ -d "$OUTDIR" ] || { echo "Missing $OUTDIR. Run: make gen HOST=${HOST}"; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ISO_OUT="${OUTDIR}/ubuntu-autoinstall-${HOST}.iso"

# Mount/extract ISO
7z x -o"$TMP/iso" "$ISO_IN" >/dev/null

# Embed NoCloud files
mkdir -p "$TMP/iso/nocloud"
cp "${OUTDIR}/user-data" "${OUTDIR}/meta-data" "$TMP/iso/nocloud/"

# Patch GRUB to append autoinstall + NoCloud path
GRUB_CFG="$TMP/iso/boot/grub/grub.cfg"
if [ -f "$GRUB_CFG" ]; then
  PATCH_ARGS="autoinstall ds=nocloud;s=/cdrom/nocloud/"
  if ! grep -q "$PATCH_ARGS" "$GRUB_CFG"; then
    sed -i "s#---#--- ${PATCH_ARGS}#g" "$GRUB_CFG"
  fi
fi

# Repack ISO (UEFI+BIOS)
xorriso -as mkisofs -r -V "UBUNTU_AUTOINSTALL_${HOST}"   -o "$ISO_OUT"   -J -l -cache-inodes   -isohybrid-mbr "$TMP/iso/isolinux/isohdpfx.bin"   -partition_offset 16   -b isolinux/isolinux.bin -c isolinux/boot.cat   -no-emul-boot -boot-load-size 4 -boot-info-table   -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot   "$TMP/iso"

echo "Created ${ISO_OUT}"
