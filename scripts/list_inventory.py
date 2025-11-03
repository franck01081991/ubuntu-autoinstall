#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_ROOT = REPO_ROOT / "baremetal" / "inventory"
HOST_VARS_ROOT = INVENTORY_ROOT / "host_vars"


@dataclass(frozen=True)
class HostSummary:
    directory: str
    hostname: str | None
    install_disk: str | None
    encrypt_disk: bool
    network_method: str | None


def collect_host_summaries() -> list[HostSummary]:
    summaries: list[HostSummary] = []
    if not HOST_VARS_ROOT.exists():
        return summaries
    for entry in sorted(HOST_VARS_ROOT.iterdir(), key=lambda candidate: candidate.name):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        main_file = entry / "main.yml"
        if not main_file.is_file():
            continue
        data = yaml.safe_load(main_file.read_text(encoding="utf-8")) or {}
        summaries.append(
            HostSummary(
                directory=entry.name,
                hostname=data.get("hostname"),
                install_disk=data.get("install_disk"),
                encrypt_disk=bool(data.get("encrypt_disk", True)),
                network_method=(data.get("network") or {}).get("method"),
            )
        )
    return summaries


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
    header_line = " | ".join(header.ljust(width) for header, width in zip(headers, widths))
    separator = "-+-".join("-" * width for width in widths)
    body = [" | ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows]
    return "\n".join([header_line, separator, *body])


def display(value: str | None, fallback: str = "-") -> str:
    return value if value else fallback


def format_host(summary: HostSummary) -> Sequence[str]:
    return (
        summary.directory,
        display(summary.hostname),
        display(summary.install_disk, "auto"),
        "oui" if summary.encrypt_disk else "non",
        display(summary.network_method, "dhcp"),
    )


def print_hosts(summaries: Sequence[HostSummary]) -> None:
    print("Inventaire des hôtes")
    print("--------------------")
    if not summaries:
        print("Aucun hôte dans baremetal/inventory/host_vars/")
        return
    rows = [format_host(summary) for summary in summaries]
    print(render_table(("Dossier", "Hostname", "Disque", "Chiffré", "Réseau"), rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lister l'inventaire bare metal")
    parser.add_argument("command", choices=["hosts", "summary"], help="Type de rapport à afficher")
    parser.add_argument("--format", default="table", help="Format (non utilisé, compatibilité)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summaries = collect_host_summaries()
    if args.command == "hosts":
        print_hosts(summaries)
    else:
        print_hosts(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
