#!/usr/bin/env python3
"""Run the hardware discovery playbook and cache results locally."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAYBOOK = REPO_ROOT / "baremetal" / "ansible" / "playbooks" / "discover_hardware.yml"
DEFAULT_INVENTORY = REPO_ROOT / "baremetal" / "inventory" / "hosts.yml"
DEFAULT_CACHE = REPO_ROOT / ".cache" / "discovery"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Collect remote hardware facts via Ansible and write JSON caches.",
    )
    parser.add_argument(
        "--inventory",
        default=DEFAULT_INVENTORY,
        type=Path,
        help="Path to the Ansible inventory file (default: baremetal/inventory/hosts.yml).",
    )
    parser.add_argument(
        "--limit",
        help="Optional Ansible --limit expression restricting targeted hosts.",
    )
    parser.add_argument(
        "--ansible-binary",
        default="ansible-playbook",
        help="Ansible playbook entrypoint to use (default: ansible-playbook).",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE,
        type=Path,
        help="Directory where discovery JSON payloads will be written (default: .cache/discovery).",
    )
    parser.add_argument(
        "--playbook",
        default=DEFAULT_PLAYBOOK,
        type=Path,
        help="Override the playbook path (default: baremetal/ansible/playbooks/discover_hardware.yml).",
    )
    parser.add_argument(
        "ansible_args",
        nargs=argparse.REMAINDER,
        help=(
            "Additional arguments passed to ansible-playbook. "
            "Use `--` before extra options so they are preserved."
        ),
    )
    return parser.parse_args(argv)


def build_command(args: argparse.Namespace) -> list[str]:
    """Return the ansible-playbook command to execute."""

    extra_vars = json.dumps({"discovery_output_dir": str(args.cache_dir)})
    command: list[str] = [
        args.ansible_binary,
        "-i",
        str(args.inventory),
        str(args.playbook),
        "--extra-vars",
        extra_vars,
    ]
    if args.limit:
        command.extend(["--limit", args.limit])
    if args.ansible_args:
        command.extend(args.ansible_args)
    return command


def main(argv: Sequence[str] | None = None) -> int:
    """Entry-point."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    cache_dir: Path = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    before = {path.name: path.stat().st_mtime_ns for path in cache_dir.glob("*.json")}
    command = build_command(args)

    result = subprocess.run(command, cwd=REPO_ROOT)
    if result.returncode != 0:
        return result.returncode

    after = {path.name: path.stat().st_mtime_ns for path in cache_dir.glob("*.json")}
    created = sorted(name for name in after if name not in before)
    updated = sorted(
        name for name, mtime in after.items() if name in before and before[name] != mtime
    )

    if created:
        print("Created discovery caches:")
        for name in created:
            print(f"  - {cache_dir / name}")
    if updated:
        print("Updated discovery caches:")
        for name in updated:
            print(f"  - {cache_dir / name}")
    if not created and not updated:
        print("Discovery cache already up-to-date.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
