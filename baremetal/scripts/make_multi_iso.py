#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = REPO_ROOT / "baremetal" / "autoinstall" / "generated"
MULTI_ROOT = GENERATED_ROOT / "_multi"
DEFAULT_TMPDIR = REPO_ROOT / ".cache" / "tmp"


class IsoBuildError(RuntimeError):
    """Exception raised when the ISO build cannot proceed."""


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise IsoBuildError(f"Missing required binary: {name}")


def ensure_generated_host(host: str) -> Path:
    host_dir = GENERATED_ROOT / host
    user_data = host_dir / "user-data"
    meta_data = host_dir / "meta-data"
    if not user_data.is_file() or not meta_data.is_file():
        raise IsoBuildError(
            "Host '{host}' is missing NoCloud artefacts. "
            "Run `make baremetal/gen HOST={host}` first.".format(host=host)
        )
    return host_dir


def render_grub_config(hosts: Sequence[str], timeout: int, default_host: str | None, workdir: Path) -> Path:
    if timeout < 0:
        raise IsoBuildError("Timeout must be positive")
    entries: list[str] = []
    default_index = 0
    for index, host in enumerate(hosts):
        if default_host and host == default_host:
            default_index = index
        patch = f"autoinstall ds=nocloud;s=/cdrom/nocloud/{host}/"
        entries.append(
            "\n".join(
                (
                    f"menuentry 'Install: {host}' {{",
                    "    set gfxpayload=keep",
                    f"    linux   /casper/vmlinuz {patch} ---",
                    "    initrd  /casper/initrd",
                    "}",
                )
            )
        )
    header = [
        f"set default={default_index}",
        "set timeout_style=menu",
        f"set timeout={timeout}",
        "if [ $grub_platform = \"efi\" ]; then",
        "    insmod efi_gop",
        "    insmod efi_uga",
        "fi",
    ]
    content = "\n".join(header + entries) + "\n"
    grub_cfg = workdir / "grub.cfg"
    grub_cfg.write_text(content, encoding="utf-8")
    return grub_cfg


def build_iso(
    *,
    ubuntu_iso: Path,
    name: str,
    hosts: Sequence[str],
    timeout: int,
    default_host: str | None,
) -> Path:
    if not hosts:
        raise IsoBuildError("At least one host must be provided")
    require_binary("xorriso")
    tmp_base = Path(os.environ.get("TMPDIR", DEFAULT_TMPDIR))
    tmp_base.mkdir(parents=True, exist_ok=True)
    MULTI_ROOT.mkdir(parents=True, exist_ok=True)
    output_dir = MULTI_ROOT / name
    output_dir.mkdir(parents=True, exist_ok=True)
    for host in hosts:
        ensure_generated_host(host)
    if default_host and default_host not in hosts:
        raise IsoBuildError(f"Default host '{default_host}' is not part of the ISO host list")

    with tempfile.TemporaryDirectory(dir=tmp_base) as tmp:
        workdir = Path(tmp)
        nocloud_dir = workdir / "nocloud"
        nocloud_dir.mkdir(parents=True, exist_ok=True)
        for host in hosts:
            host_dir = GENERATED_ROOT / host
            target_dir = nocloud_dir / host
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(host_dir / "user-data", target_dir / "user-data")
            shutil.copy2(host_dir / "meta-data", target_dir / "meta-data")
        grub_cfg = render_grub_config(hosts, timeout, default_host, workdir)
        loopback_cfg = workdir / "loopback.cfg"
        loopback_cfg.write_text(grub_cfg.read_text(encoding="utf-8"), encoding="utf-8")

        iso_output = output_dir / f"ubuntu-autoinstall-{name}.iso"
        if iso_output.exists():
            iso_output.unlink()
        command = [
            "xorriso",
            "-indev",
            str(ubuntu_iso),
            "-outdev",
            str(iso_output),
            "-map",
            str(grub_cfg),
            "/boot/grub/grub.cfg",
            "-map",
            str(loopback_cfg),
            "/boot/grub/loopback.cfg",
            "-map",
            str(nocloud_dir),
            "/nocloud",
            "-boot_image",
            "any",
            "replay",
        ]
        subprocess.run(command, check=True)

    manifest = {
        "name": name,
        "hosts": list(hosts),
        "default_host": default_host,
        "ubuntu_iso": str(ubuntu_iso.resolve()),
        "created_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = output_dir / "SUMMARY.txt"
    summary.write_text(
        "\n".join(
            [
                f"Multi-host ISO '{name}'",
                f"Hosts: {', '.join(hosts)}",
                f"Default boot entry: {default_host or hosts[0]}",
                f"Ubuntu ISO source: {ubuntu_iso}",
                f"Generated at: {manifest['created_at']}",
                "",
                "Flash the ISO with `dd` or `ventoy` and choisissez l'entrée GRUB correspondant à l'hôte cible.",
            ]
        ),
        encoding="utf-8",
    )
    return iso_output


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble a multi-host Ubuntu autoinstall ISO")
    parser.add_argument("--ubuntu-iso", required=True, help="Path to the official Ubuntu live-server ISO")
    parser.add_argument("--name", required=True, help="Name of the generated ISO artefact")
    parser.add_argument("--host", dest="hosts", action="append", required=True, help="Host to include (repeatable)")
    parser.add_argument("--timeout", type=int, default=10, help="GRUB menu timeout in seconds")
    parser.add_argument("--default-host", help="Host selected by default in the GRUB menu")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    ubuntu_iso = Path(args.ubuntu_iso).expanduser()
    if not ubuntu_iso.is_file():
        raise SystemExit(f"Ubuntu ISO not found: {ubuntu_iso}")
    try:
        iso_path = build_iso(
            ubuntu_iso=ubuntu_iso,
            name=args.name,
            hosts=args.hosts,
            timeout=args.timeout,
            default_host=args.default_host,
        )
    except IsoBuildError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"xorriso failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    rel = os.path.relpath(iso_path, REPO_ROOT)
    print(f"Created {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
