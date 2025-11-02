#!/usr/bin/env python3
"""Select bare metal validation targets based on changed files."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]


def git_diff(base: str | None) -> list[str]:
    """Return the list of changed files between ``base`` and ``HEAD``."""
    diff_range: list[str]
    if base:
        diff_range = [f"{base}..HEAD"]
    else:
        diff_range = ["HEAD"]
    result = subprocess.run(
        ["git", "diff", "--name-only", *diff_range],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def list_hardware_targets(directory: Path) -> list[str]:
    suffixes = ("*.yml", "*.yaml")
    targets = {
        profile.stem
        for suffix in suffixes
        for profile in directory.glob(suffix)
        if profile.is_file()
    }
    return sorted(targets)


def list_host_targets(directory: Path) -> list[str]:
    hosts: list[str] = []
    for candidate in directory.iterdir():
        if candidate.is_dir() and (candidate / "main.yml").exists():
            hosts.append(candidate.name)
    return sorted(hosts)


def write_output(name: str, value: str) -> None:
    escaped = value.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise SystemExit("GITHUB_OUTPUT is not defined")
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={escaped}\n")


def append_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(f"{text}\n")


def determine_targets(changed_files: Iterable[str]) -> tuple[list[dict[str, str]], str]:
    hardware_dir = REPO_ROOT / "baremetal" / "inventory" / "profiles" / "hardware"
    host_dir = REPO_ROOT / "baremetal" / "inventory" / "host_vars"

    hardware_targets = list_hardware_targets(hardware_dir)
    host_targets = list_host_targets(host_dir)

    hardware_map = {
        str(Path("baremetal/inventory/profiles/hardware") / f"{name}{suffix}"):
            name
        for name in hardware_targets
        for suffix in (".yml", ".yaml")
        if (hardware_dir / f"{name}{suffix}").is_file()
    }
    host_map = {}
    for name in host_targets:
        host_map[f"baremetal/inventory/host_vars/{name}/main.yml"] = name
        host_map[f"baremetal/inventory/host_vars/{name}/secrets.sops.yaml"] = name

    always_all_prefixes = (
        "ansible/",
        "baremetal/ansible/",
        "baremetal/autoinstall/templates/",
        "baremetal/scripts/",
    )
    always_all_files = {
        "Makefile",
        "scripts/install-sops.sh",
        "scripts/install-age.sh",
        "baremetal/inventory/hosts.yml",
        ".github/workflows/build-iso.yml",
    }

    reasons: list[str] = []

    for path in changed_files:
        if path in always_all_files or any(path.startswith(prefix) for prefix in always_all_prefixes):
            reasons.append(f"Modification globale détectée ({path}) → validation complète")
            return (
                [{"scope": "hardware", "target": target} for target in hardware_targets]
                + [{"scope": "host", "target": target} for target in host_targets],
                "\n".join(reasons),
            )

    touched_hardware: set[str] = set()
    touched_hosts: set[str] = set()

    for path in changed_files:
        if path in hardware_map:
            touched_hardware.add(hardware_map[path])
        elif path.startswith("baremetal/inventory/profiles/hardware/"):
            if Path(path).suffix in {".yml", ".yaml"}:
                touched_hardware.add(Path(path).stem)
        elif path in host_map:
            touched_hosts.add(host_map[path])
        elif path.startswith("baremetal/inventory/host_vars/"):
            parts = Path(path).parts
            try:
                host_index = parts.index("host_vars") + 1
                host_name = parts[host_index]
                touched_hosts.add(host_name)
            except ValueError:
                continue
        elif path.startswith("baremetal/inventory/profiles/"):
            reasons.append(f"Changement inventaire partagé ({path}) → validation complète")
            return (
                [{"scope": "hardware", "target": target} for target in hardware_targets]
                + [{"scope": "host", "target": target} for target in host_targets],
                "\n".join(reasons),
            )

    matrix: list[dict[str, str]] = []
    if touched_hardware:
        matrix.extend({"scope": "hardware", "target": target} for target in sorted(touched_hardware))
    if touched_hosts:
        matrix.extend({"scope": "host", "target": target} for target in sorted(touched_hosts))

    if matrix:
        if touched_hardware:
            reasons.append(
                "Profils matériels ciblés : " + ", ".join(sorted(touched_hardware))
            )
        if touched_hosts:
            reasons.append("Hôtes ciblés : " + ", ".join(sorted(touched_hosts)))
    else:
        reasons.append("Aucun profil/hôte spécifique détecté → validation complète par défaut")
        matrix = (
            [{"scope": "hardware", "target": target} for target in hardware_targets]
            + [{"scope": "host", "target": target} for target in host_targets]
        )

    return matrix, "\n".join(reasons)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select bare metal validation targets")
    parser.add_argument("--base", help="Base commit/refs to compare against", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = args.base or ""

    changed_files = git_diff(base)
    matrix, reason = determine_targets(changed_files)

    write_output("matrix", json.dumps(matrix, separators=(",", ":")))
    write_output("has_targets", "true" if matrix else "false")
    write_output("reason", reason)
    append_summary(f"### Validation bare metal\n{reason}")


if __name__ == "__main__":
    main()
