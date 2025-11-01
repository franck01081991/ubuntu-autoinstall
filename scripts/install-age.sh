#!/usr/bin/env bash
set -euo pipefail

AGE_VERSION="${AGE_VERSION:-1.1.1}"
INSTALL_PREFIX="${1:-/usr/local/bin}"

if [[ ! -d "${INSTALL_PREFIX}" ]]; then
  echo "Install prefix ${INSTALL_PREFIX} does not exist" >&2
  exit 1
fi

if command -v age >/dev/null 2>&1; then
  CURRENT_VERSION="$(age --version 2>/dev/null | head -n1 | sed -E 's/.*([0-9]+\.[0-9]+\.[0-9]+).*/\1/')"
  if [[ -n "${CURRENT_VERSION}" && "${CURRENT_VERSION}" == "${AGE_VERSION}" ]]; then
    echo "age ${CURRENT_VERSION} already installed; nothing to do" >&2
    exit 0
  fi
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

ARCHIVE_NAME="age-v${AGE_VERSION}-linux-amd64.tar.gz"
ARCHIVE_PATH="${TMPDIR}/${ARCHIVE_NAME}"

case "${AGE_VERSION}" in
  1.1.1)
    ARCHIVE_SHA256="cf16cbb108fc56e2064b00ba2b65d9fb1b8d7002ca5e38260ee1cc34f6aaa8f9"
    ;;
  *)
    echo "No checksum defined for age ${AGE_VERSION}. Update scripts/install-age.sh." >&2
    exit 1
    ;;
esac

curl -sSL "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/${ARCHIVE_NAME}" -o "${ARCHIVE_PATH}"

DOWNLOADED_SHA256="$(sha256sum "${ARCHIVE_PATH}" | awk '{print $1}')"
if [[ "${DOWNLOADED_SHA256}" != "${ARCHIVE_SHA256}" ]]; then
  echo "Checksum mismatch for ${ARCHIVE_NAME}: expected ${ARCHIVE_SHA256}, got ${DOWNLOADED_SHA256}" >&2
  exit 1
fi

tar -xzf "${ARCHIVE_PATH}" -C "${TMPDIR}"

install -m 0755 "${TMPDIR}/age/age" "${INSTALL_PREFIX}/age"
install -m 0755 "${TMPDIR}/age/age-keygen" "${INSTALL_PREFIX}/age-keygen"

echo "Installed age ${AGE_VERSION} to ${INSTALL_PREFIX}" \
  "(binaries: age, age-keygen)"
