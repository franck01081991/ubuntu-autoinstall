#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") --host <name> [--disk /dev/sdX] [--ssh-key "ssh-ed25519 ..."]

Initialise un hôte bare metal :
  - crée baremetal/inventory/host_vars/<name>/
  - génère main.yml et secrets.sops.yaml (placeholders)
  - ajoute l'entrée dans baremetal/inventory/hosts.yml
USAGE
}

HOST=""
DISK=""
SSH_KEY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --disk)
      DISK="${2:-}"
      shift 2
      ;;
    --ssh-key)
      SSH_KEY="${2:-}"
      shift 2
      ;;
    --profile)
      echo "Option --profile obsolète : utiliser scripts/new_host.py directement." >&2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argument non reconnu: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${HOST}" ]]; then
  echo "L'option --host est obligatoire." >&2
  usage >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python3 "${REPO_ROOT}/scripts/new_host.py" --host "${HOST}" ${DISK:+--disk "${DISK}"} ${SSH_KEY:+--ssh-key "${SSH_KEY}"}

echo "Initialisation terminée. Pensez à chiffrer baremetal/inventory/host_vars/${HOST}/secrets.sops.yaml via SOPS."
