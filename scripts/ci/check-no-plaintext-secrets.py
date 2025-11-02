#!/usr/bin/env python3
"""Fail the build if inventory files contain secrets in plaintext."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_ROOTS = [ROOT / "baremetal" / "inventory"]

FORBIDDEN_SUBSTRINGS = {
    "password_hash": "password_hash must be stored in a SOPS-encrypted file",
    "ssh_authorized_keys": "ssh_authorized_keys must be stored in SOPS secrets",
    "ssh-ed25519": "SSH public keys must be encrypted via SOPS",
    "ssh-rsa": "SSH public keys must be encrypted via SOPS",
}


def scan_file(path: Path) -> list[str]:
    """Return a list of human readable violations for ``path``."""
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        for substring, message in FORBIDDEN_SUBSTRINGS.items():
            if substring in line:
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_no}: {message}"
                )
    return violations


def main() -> int:
    violations: list[str] = []

    for inventory_root in INVENTORY_ROOTS:
        if not inventory_root.exists():
            continue

        for path in inventory_root.rglob("*.yml"):
            if path.name.endswith(".sops.yml") or path.name.endswith(".sops.yaml"):
                continue
            if ".sops." in path.name:
                continue
            violations.extend(scan_file(path))

        for path in inventory_root.rglob("*.yaml"):
            if path.name.endswith(".sops.yml") or path.name.endswith(".sops.yaml"):
                continue
            if ".sops." in path.name:
                continue
            violations.extend(scan_file(path))

    if violations:
        print("Found plaintext secrets in inventory files:", file=sys.stderr)
        for violation in sorted(set(violations)):
            print(f"  - {violation}", file=sys.stderr)
        print(
            "Move the offending values to secrets.sops.yaml and re-encrypt with SOPS.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
