#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-}"
if [ -z "$HOST" ]; then
  echo "usage: $0 HOST" >&2
  exit 2
fi
FILE="baremetal/inventory/host_vars/${HOST}/secrets.sops.yaml"
if [ ! -f "$FILE" ]; then
  echo "[-] ${FILE} missing"
  exit 1
fi

# Try to extract with sops; if it fails (no keys), fallback to plaintext grep.
pass="$(sops -d --extract '["encrypt_disk_passphrase"]' "$FILE" 2>/dev/null || true)"
if [ -z "$pass" ]; then
  pass="$(awk -F': *' '/^encrypt_disk_passphrase:/ {print $2}' "$FILE" | tr -d '"'"'\"'"' | xargs || true)"
fi

if [ -z "$pass" ]; then
  echo "[-] encrypt_disk_passphrase is empty/not found for host '$HOST'"
  exit 1
fi

echo "[+] Inventory OK for '$HOST' (LUKS passphrase present)"
