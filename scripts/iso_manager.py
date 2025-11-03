#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

from lib import inventory

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_make(target: str, *, variables: dict[str, str] | None = None) -> None:
    command = ["make", target]
    if variables:
        for key, value in variables.items():
            command.append(f"{key}={value}")
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def ensure_hosts_exist(hosts: Iterable[str]) -> None:
    missing = [host for host in hosts if inventory.first_existing(inventory.host_vars_candidates(host)) is None]
    if missing:
        raise SystemExit(
            "Les hôtes suivants n'ont pas été initialisés dans l'inventaire local : "
            + ", ".join(sorted(missing))
        )


def cmd_render(args: argparse.Namespace) -> None:
    ensure_hosts_exist(args.hosts)
    for host in args.hosts:
        run_make("baremetal/gen", variables={"HOST": host})


def cmd_seed(args: argparse.Namespace) -> None:
    ensure_hosts_exist([args.host])
    run_make("baremetal/seed", variables={"HOST": args.host})


def cmd_full(args: argparse.Namespace) -> None:
    ensure_hosts_exist([args.host])
    variables = {"HOST": args.host, "UBUNTU_ISO": args.ubuntu_iso}
    run_make("baremetal/fulliso", variables=variables)


def cmd_multi(args: argparse.Namespace) -> None:
    ensure_hosts_exist(args.hosts)
    if args.render:
        for host in args.hosts:
            run_make("baremetal/gen", variables={"HOST": host})
    variables = {
        "HOSTS": " ".join(args.hosts),
        "UBUNTU_ISO": args.ubuntu_iso,
        "NAME": args.name,
        "GRUB_TIMEOUT": str(args.timeout),
    }
    if args.default_host:
        variables["DEFAULT_HOST"] = args.default_host
    run_make("baremetal/multiiso", variables=variables)


def cmd_list_hosts(_: argparse.Namespace) -> None:
    for host in list_hosts():
        print(host)


def list_hosts() -> list[str]:
    discovered: set[str] = set()
    for root in inventory.iter_inventory_roots():
        host_root = root / "host_vars"
        if not host_root.exists():
            continue
        for entry in host_root.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if any((entry / candidate).is_file() for candidate in ("main.yml", "main.yaml")):
                discovered.add(entry.name)
    return sorted(discovered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automation CLI for Ubuntu autoinstall ISO workflows")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render", help="Rendre user-data/meta-data pour un ou plusieurs hôtes")
    render.add_argument("--host", dest="hosts", action="append", required=True, help="Nom d'hôte à rendre (option répétable)")
    render.set_defaults(func=cmd_render)

    seed = subparsers.add_parser("seed", help="Construire une ISO seed (CIDATA) pour un hôte")
    seed.add_argument("--host", required=True, help="Nom d'hôte")
    seed.set_defaults(func=cmd_seed)

    full = subparsers.add_parser("full", help="Construire une ISO complète pour un hôte")
    full.add_argument("--host", required=True, help="Nom d'hôte")
    full.add_argument("--ubuntu-iso", required=True, help="Chemin vers l'ISO Ubuntu officielle")
    full.set_defaults(func=cmd_full)

    multi = subparsers.add_parser("multi", help="Construire une ISO multi-hôtes avec menu GRUB")
    multi.add_argument("--host", dest="hosts", action="append", required=True, help="Hôte à inclure (option répétable)")
    multi.add_argument("--ubuntu-iso", required=True, help="Chemin vers l'ISO Ubuntu officielle")
    multi.add_argument("--name", required=True, help="Nom de l'artefact multi-hôtes")
    multi.add_argument("--default-host", help="Entrée GRUB sélectionnée par défaut")
    multi.add_argument("--timeout", type=int, default=10, help="Timeout du menu GRUB (secondes)")
    multi.add_argument("--render", action="store_true", help="Rendre user-data/meta-data avant la construction")
    multi.set_defaults(func=cmd_multi)

    subparsers.add_parser("list-hosts", help="Lister les hôtes disponibles").set_defaults(func=cmd_list_hosts)

    return parser


def main(argv: Sequence[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "list-hosts" and "hosts" in args.__dict__:
        args.hosts = [host for host in args.hosts if host]
        if not args.hosts:
            raise SystemExit("Aucun hôte fourni")
    try:
        args.func(args)
    except subprocess.CalledProcessError as exc:
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
