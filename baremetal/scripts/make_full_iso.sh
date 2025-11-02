#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-}"; ISO_IN="${2:-}"
if [ -z "$HOST" ] || [ -z "$ISO_IN" ]; then
  echo "Usage: $0 <HOST> <UBUNTU_ISO>"; exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BAREMETAL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTOINSTALL_DIR="${BAREMETAL_ROOT}/autoinstall"
OUTDIR="${AUTOINSTALL_DIR}/generated/${HOST}"
[ -d "$OUTDIR" ] || { echo "Missing $OUTDIR. Run: make baremetal/gen HOST=${HOST}"; exit 1; }
[ -f "$ISO_IN" ] || { echo "Missing source ISO: $ISO_IN"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ISO_OUT="${OUTDIR}/ubuntu-autoinstall-${HOST}.iso"

mkdir -p "$TMP/nocloud"
cp "${OUTDIR}/user-data" "${OUTDIR}/meta-data" "$TMP/nocloud/"

PATCH_ARGS="autoinstall ds=nocloud;s=/cdrom/nocloud/"

patch_kernel_args() {
  local cfg_path="$1"
  python3 - "$cfg_path" "$PATCH_ARGS" <<'PY'
import pathlib
import sys

cfg_file = pathlib.Path(sys.argv[1])
needle = sys.argv[2]
content = cfg_file.read_text()

if needle in content:
    sys.exit(0)

newline = content.endswith("\n")
patched = False

if " ---" in content:
    content = content.replace(" ---", f" --- {needle}")
    patched = True
else:
    lines = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("linux ") or stripped.startswith("linuxefi ") or stripped.startswith("append "):
            line = f"{line} {needle}"
            patched = True
        lines.append(line)
    content = "\n".join(lines)
    if newline:
        content += "\n"

if not patched:
    print(f"Warning: unable to inject autoinstall arguments into {cfg_file}", file=sys.stderr)

cfg_file.write_text(content)
PY
}

declare -a MAP_ARGS

extract_and_patch() {
  local iso_path="$1"
  local tmp_path="$2"
  local required="${3:-}"

  if xorriso -osirrox on -indev "$ISO_IN" -extract "$iso_path" "$tmp_path" >/dev/null 2>&1; then
    if [ ! -s "$tmp_path" ]; then
      echo "Extracted $iso_path is empty" >&2
      exit 1
    fi
    patch_kernel_args "$tmp_path"
    MAP_ARGS+=("-map" "$tmp_path" "$iso_path")
  else
    if [ "$required" = "required" ]; then
      echo "Failed to extract required file $iso_path from $ISO_IN" >&2
      exit 1
    fi
    echo "Warning: unable to locate $iso_path in $ISO_IN" >&2
  fi
}

GRUB_CFG="$TMP/grub.cfg"
extract_and_patch /boot/grub/grub.cfg "$GRUB_CFG" required

LOOPBACK_CFG="$TMP/loopback.cfg"
extract_and_patch /boot/grub/loopback.cfg "$LOOPBACK_CFG"

ISOLINUX_CFG="$TMP/isolinux-txt.cfg"
extract_and_patch /isolinux/txt.cfg "$ISOLINUX_CFG" required

MAP_ARGS+=("-map" "$TMP/nocloud" /nocloud)

xorriso \
  -indev "$ISO_IN" \
  -outdev "$ISO_OUT" \
  "${MAP_ARGS[@]}" \
  -boot_image any replay \
  >/dev/null

REL_ISO="$(realpath --relative-to="${BAREMETAL_ROOT}" "${ISO_OUT}" 2>/dev/null || echo "${ISO_OUT}")"
echo "Created ${REL_ISO}"
