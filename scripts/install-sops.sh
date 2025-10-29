#!/usr/bin/env bash
set -euo pipefail

SOPS_VERSION="${SOPS_VERSION:-3.8.1}"
INSTALL_PREFIX="${1:-/usr/local/bin}"

if [[ ! -d "${INSTALL_PREFIX}" ]]; then
  echo "Install prefix ${INSTALL_PREFIX} does not exist" >&2
  exit 1
fi

if command -v sops >/dev/null 2>&1; then
  CURRENT_VERSION="$(sops --version | awk '{print $2}')"
  if [[ "${CURRENT_VERSION}" == "${SOPS_VERSION}" ]]; then
    echo "sops ${CURRENT_VERSION} already installed; nothing to do" >&2
    exit 0
  fi
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

BASENAME="sops-v${SOPS_VERSION}.linux.amd64"
ARCHIVE_PATH="${TMPDIR}/${BASENAME}"
CHECKSUMS_FILE="${TMPDIR}/sops-v${SOPS_VERSION}.checksums.txt"

curl -sSL "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/${BASENAME}" -o "${ARCHIVE_PATH}"
curl -sSL "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.checksums.txt" -o "${CHECKSUMS_FILE}"

grep "${BASENAME}" "${CHECKSUMS_FILE}" > "${TMPDIR}/checksum.txt"
(cd "${TMPDIR}" && sha256sum --check --status checksum.txt)

install -m 0755 "${ARCHIVE_PATH}" "${INSTALL_PREFIX}/sops"

echo "Installed sops ${SOPS_VERSION} to ${INSTALL_PREFIX}/sops"
