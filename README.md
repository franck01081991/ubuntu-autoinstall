# Ubuntu Autoinstall

Chaîne **GitOps** dédiée à la création d'ISO Ubuntu Server 24.04 LTS entièrement
automatisées grâce à **Autoinstall + cloud-init (NoCloud)**. Chaque image est
rendue à partir de fichiers versionnés et produite manuellement en dehors de la
CI pour garantir la reproductibilité et l'auditabilité.

> 👋 Nouveau ou nouvelle ? Commencez par le
> [guide débutant](docs/getting-started-beginner.md) pour produire votre première
> ISO seed en local puis valider votre pipeline GitOps.

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Approche GitOps pour les ISO](#approche-gitops-pour-les-iso)
- [Structure du dépôt](#structure-du-dépôt)
- [Inventaire et templates](#inventaire-et-templates)
- [Prérequis](#prérequis)
- [Démarrage rapide](#démarrage-rapide)
- [Commandes Make clés](#commandes-make-clés)
- [Validation et CI/CD](#validation-et-cicd)
- [Sécurité et conformité](#sécurité-et-conformité)
- [Chiffrement du disque](#chiffrement-du-disque)
- [Ressources supplémentaires](#ressources-supplémentaires)

## Vue d'ensemble

Le dépôt concentre tous les éléments nécessaires pour construire deux variantes
principales d'ISO Autoinstall pour serveurs **bare metal** :

- **ISO seed (`CIDATA`)** : embarque uniquement `user-data` et `meta-data` à
  monter aux côtés de l'ISO officielle.
- **ISO complète** : intègre les fichiers NoCloud directement dans l'image
  Ubuntu Live Server.

Les périmètres historiques (provisioning applicatif, overlay réseau, VPS, etc.)
ont été purgés du dépôt pour ne conserver que la chaîne de génération bare
metal. Les composants supprimés restent disponibles dans l'historique Git.

## Approche GitOps pour les ISO

- **Définition déclarative** : chaque hôte ou profil est décrit par YAML sous
  `baremetal/inventory/`. Les valeurs sont versionnées et relues via revue de
  code.
- **Rendu automatisé** : Ansible + Jinja2 produisent les fichiers `user-data` et
  `meta-data` dans `baremetal/autoinstall/generated/<cible>/`.
- **Construction reproductible** : des scripts idempotents sous
  `baremetal/scripts/` créent les ISO seed et complètes à partir des fichiers
  rendus.
- **Validation GitOps** : la CI vérifie que chaque profil matériel et chaque
  machine déclarée compilent correctement leur `user-data` et `meta-data`.
  Chaque équipe peut ensuite générer son ISO en local ou via une usine
  externe.

## Structure du dépôt

```text
baremetal/
├── ansible/            # Playbooks de rendu Autoinstall NoCloud
├── autoinstall/        # Templates Jinja2 + artefacts générés
├── inventory/          # Host vars et profils matériels
└── scripts/            # Génération ISO seed/full
ansible/                # Dépendances et tâches partagées
docs/                   # Guides utilisateurs et décisions d'architecture
scripts/install-sops.sh # Installation SOPS (Linux amd64)
```

Chaque dossier listé est nécessaire à la production GitOps des ISO bare metal.

## Inventaire et templates

- **Profils matériels** (`baremetal/inventory/profiles/hardware/`) : valeurs
  minimales par modèle (disque, interface réseau, paquets optimisés). Servez-vous
  en comme point de départ.
- **Variables hôte** (`baremetal/inventory/host_vars/<hôte>/`) : chaque hôte
  possède un répertoire contenant `main.yml` (valeurs non sensibles) et
  `secrets.sops.yaml` (hash de mot de passe, clés SSH, tokens spécifiques
  chiffrés via SOPS).
- **Inventaire des hôtes** (`baremetal/inventory/hosts.yml`) : vide par défaut
  pour éviter tout état couplé à un environnement. Ajoutez-y uniquement les
  machines que vous souhaitez générer en local ou via la CI GitOps.
- **Templates** (`baremetal/autoinstall/templates/`) : décrivent le `user-data`
  et `meta-data` communs. Ne modifiez qu'en cas d'évolution produit.
- **Profils durcis prêts à l'emploi** :
  - `baremetal/autoinstall/secure-ubuntu-22.04.yaml` : Ubuntu Server 22.04 LTS
    avec chiffrement LUKS+LVM, pare-feu UFW, durcissement SSH et services de
    sécurité activés. Le champ `SOPS_DECRYPTED_DISK_PASSPHRASE` doit être
    remplacé par la passphrase LUKS déchiffrée via la CI (voir ci-dessous).

## Prérequis

- ISO officielle **Ubuntu 24.04 Live Server** pour l'assemblage complet.
- Python 3.10+, `ansible-core`, `xorriso`, `mkpasswd`.
- [SOPS](https://github.com/getsops/sops) et une paire de clés
  [age](https://age-encryption.org/) pour chiffrer les variables sensibles
  éventuelles.
- Accès Git avec revue de code (aucun changement direct en production).

## Démarrage rapide

1. **Installer les dépendances**

   ```bash
   make doctor
   ```

   La commande vérifie la présence des binaires requis et signale les linters
   utilisés par la CI (`yamllint`, `ansible-lint`, `shellcheck`,
   `markdownlint`).

2. **Préparer les variables**

   ```bash
   cp -R baremetal/inventory/host_vars/example \
     baremetal/inventory/host_vars/site-a-m710q1
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1/main.yml
   SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
     sops baremetal/inventory/host_vars/site-a-m710q1/secrets.sops.yaml
   ```

   Personnalisez `main.yml` (hostname, profil matériel, disque, réseau) et
   chiffrez les secrets (`password_hash`, `ssh_authorized_keys`, tokens) dans
   `secrets.sops.yaml`. Activez le chiffrement LUKS en ajoutant
   `disk_encryption.enabled: true` et en référencant la passphrase chiffrée via
   `SOPS` (voir [guide dédié](docs/baremetal-disk-encryption.md)).

3. **Générer les fichiers Autoinstall**

   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```

4. **Construire l'ISO seed**

   ```bash
   make baremetal/seed HOST=site-a-m710q1
   ```

5. **Assembler une ISO complète (optionnel)**

   ```bash
   make baremetal/fulliso HOST=site-a-m710q1 \
     UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso
   ```

Les ISO générées sont stockées sous
`baremetal/autoinstall/generated/<cible>/`.

## Commandes Make clés

- `make doctor` : contrôle des dépendances.
- `make baremetal/gen HOST=<nom>` ou `PROFILE=<profil>` : rendu Autoinstall.
- `make baremetal/seed HOST=<nom>` : création de l'ISO seed.
- `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` : ISO installateur
  autonome.
- `make baremetal/clean` : nettoyage des artefacts générés.
- `make lint` : agrégat des linters utilisés par la CI.

## Utilisation du profil sécurisé Ubuntu 22.04

1. **Déchiffrement GitOps de la passphrase LUKS**

   Stockez la valeur chiffrée dans `docs/secrets/baremetal-luks.sops.yaml` (voir
   ADR-0005) puis utilisez la CI pour rendre un fichier temporaire où la clé
   `SOPS_DECRYPTED_DISK_PASSPHRASE` est remplacée par la valeur déchiffrée.
   Exemple de tâche Ansible (exécutée par la pipeline) :

   ```yaml
   - name: Injecter la passphrase LUKS dans l'autoinstall sécurisé
     ansible.builtin.template:
       src: baremetal/autoinstall/secure-ubuntu-22.04.yaml
       dest: "{{ workspace }}/secure-ubuntu-22.04.rendered.yaml"
       vars:
        SOPS_DECRYPTED_DISK_PASSPHRASE: >-
          {{
            lookup(
              'community.sops.sops',
              'docs/secrets/baremetal-luks.sops.yaml'
            )['disk_luks_passphrase']
          }}
   ```

2. **Génération de l'ISO**

   Réutilisez les commandes `make baremetal/seed` ou `make baremetal/fulliso`
   en pointant vers le fichier rendu précédemment.

3. **Vérifications post-installation**

   Vérifiez que l'accès SSH est limité à la clé publique, que le disque est
   chiffré (`lsblk --fs`) et que les services `ufw`, `fail2ban` et
   `unattended-upgrades` sont actifs.

## Validation et CI/CD

- Workflow `.github/workflows/build-iso.yml` : rend les fichiers Autoinstall
  pour les profils matériels ou hôtes impactés par un changement (détection
  Git native). Les modifications globales déclenchent automatiquement la
  validation complète. Les exécutions redondantes sont annulées via
  `concurrency` pour éviter de surconsommer les minutes CI. Aucun ISO ni
  artefact n'est publié : la génération se fait désormais en dehors du dépôt
  pour limiter le temps d'exécution et les contraintes de stockage.
- Workflow `.github/workflows/repository-integrity.yml` : exécute
  `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint` et `trivy fs`
  (config + secrets) uniquement si des fichiers pertinents changent.
  Le scan Trivy ne s'exécute plus sur les pull requests : il se déclenche sur
  les pushes vers `main/master`, la planification hebdomadaire (lundi 04:00
  UTC) et via `workflow_dispatch`.
- Les caches pip/npm/collections s'appuient sur des clés dérivées du contenu pour
  garantir l'idempotence.

## Sécurité et conformité

- Remplacez les clés SSH de démonstration par vos propres clés chiffrées via
  `secrets.sops.yaml`.
- Générez les mots de passe via `mkpasswd -m yescrypt` ou `openssl passwd -6`,
  puis stockez le hash uniquement dans SOPS (`password_hash`).
- Les templates appliquent BBR, `irqbalance`, `rp_filter=2` et désactivent les
  redirections ICMP sortantes.
- La CI exécute `scripts/ci/check-no-plaintext-secrets.py` pour s'assurer que
  les inventaires ne contiennent aucun secret en clair et `trivy fs` pour la
  détection de secrets accidentels.
- Configurez le secret GitHub `SOPS_AGE_KEY` (clé privée `age`) pour permettre à
  la CI de déchiffrer les fichiers SOPS. Tant que le secret reste vide, le
  workflow *Validate Bare Metal Configurations* sera automatiquement ignoré et
  aucun rendu autoinstall ne sera effectué en CI.
- Conservez les ISO produites dans un stockage contrôlé (artefacts CI, dépôt
  interne, etc.).

## Chiffrement du disque

- Le template supporte LUKS + LVM via la variable `disk_encryption`.
- Les passphrases doivent être stockées chiffrées dans
  `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.
- Suivez le guide [Chiffrement du disque système](docs/baremetal-disk-encryption.md)
  pour la procédure complète (création du secret SOPS, activation par hôte,
  tests et rotation).

## Générer une ISO hors CI

La CI s'assure uniquement que les fichiers `user-data` et `meta-data` se
génèrent correctement pour tous les équipements déclarés. Pour créer une ISO
seed ou complète sur votre poste ou dans une usine d'image dédiée :

1. **Rendre les fichiers Autoinstall**

   - Exécuter la CI sur votre branche pour vérifier la cohérence, puis générer
     localement les fichiers via `make baremetal/gen HOST=<nom_hote>` ou
     `PROFILE=<profil_matériel>`.

2. **Préparer l'ISO Ubuntu officielle** (uniquement pour l'ISO complète)

   - Télécharger `ubuntu-24.04-live-server-amd64.iso` depuis un miroir
     officiel et vérifier son empreinte.

3. **Assembler l'ISO seed**

   ```bash
   make baremetal/seed HOST=<nom_hote>
   ```

4. **Assembler l'ISO complète (optionnel)**

   ```bash
   make baremetal/fulliso HOST=<nom_hote> \
     UBUNTU_ISO=/chemin/vers/ubuntu-24.04-live-server-amd64.iso
   ```

5. **Contrôler la sortie**

   - Les fichiers générés se trouvent sous
     `baremetal/autoinstall/generated/<nom_hote>/`.
   - Vérifiez les signatures/empreintes avant toute diffusion.

## Ressources supplémentaires

- [Guide débutant](docs/getting-started-beginner.md)
- [ADR 0001 — recentrage bare metal](docs/adr/0001-focus-baremetal.md)
- [Documentation originale en anglais](README.en.md)
- [ADR 0006 — rationalisation CI GitHub Actions](docs/adr/0006-ci-rationalization.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
