#!/usr/bin/env python3
"""Interactive helper to drive the Ubuntu Autoinstall toolchain.

The wizard guides the operator through the necessary `make` targets to render
Autoinstall configurations, assemble ISO images, manage SOPS/age keys and
trigger common Ansible playbooks. All commands remain idempotent and rely on
existing Makefile targets so that the CI/CD pipeline can replay the same
operations.
"""
from __future__ import annotations

import os
import re
import shlex
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
REQUIRED_BINARIES = ("git", "make")
RECOMMENDED_BINARIES = ("sops", "age", "age-keygen", "ansible-playbook")
SOPS_INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install-sops.sh"
AGE_INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install-age.sh"
INSTALLER_HINTS = {
    "sops": "scripts/install-sops.sh",
    "age": "scripts/install-age.sh",
}
CANCEL_KEYWORDS = {"q", "quit", "annuler", "cancel", "stop", "exit", ":q"}
YES_CHOICES = {"", "o", "oui", "y", "yes"}


class UserCancelled(RuntimeError):
    """Raised when the operator cancels the current interaction."""


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


@dataclass(frozen=True)
class PlaybookAction:
    """Describe an Ansible make target exposed through the wizard."""

    label: str
    make_target: str
    requires_host: bool = False
    supports_format: bool = False


PLAYBOOK_ACTIONS: List[PlaybookAction] = [
    PlaybookAction(
        label="Regénérer les fichiers Autoinstall (ansible)",
        make_target="baremetal/gen",
        requires_host=True,
    ),
    PlaybookAction(
        label="Valider le rendu cloud-init",
        make_target="baremetal/validate",
        requires_host=True,
    ),
    PlaybookAction(
        label="Découvrir le matériel (playbook Ansible)",
        make_target="baremetal/discover",
        requires_host=True,
    ),
    PlaybookAction(
        label="Lister inventaire + profils (table/json)",
        make_target="baremetal/list",
        supports_format=True,
    ),
    PlaybookAction(
        label="Lister uniquement les hôtes",
        make_target="baremetal/list-hosts",
        supports_format=True,
    ),
    PlaybookAction(
        label="Lister uniquement les profils matériels",
        make_target="baremetal/list-profiles",
        supports_format=True,
    ),
]


def check_required_binaries(binaries: Sequence[str]) -> None:
    missing = [binary for binary in binaries if shutil.which(binary) is None]
    if not missing:
        return
    formatted_missing = []
    for binary in missing:
        hint = INSTALLER_HINTS.get(binary)
        if hint:
            formatted_missing.append(f"{binary} (installer : {hint})")
        else:
            formatted_missing.append(binary)
    formatted = ", ".join(formatted_missing)
    print(
        "Les binaires requis suivants sont introuvables dans le PATH : "
        f"{formatted}. Installez-les avant de continuer.",
        file=sys.stderr,
    )
    sys.exit(1)


def warn_missing_binaries(binaries: Sequence[str]) -> None:
    """Display a non-blocking warning when optional binaries are absent."""

    missing = [binary for binary in binaries if shutil.which(binary) is None]
    if not missing:
        return
    formatted = ", ".join(sorted(missing))
    print(
        "ℹ️ Dépendances recommandées absentes du PATH : "
        f"{formatted}. Utilisez le menu \"Mettre à jour l'environnement local\" pour les installer.",
        file=sys.stderr,
    )


def list_hosts() -> List[str]:
    """Return the list of host directories declared in the inventory."""

    if not HOST_VARS_DIR.exists():
        print(f"Inventaire introuvable : {HOST_VARS_DIR}", file=sys.stderr)
        sys.exit(1)

    hosts = [
        entry.name
        for entry in HOST_VARS_DIR.iterdir()
        if entry.is_dir()
        and not entry.name.startswith(".")
        and any((entry / filename).is_file() for filename in ("main.yml", "main.yaml"))
    ]
    hosts.sort()
    return hosts


def list_host_files(host_dir: Path) -> List[Path]:
    """Return editable files declared for a given host."""

    if not host_dir.exists():
        return []

    files = [
        entry
        for entry in host_dir.iterdir()
        if entry.is_file() and not entry.name.startswith(".")
    ]
    files.sort()
    return files


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


def prompt_choice(
    options: Sequence[str],
    prompt: str,
    *,
    allow_cancel: bool = False,
    cancel_label: str = "Annuler",
) -> int:
    """Display a numeric menu and return the selected index."""

    while True:
        print(prompt)
        for idx, option in enumerate(options, start=1):
            print(f"  {idx}. {option}")
        if allow_cancel:
            print(f"  0. {cancel_label}")
        raw = input("Sélectionnez une option : ").strip()
        if allow_cancel and raw == "0":
            raise UserCancelled
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
    idx = prompt_choice(hosts, "Hôtes disponibles :", allow_cancel=True)
    return hosts[idx]


