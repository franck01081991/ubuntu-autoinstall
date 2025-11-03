#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <HOST>" >&2
  exit 1
fi

HOST="$1"
SECRETS_FILE="baremetal/inventory/host_vars/${HOST}/secrets.sops.yaml"

if [ ! -f "$SECRETS_FILE" ]; then
  echo "Missing secrets file: $SECRETS_FILE" >&2
  exit 1
fi

if ! command -v sops >/dev/null 2>&1; then
  echo "sops command not found. Install sops to manage encrypted secrets." >&2
  exit 1
fi

PASSPHRASE="$(sops -d --extract '["encrypt_disk_passphrase"]' "$SECRETS_FILE" 2>/dev/null || true)"

if [ -z "${PASSPHRASE}" ]; then
  echo "encrypt_disk_passphrase is missing or empty in $SECRETS_FILE" >&2
  exit 1
fi

echo "✅ Inventory for ${HOST} contains an encrypted disk passphrase."
