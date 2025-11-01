#!/usr/bin/env python3
"""Interactive helper to generate Ubuntu Autoinstall ISO images.

The wizard guides the operator through the necessary `make` targets to render
an Autoinstall configuration and assemble either the seed ISO (CIDATA), the
full ISO, or both. All commands remain idempotent and rely on existing
Makefile targets so that the CI/CD pipeline can replay the same operations.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_VARS_DIR = REPO_ROOT / "baremetal" / "inventory" / "host_vars"
HARDWARE_PROFILE_DIR = REPO_ROOT / "baremetal" / "inventory" / "profiles" / "hardware"
GENERATED_DIR = REPO_ROOT / "baremetal" / "autoinstall" / "generated"
DEFAULT_UBUNTU_ISO = "ubuntu-24.04-live-server-amd64.iso"
DEFAULT_AGE_KEY_FILE = Path.home() / ".config" / "sops" / "age" / "keys.txt"
SOPS_INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install-sops.sh"


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


def check_required_binaries(binaries: Sequence[str]) -> None:
    missing = [binary for binary in binaries if shutil.which(binary) is None]
    if not missing:
        return
    formatted = ", ".join(missing)
    print(
        "Les binaires requis suivants sont introuvables dans le PATH : "
        f"{formatted}. Installez-les avant de continuer.",
        file=sys.stderr,
    )
    sys.exit(1)


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


def list_hardware_profiles() -> List[str]:
    """Return available hardware profiles defined in the inventory."""

    if not HARDWARE_PROFILE_DIR.exists():
        return []

    profiles = [
        entry.stem
        for entry in HARDWARE_PROFILE_DIR.iterdir()
        if entry.is_file()
        and entry.suffix.lower() in {".yml", ".yaml"}
        and not entry.name.startswith(".")
    ]
    profiles.sort()
    return profiles


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


def prompt_new_host_name() -> str:
    pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
    while True:
        name = input("Nom d'hôte (alphanumérique, ._- autorisés) : ").strip()
        if not name:
            print("Le nom d'hôte est obligatoire.\n")
            continue
        if not pattern.match(name):
            print("Nom invalide. Utilisez uniquement lettres, chiffres, points, tirets, underscores.\n")
            continue
        return name


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


def prompt_age_key_file(default: Path) -> Path:
    while True:
        candidate = input(f"Chemin de la clé age pour SOPS [{default}] : ").strip()
        if not candidate:
            candidate = str(default)
        path = Path(candidate).expanduser()
        if path.is_file():
            return path
        print(f"Fichier de clé age introuvable : {path}\n")


def prepare_sops_environment(env: Dict[str, str]) -> Dict[str, str]:
    if env.get("SOPS_AGE_KEY"):
        return {}

    existing_file = env.get("SOPS_AGE_KEY_FILE")
    if existing_file:
        path = Path(existing_file).expanduser()
        if path.is_file():
            return {"SOPS_AGE_KEY_FILE": str(path)}
        print(
            f"Le fichier spécifié dans SOPS_AGE_KEY_FILE est introuvable : {path}",
            file=sys.stderr,
        )

    default_path = DEFAULT_AGE_KEY_FILE
    if default_path.is_file():
        confirmed = input(
            f"Utiliser la clé age par défaut située dans {default_path}? [O/n] : "
        ).strip().lower()
        if confirmed in {"", "o", "oui", "y", "yes"}:
            return {"SOPS_AGE_KEY_FILE": str(default_path)}

    path = prompt_age_key_file(default_path)
    return {"SOPS_AGE_KEY_FILE": str(path)}


def run_command(
    command: Sequence[str], *, env: Dict[str, str] | None = None, cwd: Path | None = None
) -> None:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    print("\n▶", " ".join(command))
    subprocess.run(command, check=True, env=effective_env, cwd=str(cwd or REPO_ROOT))


def run_make(target: str, *, variables: Dict[str, str] | None, sops_env: Dict[str, str]) -> None:
    command: List[str] = ["make", target]
    if variables:
        for key, value in variables.items():
            command.append(f"{key}={value}")
    run_command(command, env=sops_env)


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


def handle_repository_update() -> None:
    print("\nMise à jour du dépôt Git")
    print("------------------------")
    confirmation = input(
        "Lancer `git fetch --all --prune` puis `git pull --ff-only` ? [o/N] : "
    ).strip().lower()
    if confirmation not in {"o", "oui", "y", "yes"}:
        print("Opération annulée.")
        return
    try:
        run_command(["git", "fetch", "--all", "--prune"])
        run_command(["git", "pull", "--ff-only"])
        run_command(["git", "status", "--short", "--branch"])
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        sys.exit(exc.returncode or 1)


def handle_environment_update(sops_env: Dict[str, str]) -> None:
    print("\nMise à jour de l'environnement local")
    print("----------------------------------")
    if shutil.which("sops") is None and SOPS_INSTALL_SCRIPT.is_file():
        install = input(
            "Le binaire sops est introuvable. Lancer scripts/install-sops.sh ? [O/n] : "
        ).strip().lower()
        if install in {"", "o", "oui", "y", "yes"}:
            try:
                run_command(["bash", str(SOPS_INSTALL_SCRIPT)], env=sops_env)
            except subprocess.CalledProcessError as exc:
                print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
                sys.exit(exc.returncode or 1)
    try:
        run_command(["make", "doctor"], env=sops_env)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        sys.exit(exc.returncode or 1)
    print(
        "\nVérification terminée. Consultez les messages ci-dessus pour connaître les dépendances à installer."
    )


def handle_host_initialization(sops_env: Dict[str, str]) -> None:
    print("\nInitialisation d'un hôte bare metal")
    print("-----------------------------------")
    host = prompt_new_host_name()

    existing_path = HOST_VARS_DIR / host
    if existing_path.exists():
        confirm = input(
            f"Le répertoire {existing_path} existe déjà. Relancer l'initialisation ? [o/N] : "
        ).strip().lower()
        if confirm not in {"o", "oui", "y", "yes"}:
            print("Opération annulée.")
            return

    profiles = list_hardware_profiles()
    profile: str | None = None
    if profiles:
        profile_idx = prompt_choice(profiles, "Profils matériels disponibles :")
        profile = profiles[profile_idx]
    else:
        print(
            "⚠️ Aucun profil matériel détecté. La cible Make utilisera la valeur par défaut si disponible.",
            file=sys.stderr,
        )

    variables = {"HOST": host}
    if profile:
        variables["PROFILE"] = profile

    try:
        run_make("baremetal/host-init", variables=variables, sops_env=sops_env)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        sys.exit(exc.returncode or 1)

    print(
        "\nHôte initialisé. Vous pouvez maintenant personnaliser les fichiers dans "
        f"baremetal/inventory/host_vars/{host}/ puis relancer la génération d'ISO."
    )


def handle_iso_generation(sops_env: Dict[str, str]) -> None:
    hosts = list_hosts()
    if not hosts:
        print(
            "Aucun hôte disponible. Initialisez-en un avant de générer des ISO.",
            file=sys.stderr,
        )
        create = input("Souhaitez-vous créer un nouvel hôte maintenant ? [O/n] : ").strip().lower()
        if create in {"", "o", "oui", "y", "yes"}:
            handle_host_initialization(sops_env)
            hosts = list_hosts()
        if not hosts:
            return

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
    if sops_env.get("SOPS_AGE_KEY_FILE"):
        print(f"  - Clé age : {sops_env['SOPS_AGE_KEY_FILE']}")
    if os.environ.get("SOPS_AGE_KEY"):
        print("  - Clé age fournie via SOPS_AGE_KEY (variable en mémoire)")

    confirmation = input("\nConfirmer et lancer la génération ? [o/N] : ").strip().lower()
    if confirmation not in {"o", "oui", "y", "yes"}:
        print("Opération annulée.")
        return

    try:
        for target in action.make_targets:
            variables = {"HOST": host}
            if target == "baremetal/fulliso" and ubuntu_iso:
                variables["UBUNTU_ISO"] = ubuntu_iso
            run_make(target, variables=variables, sops_env=sops_env)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        sys.exit(exc.returncode or 1)

    summarize_outputs(host)


def handle_clean(sops_env: Dict[str, str]) -> None:
    confirmation = input(
        "Cette opération supprime les artefacts générés dans baremetal/autoinstall/generated/. "
        "Continuer ? [o/N] : "
    ).strip().lower()
    if confirmation not in {"o", "oui", "y", "yes"}:
        print("Opération annulée.")
        return

    try:
        run_make("baremetal/clean", variables=None, sops_env=sops_env)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        sys.exit(exc.returncode or 1)

    print("\nArtefacts supprimés.")


def prompt_main_action() -> int:
    options = (
        "Mettre à jour le dépôt Git",
        "Mettre à jour l'environnement local",
        "Initialiser un nouvel hôte",
        "Générer des ISO pour un hôte",
        "Nettoyer les artefacts générés",
        "Quitter",
    )
    return prompt_choice(options, "Actions disponibles :")


def main() -> None:
    print("Ubuntu Autoinstall – Assistant de génération d'ISO")
    print("================================================\n")

    check_required_binaries(("git", "make", "sops", "age"))

    sops_env = prepare_sops_environment(os.environ.copy())
    while True:
        choice = prompt_main_action()
        if choice == 0:
            handle_repository_update()
        elif choice == 1:
            handle_environment_update(sops_env)
        elif choice == 2:
            handle_host_initialization(sops_env)
        elif choice == 3:
            handle_iso_generation(sops_env)
        elif choice == 4:
            handle_clean(sops_env)
        else:
            print("Au revoir !")
            break


if __name__ == "__main__":
    main()
