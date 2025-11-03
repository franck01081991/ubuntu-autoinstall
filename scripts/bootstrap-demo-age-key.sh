#!/usr/bin/env bash
set -euo pipefail

DEFAULT_KEY_FILE="$HOME/.config/sops/age/keys.txt"
TARGET_FILE="${BOOTSTRAP_AGE_KEY_FILE:-${SOPS_AGE_KEY_FILE:-${1:-$DEFAULT_KEY_FILE}}}"
TARGET_DIR="$(dirname "${TARGET_FILE}")"

mkdir -p "${TARGET_DIR}"

if [[ -f "${TARGET_FILE}" && "${BOOTSTRAP_OVERWRITE:-0}" != "1" ]]; then
  printf "age identity already exists at %s (set BOOTSTRAP_OVERWRITE=1 to replace)\n" "${TARGET_FILE}"
  exit 0
fi

tmp_key="$(mktemp)"
trap 'rm -f "${tmp_key}"' EXIT

age-keygen -o "${tmp_key}" >/dev/null
chmod 600 "${tmp_key}"
mv "${tmp_key}" "${TARGET_FILE}"

public_recipient="$(age-keygen -y "${TARGET_FILE}")"

printf "Generated demo age identity at %s\n" "${TARGET_FILE}"
printf "Public recipient: %s\n" "${public_recipient}"
if [[ -z "${SOPS_AGE_KEY_FILE:-}" ]]; then
  printf "Export SOPS_AGE_KEY_FILE to reuse this key: export SOPS_AGE_KEY_FILE=%s\n" "${TARGET_FILE}"
fi
