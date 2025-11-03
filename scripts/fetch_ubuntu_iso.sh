#!/usr/bin/env bash
set -euo pipefail
REL="${1:-24.04.3}"
ARCH="${2:-amd64}"
BASE="https://releases.ubuntu.com/${REL}"
ISO="ubuntu-${REL}-live-server-${ARCH}.iso"

mkdir -p .cache/iso && cd .cache/iso

echo "[*] Download SHA256SUMS (+ .gpg) from ${BASE}"
curl -fsSLO "${BASE}/SHA256SUMS"
curl -fsSLO "${BASE}/SHA256SUMS.gpg"

echo "[*] Import Ubuntu CD Image signing key (2012)"
# FPR: 8439 38DF 228D 22F7 B374 2BC0 D94A A3F0 EFE2 1092
gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys D94AA3F0EFE21092

echo "[*] Verify signature of SHA256SUMS"
gpg --verify SHA256SUMS.gpg SHA256SUMS

echo "[*] Download ISO ${ISO}"
curl -fsSLO "${BASE}/${ISO}"

echo "[*] Check ISO SHA256"
grep " ${ISO}$" SHA256SUMS | sha256sum -c -

echo "[+] ISO OK: .cache/iso/${ISO}"
