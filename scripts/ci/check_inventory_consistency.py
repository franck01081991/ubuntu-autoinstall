#!/usr/bin/env python3
"""Validate bare-metal inventory coherence for automation flows."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY_ROOT = REPO_ROOT / "baremetal" / "inventory"


@dataclass
class HardwareProfile:
    """Structured view over a hardware profile entry."""

    name: str
    path: Path
    data: dict[str, Any]


@dataclass
class HostInventory:
    """Structured view over host variables."""

    name: str
    path: Path
    data: dict[str, Any]


def load_yaml(path: Path) -> dict[str, Any]:
    """Return YAML data from path, defaulting to an empty mapping."""

    try:
        with path.open(encoding="utf-8") as handle:
            content = yaml.safe_load(handle)
    except FileNotFoundError:
        return {}
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return content


def collect_hardware_profiles(root: Path) -> list[HardwareProfile]:
    """Load hardware profiles from the expected directory."""

    profiles: list[HardwareProfile] = []
    for candidate in sorted(root.glob("*.yml")):
        profiles.append(HardwareProfile(candidate.stem, candidate, load_yaml(candidate)))
    for candidate in sorted(root.glob("*.yaml")):
        if candidate.stem not in {profile.name for profile in profiles}:
            profiles.append(HardwareProfile(candidate.stem, candidate, load_yaml(candidate)))
    return profiles


def collect_host_vars(root: Path) -> list[HostInventory]:
    """Load host vars directories containing a main.yml file."""

    hosts: list[HostInventory] = []
    if not root.exists():
        return hosts
    for directory in sorted(root.iterdir(), key=lambda entry: entry.name):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        main_file = directory / "main.yml"
        if not main_file.is_file():
            continue
        hosts.append(HostInventory(directory.name, main_file, load_yaml(main_file)))
    return hosts


def ensure_fields_present(profile: HardwareProfile, errors: list[str]) -> None:
    """Validate required keys inside a hardware profile."""

    required_keys = ("hardware_model", "disk_device", "nic", "netmode")
    for key in required_keys:
        value = profile.data.get(key)
        if not value:
            errors.append(f"[{profile.path}] missing required key: {key}")

    specs = profile.data.get("hardware_specs")
    if not isinstance(specs, dict):
        errors.append(f"[{profile.path}] missing hardware_specs block")
        return

    cpu = specs.get("cpu")
    memory = specs.get("memory")
    cpu_required = ("model", "architecture", "cores", "threads", "turbo_mhz")
    mem_required = ("total_gb", "type", "speed_mhz")

    if not isinstance(cpu, dict):
        errors.append(f"[{profile.path}] missing hardware_specs.cpu map")
    else:
        for key in cpu_required:
            if key not in cpu or cpu.get(key) in (None, ""):
                errors.append(f"[{profile.path}] missing cpu.{key}")

    if not isinstance(memory, dict):
        errors.append(f"[{profile.path}] missing hardware_specs.memory map")
    else:
        for key in mem_required:
            if key not in memory or memory.get(key) in (None, ""):
                errors.append(f"[{profile.path}] missing memory.{key}")


def resolve_effective_value(host_value: Any, profile_value: Any) -> Any:
    """Return the effective value, preferring host-specific overrides."""

    return host_value if host_value not in (None, "") else profile_value


def validate_hosts(
    hosts: list[HostInventory],
    profiles: dict[str, HardwareProfile],
    errors: list[str],
) -> None:
    """Validate host variables consistency against hardware profiles."""

    for host in hosts:
        data = host.data
        hardware_profile_name = data.get("hardware_profile")
        if not hardware_profile_name:
            errors.append(f"[{host.path}] missing hardware_profile reference")
            continue
        profile = profiles.get(hardware_profile_name)
        if profile is None:
            errors.append(
                f"[{host.path}] references unknown hardware_profile: {hardware_profile_name}"
            )
            continue

        host_netmode = data.get("netmode")
        if not host_netmode:
            errors.append(f"[{host.path}] missing netmode value")
        else:
            profile_netmode = profile.data.get("netmode")
            if profile_netmode and host_netmode != profile_netmode:
                errors.append(
                    "[{path}] netmode '{host}' mismatches hardware profile '{profile}'".format(
                        path=host.path,
                        host=host_netmode,
                        profile=profile_netmode,
                    )
                )

        effective_disk = resolve_effective_value(data.get("disk_device"), profile.data.get("disk_device"))
        if not effective_disk:
            errors.append(f"[{host.path}] no disk_device defined in host or profile")

        effective_nic = resolve_effective_value(data.get("nic"), profile.data.get("nic"))
        if not effective_nic:
            errors.append(f"[{host.path}] no nic defined in host or profile")

        specs = profile.data.get("hardware_specs")
        if not specs:
            errors.append(
                f"[{profile.path}] referenced by {host.path} but missing hardware_specs block"
            )


def run_checks(inventory_root: Path) -> list[str]:
    """Execute inventory consistency checks and return any errors."""

    hardware_root = inventory_root / "profiles" / "hardware"
    host_vars_root = inventory_root / "host_vars"

    profiles = collect_hardware_profiles(hardware_root)
    profile_index = {profile.name: profile for profile in profiles}
    errors: list[str] = []

    for profile in profiles:
        ensure_fields_present(profile, errors)

    hosts = collect_host_vars(host_vars_root)
    validate_hosts(hosts, profile_index, errors)
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory-root",
        default=DEFAULT_INVENTORY_ROOT,
        type=Path,
        help="Path to the bare-metal inventory root (default: baremetal/inventory).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Program entrypoint."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    errors = run_checks(args.inventory_root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"Found {len(errors)} inventory consistency issue(s).", file=sys.stderr)
        return 1
    print("Inventory consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
