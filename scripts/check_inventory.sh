#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  echo "usage: $0 HOST" >&2
  exit 2
fi

FILE="baremetal/inventory/host_vars/${HOST}/secrets.sops.yaml"
if [[ ! -f "$FILE" ]]; then
  echo "[-] ${FILE} missing"
  exit 1
fi

pass=""

# 1) Essai avec sops --extract (renvoie souvent une chaîne JSON entre guillemets)
if command -v sops >/dev/null 2>&1; then
  if out="$(sops -d --extract '["encrypt_disk_passphrase"]' "$FILE" 2>/dev/null || true)"; then
    # strip guillemets éventuels au début/fin
    pass="$(printf '%s' "$out" | sed -e 's/^"//' -e 's/"$//')"
  fi
fi

# 2) Fallback: lecture brute de la ligne YAML si non chiffré
if [[ -z "${pass}" ]]; then
  if line="$(grep -E '^[[:space:]]*encrypt_disk_passphrase:' "$FILE" | head -n1 || true)"; then
    pass="$(printf '%s' "$line" | sed -E 's/^[[:space:]]*encrypt_disk_passphrase:[[:space:]]*//; s/^"//; s/"$//')"
  fi
fi

if [[ -z "${pass}" ]]; then
  echo "[-] encrypt_disk_passphrase is empty/not found for host '$HOST'"
  exit 1
fi

echo "[+] Inventory OK for '$HOST' (LUKS passphrase present)"
