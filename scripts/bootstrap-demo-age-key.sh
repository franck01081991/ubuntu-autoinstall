#!/usr/bin/env bash
set -euo pipefail

DEFAULT_KEY_FILE="$HOME/.config/sops/age/keys.txt"
TARGET_FILE="${BOOTSTRAP_AGE_KEY_FILE:-${SOPS_AGE_KEY_FILE:-${1:-$DEFAULT_KEY_FILE}}}"
TARGET_DIR="$(dirname "${TARGET_FILE}")"

mkdir -p "${TARGET_DIR}"
cat <<'KEY' >"${TARGET_FILE}"
# demo age identity for ubuntu-autoinstall training only
AGE-SECRET-KEY-1X9SCJNY3MVQ97NJ870586FG0VQVZ693ZN7HT0D67U25K3HV4Q5CQUUQEKF
KEY
chmod 600 "${TARGET_FILE}"

printf "Wrote demo age identity to %s\n" "${TARGET_FILE}"
printf "Public recipient: %s\n" "age1akkcd4nm65lekere3zuem7v3fxqxp3sz2mzpqvs9lh98ffq98psqjl9y6r"
if [[ -z "${SOPS_AGE_KEY_FILE:-}" ]]; then
  printf "Export SOPS_AGE_KEY_FILE to reuse this key: export SOPS_AGE_KEY_FILE=%s\n" "${TARGET_FILE}"
fi
