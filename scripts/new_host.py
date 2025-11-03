#!/usr/bin/env python3
import argparse, os, sys, yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def dump_yaml(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

def main():
    ap = argparse.ArgumentParser(description="Create baremetal host skeleton")
    ap.add_argument("--host", required=True)
    ap.add_argument("--disk", default=None, help="e.g. /dev/nvme0n1 or /dev/sda")
    ap.add_argument("--ssh-key", default=None, help="ssh-ed25519 ...")
    args = ap.parse_args()

    hv_dir = os.path.join(ROOT, "baremetal", "inventory", "host_vars", args.host)
    os.makedirs(hv_dir, exist_ok=True)

    # main.yml
    main_yml_path = os.path.join(hv_dir, "main.yml")
    main_yml = load_yaml(main_yml_path)
    main_yml.setdefault("hostname", args.host)
    main_yml.setdefault("encrypt_disk", True)
    if args.disk:
        main_yml["install_disk"] = args.disk
    if args.ssh_key:
        main_yml["ssh_authorized_keys"] = [args.ssh_key]
    dump_yaml(main_yml_path, main_yml)

    # secrets.sops.yaml (plaintext placeholder; you will encrypt with sops)
    secrets_path = os.path.join(hv_dir, "secrets.sops.yaml")
    if not os.path.exists(secrets_path):
        dump_yaml(secrets_path, {"encrypt_disk_passphrase": ""})

    # hosts.yml
    hosts_path = os.path.join(ROOT, "baremetal", "inventory", "hosts.yml")
    hosts = load_yaml(hosts_path) or {}
    hosts.setdefault("all", {}).setdefault("hosts", {})
    if args.host not in hosts["all"]["hosts"]:
        hosts["all"]["hosts"][args.host] = {}
        dump_yaml(hosts_path, hosts)

    print(f"✅ Host '{args.host}' initialized in {hv_dir}")
    print(f"   - Edit LUKS passphrase: sops {secrets_path} (set encrypt_disk_passphrase)")
    if args.ssh_key:
        print("   - SSH key set in main.yml")
    if not args.disk:
        print("   - No disk specified; template will auto-pick the largest disk.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
