#!/usr/bin/env python3
"""Summarise Git-tracked bare-metal inventory for technicians."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from lib import inventory


@dataclass(frozen=True)
class HostSummary:
    """Minimal host metadata rendered from host_vars."""

    directory: str
    hostname: str | None
    hardware_profile: str | None
    netmode: str | None


@dataclass(frozen=True)
class HardwareSummary:
    """Minimal hardware profile metadata."""

    name: str
    hardware_model: str | None
    storage_profile: str | None
    netmode: str | None
    nic: str | None
    disk_device: str | None


def parse_simple_keys(path: Path, keys: Iterable[str]) -> dict[str, str]:
    """Extract first-level scalar keys from a YAML file without external deps."""

    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        if ":" not in stripped:
            continue
        key, remainder = stripped.split(":", 1)
        key = key.strip()
        if key not in keys or key in values:
            continue
        value = remainder.split("#", 1)[0].strip()
        if not value:
            continue
        if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        values[key] = value
    return values


def collect_host_summaries() -> list[HostSummary]:
    """Return sorted host summaries discovered under host_vars/."""

    summaries: dict[str, HostSummary] = {}
    for root in inventory.iter_inventory_roots():
        host_root = root / "host_vars"
        if not host_root.exists():
            continue
        for entry in sorted(host_root.iterdir(), key=lambda candidate: candidate.name):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            main_file = entry / "main.yml"
            if not main_file.is_file():
                continue
            data = parse_simple_keys(main_file, ("hostname", "hardware_profile", "netmode"))
            summaries.setdefault(
                entry.name,
                HostSummary(
                    directory=entry.name,
                    hostname=data.get("hostname"),
                    hardware_profile=data.get("hardware_profile"),
                    netmode=data.get("netmode"),
                ),
            )
    return [summaries[name] for name in sorted(summaries)]


def collect_hardware_summaries() -> list[HardwareSummary]:
    """Return sorted hardware summaries discovered under profiles/hardware/."""

    files: dict[str, Path] = {}
    for root in inventory.hardware_profiles_roots():
        if not root.exists():
            continue
        for candidate in root.iterdir():
            if candidate.is_file() and candidate.suffix in {".yml", ".yaml"}:
                files.setdefault(candidate.stem, candidate)
    summaries: list[HardwareSummary] = []
    for name in sorted(files):
        data = parse_simple_keys(
            files[name],
            ("hardware_model", "storage_profile", "netmode", "nic", "disk_device"),
        )
        summaries.append(
            HardwareSummary(
                name=name,
                hardware_model=data.get("hardware_model"),
                storage_profile=data.get("storage_profile"),
                netmode=data.get("netmode"),
                nic=data.get("nic"),
                disk_device=data.get("disk_device"),
            )
        )
    return summaries


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render a simple ASCII table."""

    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
    header_line = " | ".join(header.ljust(width) for header, width in zip(headers, widths))
    separator = "-+-".join("-" * width for width in widths)
    body = [" | ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows]
    return "\n".join([header_line, separator, *body])


def display(value: str | None) -> str:
    """Return a printable value for optional fields."""

    return value if value else "-"


def print_hardware_section(profiles: Sequence[HardwareSummary]) -> None:
    """Print the hardware profile section."""

    print("Profils matériels disponibles")
    print("-----------------------------")
    if not profiles:
        print("Aucun profil matériel détecté dans baremetal/inventory/profiles/hardware/.")
        return
    rows = [
        (
            profile.name,
            display(profile.hardware_model),
            display(profile.storage_profile),
            display(profile.netmode),
            display(profile.nic),
            display(profile.disk_device),
        )
        for profile in profiles
    ]
    print(
        render_table(
            ("Profil", "Modèle", "Stockage", "Netmode", "NIC", "Disque principal"),
            rows,
        )
    )


def print_hosts_section(hosts: Sequence[HostSummary]) -> None:
    """Print the host section."""

    print("Hôtes déclarés")
    print("--------------")
    if not hosts:
        print("Aucun hôte déclaré. Utilisez `make baremetal/host-init` puis recommencez.")
        return
    rows = [
        (
            host.directory,
            display(host.hostname),
            display(host.hardware_profile),
            display(host.netmode),
        )
        for host in hosts
    ]
    print(
        render_table(
            ("Répertoire", "Hostname", "Profil matériel", "Netmode"),
            rows,
        )
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Lister l'inventaire bare metal versionné (hôtes, profils matériels)."
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Format de sortie (table par défaut).",
    )
    parser.add_argument(
        "mode",
        choices=("summary", "hosts", "profiles"),
        nargs="?",
        default="summary",
        help="Vue à afficher (summary par défaut).",
    )
    return parser.parse_args()


def main() -> None:
    """Entrypoint."""

    args = parse_args()
    if args.mode in {"summary", "profiles"}:
        profiles = collect_hardware_summaries()
    else:
        profiles = []
    if args.mode in {"summary", "hosts"}:
        hosts = collect_host_summaries()
    else:
        hosts = []

    if args.format == "json":
        payload: dict[str, list[dict[str, str | None]]] = {}
        if args.mode in {"summary", "profiles"}:
            payload["hardware_profiles"] = [asdict(profile) for profile in profiles]
        if args.mode in {"summary", "hosts"}:
            payload["hosts"] = [asdict(host) for host in hosts]
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    if args.mode == "summary":
        print_hardware_section(profiles)
        print()
        print_hosts_section(hosts)
    elif args.mode == "hosts":
        print_hosts_section(hosts)
    else:
        print_hardware_section(profiles)


if __name__ == "__main__":
    main()
