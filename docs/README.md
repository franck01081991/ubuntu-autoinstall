# Ubuntu Autoinstall bare metal factory

## Objectifs
- Fournir une ISO unique pour tous les serveurs bare metal, personnalisée par hôte via NoCloud.
- Appliquer par défaut un chiffrement LUKS2 + LVM et un durcissement inspiré de l'ANSSI.
- Industrialiser la génération via Makefile, Dockerfile et GitHub Actions.
- Protéger tous les secrets avec SOPS et age.

## Prérequis
- Ubuntu 24.04 ou équivalent avec `make`, `python3`, `ansible`, `sops`, `age`, `xorriso`, `squashfs-tools`.
- Accès à la clé age privée permettant de déchiffrer `baremetal/inventory/host_vars/<host>/secrets.sops.yaml`.
- `sops` CLI disponible dans le PATH pour déchiffrer `secrets.sops.yaml`.

## Commandes essentielles
| Étape | Commande | Description |
| ----- | -------- | ----------- |
| 1. Initialiser un hôte | `make new-host HOST=serveur1 DISK=/dev/sda` | Crée le dossier `baremetal/inventory/host_vars/serveur1/` et prépare les fichiers `main.yml` + `secrets.sops.yaml`. |
| 2. Renseigner le secret | `sops baremetal/inventory/host_vars/serveur1/secrets.sops.yaml` | Chiffrer `encrypt_disk_passphrase` (et les clés SSH si besoin). |
| 3. Générer l'autoinstall | `make gen HOST=serveur1` | Rend `user-data` + `meta-data` sous `baremetal/autoinstall/generated/serveur1/`. |
| 4. Construire une ISO autonome | `make iso HOST=serveur1 UBUNTU_ISO=ubuntu-24.04-live-server-amd64.iso` | Produit une ISO NoCloud autonome contenant les fichiers de l'hôte. |

## Références complémentaires
- [docs/autoinstall.md](autoinstall.md) pour le fonctionnement Subiquity/NoCloud.
- [docs/securite-anssi.md](securite-anssi.md) pour le durcissement appliqué.
- [docs/ci-cd.md](ci-cd.md) pour le pipeline GitHub Actions et les contrôles.
