#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") --host <name> --profile <hardware_profile>

Initialise un hôte bare metal :
  - crée baremetal/inventory-local/host_vars/<name>/
  - génère main.yml pré-rempli
  - dépose un modèle de secrets à chiffrer via SOPS
  - ajoute l'hôte dans baremetal/inventory-local/hosts.yml
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
OVERLAY_ROOT="${AUTOINSTALL_LOCAL_DIR:-${REPO_ROOT}/baremetal/inventory-local}"
HOST_VARS_ROOT="${OVERLAY_ROOT}/host_vars"
EXAMPLE_TEMPLATE="${REPO_ROOT}/baremetal/inventory/examples/secrets.template.yaml"
HOST_DIR="${HOST_VARS_ROOT}/${HOST}"
MAIN_FILE="${HOST_DIR}/main.yml"
SECRETS_FILE="${HOST_DIR}/secrets.sops.yaml"
HOSTS_FILE="${OVERLAY_ROOT}/hosts.yml"

if [[ ! -f "${EXAMPLE_TEMPLATE}" ]]; then
  echo "Modèle de secrets introuvable: ${EXAMPLE_TEMPLATE}" >&2
  exit 1
fi

mkdir -p "${HOST_DIR}"
mkdir -p "${OVERLAY_ROOT}"

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
  TEMPLATE_TARGET="${SECRETS_FILE%.sops.yaml}.template.yaml"
  install -m 0600 "${EXAMPLE_TEMPLATE}" "${TEMPLATE_TARGET}"
  cat <<MSG
Modèle de secrets copié : ${TEMPLATE_TARGET}
Chiffrez-le avec : sops --encrypt --in-place ${TEMPLATE_TARGET}
Puis renommez le fichier chiffré en : ${SECRETS_FILE}
MSG
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
cat <<EOT
Initialisation terminée.
- Personnalisez ${MAIN_FILE}
- Chiffrez le modèle de secrets généré puis renommez-le en ${SECRETS_FILE}
- Les fichiers sont stockés hors Git dans ${OVERLAY_ROOT}
EOT
