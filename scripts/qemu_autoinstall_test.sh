#!/usr/bin/env bash
set -euo pipefail
ISO="${1:-baremetal/autoinstall/generated/ci-demo/ubuntu-autoinstall.iso}"
RAM="${RAM:-2048}"
TIMEOUT="${TIMEOUT:-900}"

if [ ! -f "$ISO" ]; then
  echo "ISO not found: $ISO" >&2; exit 1
fi

echo "[*] Booting QEMU (timeout ${TIMEOUT}s)"
set +e
timeout --preserve-status "${TIMEOUT}" \
qemu-system-x86_64 \
  -m "${RAM}" -smp 2 \
  -enable-kvm \
  -nographic \
  -serial mon:stdio \
  -drive file="${ISO}",media=cdrom,if=virtio \
  -drive file=/tmp/autoinstall-test.qcow2,if=virtio,format=qcow2 \
  -boot d \
  -no-reboot
rc=$?
set -e

if [ $rc -eq 124 ]; then
  echo "[-] Timeout (increase TIMEOUT or check cloud-init logs)"
  exit 1
fi

echo "[+] QEMU exited with code $rc"
