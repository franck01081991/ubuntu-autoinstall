#!/usr/bin/env python3
"""Onboard a new bare metal host inventory entry."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_ROOT = REPO_ROOT / "baremetal" / "inventory"
HOST_VARS_ROOT = INVENTORY_ROOT / "host_vars"
HOSTS_FILE = INVENTORY_ROOT / "hosts.yml"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover
        raise SystemExit(f"Invalid YAML in {path}: {exc}") from exc


def dump_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(
        "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def ensure_host_entry(host: str, disk: str | None, ssh_key: str | None) -> None:
    host_dir = HOST_VARS_ROOT / host
    host_dir.mkdir(parents=True, exist_ok=True)

    main_file = host_dir / "main.yml"
    main_data = load_yaml(main_file)

    main_data.setdefault("hostname", host)
    main_data.setdefault("encrypt_disk", True)

    if disk:
        main_data["install_disk"] = disk
    else:
        main_data.setdefault("install_disk", "")

    admin_user = main_data.get("admin_user", {})
    admin_user.setdefault("name", "admin")
    admin_user.setdefault("gecos", "ANSSI Admin")
    admin_user.setdefault("groups", ["sudo"])
    admin_user.setdefault("shell", "/bin/bash")
    main_data["admin_user"] = admin_user

    main_data.setdefault("network", {"method": "dhcp"})
    main_data.setdefault("network_interface", "eth0")

    keys = list(main_data.get("ssh_authorized_keys", []) or [])
    if ssh_key:
        if ssh_key not in keys:
            keys.append(ssh_key)
    main_data["ssh_authorized_keys"] = keys

    dump_yaml(main_file, main_data)

    secrets_file = host_dir / "secrets.sops.yaml"
    secrets_data = load_yaml(secrets_file)
    if "encrypt_disk_passphrase" not in secrets_data:
        secrets_data["encrypt_disk_passphrase"] = ""
    dump_yaml(secrets_file, secrets_data)

    hosts_data = load_yaml(HOSTS_FILE)
    if not hosts_data:
        hosts_data = {"all": {"children": {"baremetal": {"hosts": {}}}}}

    hosts_section = hosts_data.setdefault("all", {}).setdefault("children", {}).setdefault("baremetal", {}).setdefault("hosts", {})
    host_entry = hosts_section.setdefault(host, {})
    host_entry.setdefault("ansible_host", f"{host}")

    dump_yaml(HOSTS_FILE, hosts_data)

    print(f"Inventory for host '{host}' is ready under {host_dir.relative_to(REPO_ROOT)}")
    if disk:
        print(f"- install_disk: {disk}")
    else:
        print("- install_disk: auto (largest disk)")
    if ssh_key:
        print("- SSH key registered in host variables")
    print("Remember to encrypt secrets with: sops {}/secrets.sops.yaml".format(host_dir.relative_to(REPO_ROOT)))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update bare metal host inventory entries.")
    parser.add_argument("--host", required=True, help="Hostname to manage")
    parser.add_argument("--disk", help="Installation disk path (e.g. /dev/sda)")
    parser.add_argument("--ssh-key", help="SSH public key to authorize")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    ensure_host_entry(args.host, args.disk, args.ssh_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