def prompt_new_host_name() -> str:
    pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
    while True:
        name = input("Nom d'hôte (alphanumérique, ._- autorisés, :q pour annuler) : ").strip()
        if name.lower() in CANCEL_KEYWORDS:
            raise UserCancelled
        if not name:
            print("Le nom d'hôte est obligatoire.\n")
            continue
        if not pattern.match(name):
            print("Nom invalide. Utilisez uniquement lettres, chiffres, points, tirets, underscores.\n")
            continue
        return name


def prompt_iso_action() -> IsoAction:
    idx = prompt_choice(
        [action.label for action in ISO_ACTIONS],
        "Quel type d'image générer ?",
        allow_cancel=True,
    )
    return ISO_ACTIONS[idx]


def prompt_iso_path(default: str) -> str:
    while True:
        candidate = input(
            f"Chemin vers l'ISO Ubuntu officielle [{default}] (:q pour annuler) : "
        ).strip()
        if candidate.lower() in CANCEL_KEYWORDS:
            raise UserCancelled
        if not candidate:
            candidate = default
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path)
        print(f"ISO introuvable à l'emplacement : {path}\n")


def prompt_age_key_file(default: Path) -> Path:
    while True:
        candidate = input(
            f"Chemin de la clé age pour SOPS [{default}] (:q pour annuler) : "
        ).strip()
        if candidate.lower() in CANCEL_KEYWORDS:
            raise UserCancelled
        if not candidate:
            candidate = str(default)
        path = Path(candidate).expanduser()
        if path.is_file():
            return path
        print(f"Fichier de clé age introuvable : {path}\n")


def prompt_age_key_output(default: Path) -> Path:
    while True:
        candidate = input(
            f"Emplacement du fichier de clé age [{default}] (:q pour annuler) : "
        ).strip()
        if candidate.lower() in CANCEL_KEYWORDS:
            raise UserCancelled
        if not candidate:
            candidate = str(default)
        path = Path(candidate).expanduser()
        if path.is_dir():
            print("Le chemin fourni correspond à un répertoire. Indiquez un fichier.\n")
            continue
        if " " in str(path):
            print("Les chemins contenant des espaces ne sont pas pris en charge.\n")
            continue
        return path


def detect_editor() -> List[str]:
    """Return the preferred text editor command."""

    for env_var in ("VISUAL", "EDITOR"):
        value = os.environ.get(env_var)
        if value:
            command = shlex.split(value)
            if command:
                return command

    for candidate in ("nano", "vi", "vim"):
        if shutil.which(candidate):
            return [candidate]

    raise FileNotFoundError(
        "Aucun éditeur texte détecté (VISUAL/EDITOR non définis et nano/vi/vim absents)."
    )


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

    try:
        path = prompt_age_key_file(default_path)
    except UserCancelled:
        print("Opération annulée.")
        return {}
    return {"SOPS_AGE_KEY_FILE": str(path)}


def run_command(
    command: Sequence[str], *, env: Dict[str, str] | None = None, cwd: Path | None = None
) -> None:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    print("\n▶", " ".join(command))
    subprocess.run(command, check=True, env=effective_env, cwd=str(cwd or REPO_ROOT))


def run_make(
    target: str,
    *,
    variables: Dict[str, str] | None,
    sops_env: Dict[str, str],
    propagate_profile: bool = True,
) -> None:
    command: List[str] = ["make", target]
    if variables:
        for key, value in variables.items():
            command.append(f"{key}={value}")
    env = dict(sops_env)
    if propagate_profile and variables:
        profile_candidate = variables.get("PROFILE") or variables.get("HOST")
        if profile_candidate:
            env["PROFILE"] = profile_candidate
    run_command(command, env=env)


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


