#!/usr/bin/env python3
"""Interactive helper to generate Ubuntu Autoinstall ISO images.

The wizard guides the operator through the necessary `make` targets to render
an Autoinstall configuration and assemble either the seed ISO (CIDATA), the
full ISO, or both. All commands remain idempotent and rely on existing
Makefile targets so that the CI/CD pipeline can replay the same operations.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_VARS_DIR = REPO_ROOT / "baremetal" / "inventory" / "host_vars"
GENERATED_DIR = REPO_ROOT / "baremetal" / "autoinstall" / "generated"
DEFAULT_UBUNTU_ISO = "ubuntu-24.04-live-server-amd64.iso"


@dataclass(frozen=True)
class IsoAction:
    """Describe the ISO artefacts that should be produced."""

    label: str
    requires_ubuntu_iso: bool
    make_targets: Sequence[str]


ISO_ACTIONS: List[IsoAction] = [
    IsoAction(
        label="1. Seed ISO (CIDATA)",
        requires_ubuntu_iso=False,
        make_targets=("baremetal/seed",),
    ),
    IsoAction(
        label="2. Full ISO (autonomous)",
        requires_ubuntu_iso=True,
        make_targets=("baremetal/fulliso",),
    ),
    IsoAction(
        label="3. Seed + Full ISO", 
        requires_ubuntu_iso=True,
        make_targets=("baremetal/seed", "baremetal/fulliso"),
    ),
]


def list_hosts() -> List[str]:
    """Return the list of host directories declared in the inventory."""

    if not HOST_VARS_DIR.exists():
        print(f"Inventaire introuvable : {HOST_VARS_DIR}", file=sys.stderr)
        sys.exit(1)

    hosts = [
        entry.name
        for entry in HOST_VARS_DIR.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    hosts.sort()
    return hosts


def prompt_choice(options: Sequence[str], prompt: str) -> int:
    """Display a numeric menu and return the selected index."""

    while True:
        print(prompt)
        for idx, option in enumerate(options, start=1):
            print(f"  {idx}. {option}")
        raw = input("Sélectionnez une option : ").strip()
        if not raw.isdigit():
            print("Veuillez entrer un numéro valide.\n")
            continue
        idx = int(raw)
        if 1 <= idx <= len(options):
            return idx - 1
        print("Choix hors limites, recommencez.\n")


def prompt_host(hosts: Sequence[str]) -> str:
    if not hosts:
        print(
            "Aucun hôte n'est défini. Utilisez `make baremetal/host-init` avant de lancer le wizard.",
            file=sys.stderr,
        )
        sys.exit(1)
    idx = prompt_choice(hosts, "Hôtes disponibles :")
    return hosts[idx]


def prompt_iso_action() -> IsoAction:
    idx = prompt_choice([action.label for action in ISO_ACTIONS], "Quel type d'image générer ?")
    return ISO_ACTIONS[idx]


def prompt_iso_path(default: str) -> str:
    while True:
        candidate = input(f"Chemin vers l'ISO Ubuntu officielle [{default}] : ").strip()
        if not candidate:
            candidate = default
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path)
        print(f"ISO introuvable à l'emplacement : {path}\n")


def run_make(target: str, host: str, ubuntu_iso: str | None) -> None:
    env = os.environ.copy()
    env.setdefault("HOST", host)
    env.setdefault("PROFILE", "")
    command: List[str] = ["make", target, f"HOST={host}"]
    if target == "baremetal/fulliso" and ubuntu_iso:
        command.append(f"UBUNTU_ISO={ubuntu_iso}")
    print("\n▶", " ".join(command))
    subprocess.run(command, check=True, env=env, cwd=str(REPO_ROOT))


def summarize_outputs(host: str) -> None:
    host_dir = GENERATED_DIR / host
    if not host_dir.exists():
        print(
            f"⚠️ Aucun artefact trouvé dans {host_dir}. Vérifiez les commandes exécutées.",
            file=sys.stderr,
        )
        return
    artefacts = sorted(host_dir.glob("*.iso"))
    if not artefacts:
        print(
            f"⚠️ Aucun fichier ISO généré sous {host_dir}.",
            file=sys.stderr,
        )
        return
    print("\nISO générées :")
    for artefact in artefacts:
        print(f"  - {artefact.relative_to(REPO_ROOT)}")


def main() -> None:
    print("Ubuntu Autoinstall – Assistant de génération d'ISO")
    print("================================================\n")

    hosts = list_hosts()
    host = prompt_host(hosts)
    print(f"\nHôte sélectionné : {host}\n")

    action = prompt_iso_action()
    ubuntu_iso: str | None = None
    if action.requires_ubuntu_iso:
        ubuntu_iso = prompt_iso_path(os.environ.get("UBUNTU_ISO", DEFAULT_UBUNTU_ISO))

    print("\nRésumé :")
    print(f"  - Hôte : {host}")
    print(f"  - Artefacts : {action.label.split('.', 1)[-1].strip()}")
    if ubuntu_iso:
        print(f"  - ISO Ubuntu source : {ubuntu_iso}")

    confirmation = input("\nConfirmer et lancer la génération ? [o/N] : ").strip().lower()
    if confirmation not in {"o", "oui", "y", "yes"}:
        print("Opération annulée.")
        return

    try:
        for target in action.make_targets:
            run_make(target, host=host, ubuntu_iso=ubuntu_iso)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        sys.exit(exc.returncode or 1)

    summarize_outputs(host)


if __name__ == "__main__":
    main()
