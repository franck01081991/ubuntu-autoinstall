#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from lib import inventory

ROOT = Path(__file__).resolve().parents[1]

def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def dump_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Create baremetal host skeleton")
    ap.add_argument("--host", required=True)
    ap.add_argument("--disk", default=None, help="e.g. /dev/nvme0n1 or /dev/sda")
    ap.add_argument("--ssh-key", default=None, help="ssh-ed25519 ...")
    args = ap.parse_args()

    overlay_root = inventory.get_overlay_root()
    hv_dir = overlay_root / "host_vars" / args.host
    hv_dir.mkdir(parents=True, exist_ok=True)

    # main.yml
    main_yml_path = hv_dir / "main.yml"
    main_yml = load_yaml(main_yml_path)
    main_yml.setdefault("hostname", args.host)
    main_yml.setdefault("encrypt_disk", True)
    if args.disk:
        main_yml["install_disk"] = args.disk
    if args.ssh_key:
        main_yml["ssh_authorized_keys"] = [args.ssh_key]
    dump_yaml(main_yml_path, main_yml)

    # secrets.sops.yaml placeholder (operator must encrypt with SOPS)
    secrets_path = hv_dir / "secrets.sops.yaml"
    if not secrets_path.exists():
        dump_yaml(
            secrets_path,
            {
                "encrypt_disk_passphrase": "",
                "_comment": "Encrypt this file with `sops --in-place` before committing artefacts.",
            },
        )

    # hosts.yml
    hosts_path = inventory.get_overlay_root() / "hosts.yml"
    hosts = load_yaml(hosts_path) or {}
    hosts.setdefault("all", {}).setdefault("hosts", {})
    if args.host not in hosts["all"]["hosts"]:
        hosts["all"]["hosts"][args.host] = {}
        dump_yaml(hosts_path, hosts)

    repo_rel = os.path.relpath(hv_dir, ROOT)
    print(f"✅ Host '{args.host}' initialized in {repo_rel}")
    print(f"   - Encrypt secrets: sops --in-place {secrets_path}")
    if args.ssh_key:
        print("   - SSH key set in main.yml")
    if not args.disk:
        print("   - No disk specified; template will auto-pick the largest disk.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
