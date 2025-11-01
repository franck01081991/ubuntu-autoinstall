#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

if [[ $# -ne 1 || -z "${1}" ]]; then
  echo "Usage: $0 <target>" >&2
  exit 1
fi

TARGET_NAME="$1"
CONFIG_PATH="baremetal/autoinstall/generated/${TARGET_NAME}/user-data"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "cloud-init config not found: ${CONFIG_PATH}" >&2
  exit 1
fi

cloud-init schema --config-file "${CONFIG_PATH}"
