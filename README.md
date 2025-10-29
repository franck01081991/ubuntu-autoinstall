# ubuntu-autoinstall-git

Provisionner **Ubuntu Server 24.04 LTS** hôte par hôte (ThinkCentre M710q, Dell
OptiPlex 3020M) grâce à **Autoinstall + cloud-init (NoCloud)** dans une approche
GitOps pilotée par Git, CI/CD et revue de code.

> 👋 **Nouveau dans le dépôt ?** Consultez le [guide débutant](docs/getting-started-beginner.md)
> pour découvrir pas à pas la chaîne GitOps et lancer votre premier rendu
> autoinstall.

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture GitOps](#architecture-gitops)
- [Structure du dépôt](#structure-du-dépôt)
- [Périmètre bare metal](#périmètre-bare-metal)
- [Prérequis](#prérequis)
- [Démarrage rapide (bare metal)](#démarrage-rapide-bare-metal)
- [Parcours débutant](#parcours-débutant)
- [Profils matériels](#profils-matériels)
- [Variables d'hôte bare metal](#variables-dhôte-bare-metal)
- [Gestion des variables et secrets partagés](#gestion-des-variables-et-secrets-partagés)
- [Commandes Make disponibles](#commandes-make-disponibles)
- [Tests et validation](#tests-et-validation)
- [Intégration continue](#intégration-continue)
- [Sécurité et conformité](#sécurité-et-conformité)
- [Provisioning VPS avec Ansible (sans ISO)](#provisioning-vps-avec-ansible-sans-iso)
- [Ressources supplémentaires](#ressources-supplémentaires)

## Vue d'ensemble

Ce dépôt fournit deux chaînes GitOps distinctes :

- **`baremetal/`** : génération des fichiers autoinstall et des ISO (seed et
  full) pour les hôtes physiques Ubuntu Server 24.04 LTS.
- **`vps/`** : déploiement applicatif et post-installation pour les VPS,
  orchestrés uniquement par Ansible sans ISO.

Chaque hôte bare metal possède ses propres variables inventoriées afin de
garantir des déploiements reproductibles et idempotents. Les ISO générées (seed
ou complètes) sont archivées dans les artefacts de pipeline pour assurer
l'auditabilité. Une bibliothèque de **profils matériels** dans
`baremetal/inventory/profiles/hardware/` permet de valider la génération
d'autoinstall par modèle via la CI.

## Architecture GitOps

- **Définition déclarative** :
  - les paramètres spécifiques à chaque hôte bare metal résident dans
    `baremetal/inventory/host_vars/<hôte>.yml` ;
  - les profils matériels standards vivent dans
    `baremetal/inventory/profiles/hardware/<profil>.yml` et servent de
    référence partagée.
- **Rendu automatisé** : Ansible et Jinja2 génèrent les fichiers
  `user-data`/`meta-data` dans `baremetal/autoinstall/generated/<hôte>/`.
  - le playbook `baremetal/ansible/playbooks/generate_autoinstall.yml` calcule
    dynamiquement les chemins `autoinstall/` et `inventory/host_vars/` via
    `{{ playbook_dir }}` pour rester fiable quel que soit le répertoire
    d'exécution (ex. `make baremetal/gen`).
- **Distribution contrôlée** : la CI construit les ISO d'installation, stockées
  en artefacts et récupérées lors du déploiement.
- **Aucune intervention manuelle** : l'intégralité du flux passe par Git,
  CI/CD et les commandes documentées.

## Structure du dépôt

```text
baremetal/
├── ansible/            # Playbook de rendu autoinstall (NoCloud)
├── autoinstall/        # Templates Jinja2 + artefacts générés
├── inventory/          # Host vars et profils matériels bare metal
└── scripts/            # Génération ISO seed/full
vps/
├── ansible/            # Playbook de provisioning applicatif
└── inventory/          # Inventaire et secrets chiffrés SOPS
ansible/                # Dépendances communes (collections, requirements)
scripts/install-sops.sh # Installation SOPS (baremetal & vps)
```

## Périmètre bare metal

- **Infrastructure ciblée** : ce dépôt gère exclusivement le provisioning
  **bare metal** (ISO seed ou complète) pour les hôtes Ubuntu Server.
- **Pas d'IaC cloud** : aucune ressource distante (Terraform, Kubernetes,
  secrets chiffrés) n'est gérée ici ; tout changement d'infrastructure cloud
  doit être traité dans un dépôt dédié.
- **Traçabilité GitOps** : chaque hôte ou profil matériel est décrit via
  Ansible/Jinja et suivi par la CI, ce qui assure une auditabilité complète sans
  scripts ad hoc.

## Prérequis

- Ubuntu 24.04 Live Server ISO officiel (pour `make baremetal/fulliso`).
- Python 3.10+ et Ansible installés dans l'environnement de build.
- Outils systèmes : `mkpasswd`, `cloud-localds`, `xorriso`, `genisoimage` ou
  équivalents selon la distribution.
- [SOPS](https://github.com/getsops/sops) et une paire de clés
  [age](https://age-encryption.org/) pour chiffrer les variables sensibles. Le
  script `scripts/install-sops.sh` installe la version recommandée (Linux
  amd64) en vérifiant la somme SHA-256.
- Clés SSH valides et un mot de passe chiffré (YESCRYPT recommandé) pour chaque
  hôte.

## Démarrage rapide (bare metal)

> 🎯 Idéal pour un premier rendu autoinstall sans personnalisation avancée.

1. **Choisir (ou non) un profil matériel**

   ```bash
   ls baremetal/inventory/profiles/hardware
   make baremetal/gen PROFILE=lenovo-m710q
   ```

   Les artefacts sont générés sous
   `baremetal/autoinstall/generated/lenovo-m710q/`.

2. **Cloner un fichier d'exemple pour l'hôte**

   ```bash
   cp baremetal/inventory/host_vars/example.yml \
     baremetal/inventory/host_vars/site-a-m710q1.yml
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1.yml
   ```

   Le guide débutant détaille les champs clés à modifier (hostname, réseau,
   disques).

3. **Générer les fichiers autoinstall**

   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```

4. **Construire l'ISO seed (`CIDATA`)**

   ```bash
   make baremetal/seed HOST=site-a-m710q1
   ```

   L'ISO est exportée dans
   `baremetal/autoinstall/generated/site-a-m710q1/seed-site-a-m710q1.iso`.

5. **Démarrer l'installation automatisée**

   - Graver l'ISO officielle d'Ubuntu sur une clé USB (USB #1).
   - Monter l'ISO seed sur une deuxième clé USB ou via une clé USB dédiée
     (USB #2).
   - Démarrer sur l'installateur Ubuntu, appuyer sur `e` dans GRUB et ajouter
     `autoinstall` à la ligne Linux.
   - L'installation est ensuite entièrement automatisée via cloud-init
     (NoCloud).

6. **(Optionnel) Construire une ISO complète avec autoinstall intégré**

   ```bash
   make baremetal/fulliso HOST=site-a-m710q1 \
     UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso
   ```

   Le script `baremetal/scripts/make_full_iso.sh` rejoue la configuration de
   démarrage de l'ISO source via `xorriso` afin d'ajouter le dossier `nocloud/`
   sans dépendre d'`isolinux/` (flag `-boot_image any replay`).

## Parcours débutant

- 📘 **Guide pas à pas** : suivez le [parcours détaillé](docs/getting-started-beginner.md)
  pour découvrir la structure du dépôt, comprendre les variables essentielles et
  rejouer la génération autoinstall via `make`.
- 🧠 **Concepts clés** : résumés des notions GitOps, autoinstall et SOPS avec des
  liens vers la documentation amont.
- ✅ **Checklist de validation** : assurez-vous que les commandes locales,
  l'outillage (Ansible, SOPS) et la CI produisent les mêmes artefacts.

## Profils matériels

Les profils sous `baremetal/inventory/profiles/hardware/` décrivent les valeurs
minimales par modèle pour valider la génération autoinstall (disque, interface
réseau, clés SSH de test, etc.). Chaque fichier peut être référencé via
`make baremetal/gen PROFILE=<profil>` et sert de base pour définir des sites
spécifiques via Ansible.

- `lenovo-m710q` : ThinkCentre M710q Tiny équipé d'un NVMe et d'un emplacement
  SATA 2,5". Le profil assemble les deux disques dans le même volume LVM afin
  d'offrir une capacité unique.
  - Optimisations : microcode Intel, `thermald`, `powertop` (service d'auto-
    tune) et `lm-sensors` sont préinstallés pour stabiliser les températures et
    l'efficacité énergétique du châssis compact.
- `lenovo-90dq004yfr` : ThinkCentre M700 Tiny (référence 90DQ004YFR) basé
  uniquement sur un disque SATA. Ce profil applique les optimisations
  d'alimentation et de microcode adaptées aux puces Intel de cette génération.

## Variables d'hôte bare metal

Chaque fichier `baremetal/inventory/host_vars/<hôte>.yml` peut contenir les
paramètres suivants :

- `hostname` : nom d'hôte configuré pendant l'installation.
- `disk_device` : disque système principal (ex. `/dev/nvme0n1`).
- `additional_disk_devices` : liste de disques supplémentaires à intégrer au VG
  LVM (ex. `['/dev/sda']`).
- `netmode` : `dhcp` ou `static`.
- `nic` : interface réseau (ex. `enp1s0`) pour IP statique.
- `ip`, `cidr`, `gw`, `dns` : paramètres réseau statiques.
- `ssh_authorized_keys` : liste des clés publiques autorisées.
- `password_hash` : hash de mot de passe (YESCRYPT ou SHA512).
- `extra_packages` : liste additionnelle de paquets à installer (ex.
  optimisations matérielles).
- `enable_powertop_autotune` : active la création/activation du service systemd
  `powertop-autotune`.

## Gestion des variables et secrets partagés

- Les variables communes aux VPS vivent dans `vps/inventory/group_vars/vps/`
  pour rester proches de l'inventaire GitOps.
- Les secrets sont versionnés sous forme **chiffrée** avec
  [SOPS](https://github.com/getsops/sops) :
  1. Copier le modèle :

     ```bash
     cp vps/inventory/group_vars/vps/secrets.sops.yaml.example \
       vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

  2. Installer SOPS si nécessaire :

     ```bash
     sudo bash scripts/install-sops.sh /usr/local/bin
     ```

  3. Ajouter votre clé publique age à `.sops.yaml` (`age1...`).
  4. Chiffrer le fichier :

     ```bash
     sops --encrypt --in-place \
       vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

  5. Éditer le secret de façon sécurisée :

     ```bash
     sops vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

Les clés `vps_external_dns_api_token` et `vps_keycloak_admin_password` doivent
être présentes dans ce fichier pour que le playbook
`vps/ansible/playbooks/provision.yml` aboutisse. Un échec explicite est
lancé si ces valeurs manquent.

## Commandes Make disponibles

- `make baremetal/gen HOST=<nom>` : génère `user-data` et `meta-data` dans
  `baremetal/autoinstall/generated/<nom>/`.
- `make baremetal/gen PROFILE=<profil>` : génère les artefacts pour un profil
  matériel sous `baremetal/autoinstall/generated/<profil>/`.
- `make baremetal/seed HOST=<nom>` : construit `seed-<nom>.iso` (NoCloud
  `CIDATA`).
- `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` : construit un
  installateur complet avec autoinstall et boot flags.
- `make baremetal/clean` : supprime les artefacts générés.
- `make vps/provision` : applique le playbook Ansible sur l'inventaire VPS
  (post-installation, aucune ISO).
- `make vps/lint` : lance `yamllint` et `ansible-lint` sur la chaîne VPS.
- `make lint` : agrège `yamllint`, `ansible-lint`, `shellcheck` et
  `markdownlint` sur l'ensemble du dépôt (mêmes contrôles que la CI « Repository
  Integrity »).

## Tests et validation

- `make lint` : exécute l'intégralité des contrôles syntaxiques (`yamllint`,
  `ansible-lint`, `shellcheck`, `markdownlint`). Prérequis : disposer de
  `shellcheck` et `markdownlint` dans le `PATH` local.
- `make vps/lint` : lint ciblé sur la chaîne VPS (`yamllint` + `ansible-lint`).
- `ansible-lint` : rejouer localement une analyse profonde (utile pour du
  débogage ciblé).
- `yamllint baremetal/inventory baremetal/ansible vps/inventory vps/ansible` :
  vérifier uniquement la syntaxe YAML.
- `trivy fs --security-checks config,secret --severity HIGH,CRITICAL .` :
  scanner localement la configuration et la détection de secrets (mêmes
  seuils que la CI).
- `pip install -r ansible/requirements.txt` : garantit l'utilisation de
  `ansible-core` en version 2.16.13 (correctif CVE-2024-8775) avant d'exécuter
  les playbooks.

## Intégration continue

- Le workflow `.github/workflows/repository-integrity.yml` garantit
  l'intégrité du dépôt :
  - job **Static analysis** : relance `yamllint`, `ansible-lint`, `shellcheck`
    et `markdownlint` (identique à `make lint`).
  - job **Trivy configuration scan** : `trivy fs` échoue en cas de
    vulnérabilités **HIGH/CRITICAL** ou de secrets révélés.
- Le workflow `.github/workflows/build-iso.yml` rend les fichiers autoinstall
  **par modèle matériel** (`PROFILE`) et construit les ISO seed/full pour
  validation.
- Pour lancer manuellement : **Actions → Build Bare Metal ISOs → Run
  workflow** et, si besoin, surcharger `UBUNTU_ISO_URL`.
  - par défaut, la CI télécharge l'image depuis
    `https://old-releases.ubuntu.com/releases/24.04/ubuntu-24.04-live-server-amd64.iso`
    pour garantir la disponibilité dans le temps. Un cache ISO (`.cache/`)
    évite les téléchargements répétés.
- Les artefacts générés sont regroupés par profil matériel pour simplifier la
  traçabilité et sont conservés **1 jour** (`retention-days: 1`).
- Avant chaque téléversement, la CI supprime les artefacts GitHub Actions
  existants pour le même profil (`autoinstall-<profil>`) afin d'éviter d'atteindre
  le quota de stockage lorsque le workflow s'exécute depuis le dépôt principal
  (branches locales ou workflows manuels).
- Si le quota GitHub Actions est dépassé ou que le token ne dispose pas des
  droits suffisants, l'upload d'artefacts échoue en avertissant mais sans
  interrompre le workflow (mode best-effort, artefacts absents à récupérer
  manuellement si besoin).

## Sécurité et conformité

- Toujours remplacer les clés SSH de démonstration par des clés réelles
  spécifiques.
- Générer des mots de passe via `mkpasswd -m yescrypt` (paquet `whois`) ou
  `openssl passwd -6` pour SHA512.
- Les configurations réseau appliquent BBR, `rp_filter=2`, désactivent les
  redirections ICMP et activent `irqbalance`.
- Les artefacts ISO publiés dans la CI doivent être stockés dans un espace
  contrôlé (ex. artefacts GitHub Actions).

## Provisioning VPS avec Ansible (sans ISO)

Les VPS sont provisionnés **uniquement** via Ansible : aucune ISO n'est
construite ni montée sur ces hôtes.

Pour finaliser la configuration d'un VPS après installation :

```bash
ansible-playbook -i vps/inventory/hosts.yml \
  vps/ansible/playbooks/provision.yml -u ubuntu --become
```

Définir les variables via `vps/inventory/group_vars/vps/` (voir section
précédente) ou, pour des tests ponctuels, l'option `-e`.

Avant exécution :

```bash
ansible-galaxy collection install -r ansible/collections/requirements.yml
```

Le fichier `ansible/collections/requirements.yml` épingle `community.sops`
(**1.6.0**), `community.kubernetes` (**2.0.3**) et `kubernetes.core` (**3.0.1**)
afin d'alimenter les modules Helm/kubectl nécessaires aux déploiements GitOps.

## Ressources supplémentaires

- [Documentation originale en anglais](README.en.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