def edit_host_file(path: Path, sops_env: Dict[str, str]) -> None:
    """Open the requested file with the appropriate editor."""

    if ".sops." in path.name:
        if shutil.which("sops") is None:
            print(
                "⚠️ Impossible d'éditer les secrets : le binaire `sops` est introuvable.",
                file=sys.stderr,
            )
            return
        run_command(["sops", str(path)], env=sops_env, cwd=path.parent)
        return

    try:
        editor = detect_editor()
    except FileNotFoundError as error:
        print(f"⚠️ {error}", file=sys.stderr)
        return

    run_command([*editor, str(path)], env=sops_env, cwd=path.parent)


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
    if shutil.which("age") is None and AGE_INSTALL_SCRIPT.is_file():
        install_age = input(
            "Le binaire age est introuvable. Lancer scripts/install-age.sh ? [O/n] : "
        ).strip().lower()
        if install_age in {"", "o", "oui", "y", "yes"}:
            try:
                run_command(["bash", str(AGE_INSTALL_SCRIPT)], env=sops_env)
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
    try:
        host = prompt_new_host_name()
    except UserCancelled:
        print("Opération annulée.")
        return

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
        try:
            profile_idx = prompt_choice(
                profiles,
                "Profils matériels disponibles :",
                allow_cancel=True,
                cancel_label="Annuler la sélection et revenir au menu",
            )
        except UserCancelled:
            print("Opération annulée.")
            return
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

    customize = input(
        "Souhaitez-vous ouvrir ces fichiers pour les personnaliser tout de suite ? [O/n] : "
    ).strip().lower()
    if customize in YES_CHOICES:
        handle_host_customization(sops_env, host=host)


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

    try:
        host = prompt_host(hosts)
    except UserCancelled:
        print("Opération annulée.")
        return
    print(f"\nHôte sélectionné : {host}\n")

    try:
        action = prompt_iso_action()
    except UserCancelled:
        print("Opération annulée.")
        return
    ubuntu_iso: str | None = None
    if action.requires_ubuntu_iso:
        try:
            ubuntu_iso = prompt_iso_path(os.environ.get("UBUNTU_ISO", DEFAULT_UBUNTU_ISO))
        except UserCancelled:
            print("Opération annulée.")
            return

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


def display_selected_age_key(path: Path | None) -> None:
    if path:
        print(f"Clé age active : {path}")
    else:
        print(
            "Aucune clé age n'est configurée. Générer ou sélectionner un fichier avant de chiffrer des secrets."
        )


def generate_age_key(sops_env: Dict[str, str]) -> Dict[str, str]:
    current_value = sops_env.get("SOPS_AGE_KEY_FILE")
    default_path = Path(current_value).expanduser() if current_value else DEFAULT_AGE_KEY_FILE
    try:
        target_path = prompt_age_key_output(default_path)
    except UserCancelled:
        print("Opération annulée.")
        return sops_env

    overwrite = False
    if target_path.exists():
        confirm = input(
            f"Le fichier {target_path} existe déjà. Le remplacer ? [o/N] : "
        ).strip().lower()
        if confirm not in {"o", "oui", "y", "yes"}:
            print("Opération annulée.")
            return sops_env
        overwrite = True

    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["make", "age/keygen", f"OUTPUT={target_path}"]
    if overwrite:
        command.append("OVERWRITE=1")
    try:
        run_command(command, env=sops_env)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
        return sops_env

    updated_env = dict(sops_env)
    updated_env["SOPS_AGE_KEY_FILE"] = str(target_path)
    print(
        "\nClé age générée. Sauvegardez la clé privée dans votre gestionnaire de secrets et partagez uniquement la clé publique."
    )
    display_selected_age_key(target_path)
    return updated_env


def select_existing_age_key(sops_env: Dict[str, str]) -> Dict[str, str]:
    current_value = sops_env.get("SOPS_AGE_KEY_FILE")
    default_path = Path(current_value).expanduser() if current_value else DEFAULT_AGE_KEY_FILE
    try:
        path = prompt_age_key_file(default_path)
    except UserCancelled:
        print("Opération annulée.")
        return sops_env

    updated_env = dict(sops_env)
    updated_env["SOPS_AGE_KEY_FILE"] = str(path)
    display_selected_age_key(path)
    return updated_env


def show_age_public_key(sops_env: Dict[str, str]) -> None:
    raw_path = sops_env.get("SOPS_AGE_KEY_FILE")
    if not raw_path:
        print(
            "⚠️ Aucune clé age n'est sélectionnée. Générez ou sélectionnez un fichier avant d'afficher la clé publique.",
            file=sys.stderr,
        )
        return
    path = Path(raw_path).expanduser()
    if not path.is_file():
        print(f"⚠️ Le fichier {path} est introuvable.", file=sys.stderr)
        return
    try:
        run_command(["make", "age/show-recipient", f"OUTPUT={path}"], env=sops_env)
    except subprocess.CalledProcessError as exc:
        print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)


