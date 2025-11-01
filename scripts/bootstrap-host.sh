#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") --host <name> --profile <hardware_profile>

Initialise un hôte bare metal :
  - crée baremetal/inventory/host_vars/<name>/
  - génère main.yml pré-rempli
  - copie secrets.sops.yaml de l'exemple
  - ajoute l'hôte dans baremetal/inventory/hosts.yml
USAGE
}

HOST=""
PROFILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --profile)
      PROFILE="${2:-}"
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

if [[ -z "${HOST}" || -z "${PROFILE}" ]]; then
  echo "Les options --host et --profile sont obligatoires." >&2
  usage >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOST_VARS_ROOT="${REPO_ROOT}/baremetal/inventory/host_vars"
EXAMPLE_DIR="${HOST_VARS_ROOT}/example"
HOST_DIR="${HOST_VARS_ROOT}/${HOST}"
MAIN_FILE="${HOST_DIR}/main.yml"
SECRETS_FILE="${HOST_DIR}/secrets.sops.yaml"
HOSTS_FILE="${REPO_ROOT}/baremetal/inventory/hosts.yml"

if [[ ! -d "${EXAMPLE_DIR}" ]]; then
  echo "Répertoire d'exemple introuvable: ${EXAMPLE_DIR}" >&2
  exit 1
fi

mkdir -p "${HOST_DIR}"

tmp_main=""
cleanup() {
  if [[ -n "${tmp_main}" && -f "${tmp_main}" ]]; then
    rm -f "${tmp_main}"
  fi
}
trap cleanup EXIT

if [[ ! -f "${MAIN_FILE}" ]]; then
  tmp_main="$(mktemp)"
  cat >"${tmp_main}" <<EOF_MAIN
---
hostname: ${HOST}
hardware_profile: ${PROFILE}
netmode: dhcp
# Secrets (password_hash, ssh_authorized_keys, etc.) sont gérés via
# 'secrets.sops.yaml' adjacent chiffré avec SOPS.
EOF_MAIN
  install -m 0644 "${tmp_main}" "${MAIN_FILE}"
  rm -f "${tmp_main}"
  tmp_main=""
  echo "Création de ${MAIN_FILE}"
else
  echo "${MAIN_FILE} existe déjà, aucune modification"
fi

if [[ ! -f "${SECRETS_FILE}" ]]; then
  install -m 0640 "${EXAMPLE_DIR}/secrets.sops.yaml" "${SECRETS_FILE}"
  echo "Copie de secrets.sops.yaml vers ${SECRETS_FILE}"
else
  echo "${SECRETS_FILE} existe déjà, aucune copie"
fi

python3 - "${HOST}" "${HOSTS_FILE}" <<'PY'
import pathlib
import sys

import yaml

host = sys.argv[1]
hosts_file = pathlib.Path(sys.argv[2])

if hosts_file.exists():
    original_text = hosts_file.read_text(encoding="utf-8")
else:
    original_text = ""

data = yaml.safe_load(original_text) if original_text.strip() else {}

all_section = data.setdefault("all", {})
children = all_section.setdefault("children", {})
baremetal = children.setdefault("baremetal", {})
hosts = baremetal.setdefault("hosts", {}) or {}
baremetal["hosts"] = hosts

added = False
if host not in hosts:
    hosts[host] = {}
    added = True

new_text = "---\n" + yaml.safe_dump(data, sort_keys=False, default_flow_style=False)

if new_text != original_text:
    hosts_file.write_text(new_text, encoding="utf-8")
    if added:
        print(f"Ajout de {host} dans {hosts_file}")
    else:
        print(f"Normalisation de {hosts_file} (aucun nouvel hôte)")
else:
    print(f"{host} déjà présent dans {hosts_file}")
PY
echo "Initialisation terminée. Personnalisez ${MAIN_FILE} puis éditez ${SECRETS_FILE} via SOPS."