def handle_age_key_management(sops_env: Dict[str, str]) -> Dict[str, str]:
    env = dict(sops_env)
    while True:
        print("\nGestion des clés SOPS/age")
        print("-------------------------")
        display_selected_age_key(
            Path(env["SOPS_AGE_KEY_FILE"]).expanduser() if env.get("SOPS_AGE_KEY_FILE") else None
        )
        try:
            choice = prompt_choice(
                (
                    "Sélectionner un fichier de clé existant",
                    "Générer une nouvelle clé age",
                    "Afficher la clé publique (recipient)",
                ),
                "Actions disponibles :",
                allow_cancel=True,
                cancel_label="Retour au menu principal",
            )
        except UserCancelled:
            return env

        if choice == 0:
            env = select_existing_age_key(env)
        elif choice == 1:
            env = generate_age_key(env)
        else:
            show_age_public_key(env)


def handle_host_customization(
    sops_env: Dict[str, str], *, host: str | None = None
) -> None:
    """Let the operator edit host_vars files without leaving the wizard."""

    selected_host = host
    if selected_host is None:
        hosts = list_hosts()
        if not hosts:
            print(
                "Aucun hôte disponible. Initialisez-en un avant de personnaliser les fichiers.",
                file=sys.stderr,
            )
            return
        try:
            selected_host = prompt_host(hosts)
        except UserCancelled:
            print("Opération annulée.")
            return
    host_dir = HOST_VARS_DIR / selected_host
    files = list_host_files(host_dir)
    if not files:
        print(
            f"Aucun fichier à personnaliser dans {host_dir.relative_to(REPO_ROOT)}.",
            file=sys.stderr,
        )
        return

    while True:
        options = [
            str(path.relative_to(REPO_ROOT))
            for path in files
        ] + ["Terminer la personnalisation"]
        try:
            choice = prompt_choice(
                options,
                "Fichiers disponibles :",
                allow_cancel=True,
                cancel_label="Retour au menu principal",
            )
        except UserCancelled:
            print("Opération annulée.")
            return
        if choice == len(options) - 1:
            print("Personnalisation terminée.")
            return
        edit_host_file(files[choice], sops_env)


def prompt_output_format() -> str:
    choice = prompt_choice(
        ("table (lecture humaine)", "json (scripts/CI)"),
        "Format de sortie :",
        allow_cancel=True,
        cancel_label="Annuler et revenir au menu",
    )
    if choice == 1:
        return "json"
    return "table"


def handle_playbook_management(sops_env: Dict[str, str]) -> None:
    while True:
        try:
            idx = prompt_choice(
                [action.label for action in PLAYBOOK_ACTIONS],
                "Playbooks disponibles :",
                allow_cancel=True,
                cancel_label="Retour au menu principal",
            )
        except UserCancelled:
            return

        action = PLAYBOOK_ACTIONS[idx]
        variables: Dict[str, str] = {}
        if action.requires_host:
            hosts = list_hosts()
            try:
                host = prompt_host(hosts)
            except UserCancelled:
                print("Opération annulée.")
                continue
            variables["HOST"] = host
            print(f"\nHôte sélectionné : {host}\n")

        if action.supports_format:
            try:
                selected_format = prompt_output_format()
            except UserCancelled:
                print("Opération annulée.")
                continue
            variables["FORMAT"] = selected_format

        try:
            run_make(
                action.make_target,
                variables=variables or None,
                sops_env=sops_env,
                propagate_profile=action.requires_host,
            )
        except subprocess.CalledProcessError as exc:
            print(f"La commande s'est terminée avec une erreur : {exc}", file=sys.stderr)
            return

        if action.supports_format:
            print()


def prompt_main_action() -> int:
    options = (
        "Mettre à jour le dépôt Git",
        "Mettre à jour l'environnement local",
        "Gérer les clés SOPS/age",
        "Initialiser un nouvel hôte",
        "Personnaliser la configuration d'un hôte",
        "Générer des ISO pour un hôte",
        "Gérer les playbooks Ansible",
        "Nettoyer les artefacts générés",
        "Quitter",
    )
    return prompt_choice(options, "Actions disponibles :")


def main() -> None:
    print("Ubuntu Autoinstall – Assistant de génération d'ISO")
    print("================================================\n")

    check_required_binaries(REQUIRED_BINARIES)
    warn_missing_binaries(RECOMMENDED_BINARIES)

    sops_env = prepare_sops_environment(os.environ.copy())
    while True:
        choice = prompt_main_action()
        if choice == 0:
            handle_repository_update()
        elif choice == 1:
            handle_environment_update(sops_env)
        elif choice == 2:
            sops_env = handle_age_key_management(sops_env)
        elif choice == 3:
            handle_host_initialization(sops_env)
        elif choice == 4:
            handle_host_customization(sops_env)
        elif choice == 5:
            handle_iso_generation(sops_env)
        elif choice == 6:
            handle_playbook_management(sops_env)
        elif choice == 7:
            handle_clean(sops_env)
        else:
            print("Au revoir !")
            break


if __name__ == "__main__":
    main()
