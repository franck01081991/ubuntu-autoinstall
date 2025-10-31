# Ubuntu Autoinstall

Chaîne **GitOps** dédiée à la création d'ISO Ubuntu Server 24.04 LTS entièrement
automatisées grâce à **Autoinstall + cloud-init (NoCloud)**. Chaque image est
rendue à partir de fichiers versionnés et générée par la CI pour garantir la
reproductibilité et l'auditabilité.

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
- [Ressources supplémentaires](#ressources-supplémentaires)

## Vue d'ensemble

Le dépôt concentre tous les éléments nécessaires pour construire deux variantes
principales d'ISO Autoinstall :

- **ISO seed (`CIDATA`)** : embarque uniquement `user-data` et `meta-data` à
  monter aux côtés de l'ISO officielle.
- **ISO complète** : intègre les fichiers NoCloud directement dans l'image
  Ubuntu Live Server.

Aucun autre périmètre (provisioning applicatif, overlay réseau, etc.) n'est
couvert ici ; les répertoires hérités demeurent dans l'historique Git mais ne
sont plus documentés.

## Approche GitOps pour les ISO

- **Définition déclarative** : chaque hôte ou profil est décrit par YAML sous
  `baremetal/inventory/`. Les valeurs sont versionnées et relues via revue de
  code.
- **Rendu automatisé** : Ansible + Jinja2 produisent les fichiers `user-data` et
  `meta-data` dans `baremetal/autoinstall/generated/<cible>/`.
- **Construction reproductible** : des scripts idempotents sous
  `baremetal/scripts/` créent les ISO seed et complètes à partir des artefacts
  générés.
- **Distribution contrôlée** : la CI publie les ISO en artefacts et sert de
  référence unique pour les déploiements.

## Structure du dépôt

```text
baremetal/
├── ansible/            # Playbooks de rendu Autoinstall NoCloud
├── autoinstall/        # Templates Jinja2 + artefacts générés
├── inventory/          # Host vars et profils matériels
└── scripts/            # Génération ISO seed/full
ansible/                # Dépendances et tâches partagées
scripts/install-sops.sh # Installation SOPS (Linux amd64)
```

Les dossiers non listés sont conservés pour compatibilité mais ne font pas
partie du flux ISO documenté.

## Inventaire et templates

- **Profils matériels** (`baremetal/inventory/profiles/hardware/`) : valeurs
  minimales par modèle (disque, interface réseau, paquets optimisés). Servez-vous
  en comme point de départ.
- **Variables hôte** (`baremetal/inventory/host_vars/<hôte>.yml`) : définissent
  les identifiants, périphériques et paramètres réseau propres à un nœud.
- **Templates** (`baremetal/autoinstall/templates/`) : décrivent le `user-data`
  et `meta-data` communs. Ne modifiez qu'en cas d'évolution produit.

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
   cp baremetal/inventory/host_vars/example.yml \
     baremetal/inventory/host_vars/site-a-m710q1.yml
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1.yml
   ```

   Personnalisez `hostname`, `hardware_profile`, le disque cible et, le cas
   échéant, l'adressage réseau statique ou les paquets supplémentaires.

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

## Validation et CI/CD

- Workflow `.github/workflows/build-iso.yml` : génère les artefacts Autoinstall
  par profil matériel, construit les ISO seed et complètes, publie les artefacts
  et purge les versions précédentes pour rester dans les quotas GitHub Actions.
- Workflow `.github/workflows/repository-integrity.yml` : exécute `yamllint`,
  `ansible-lint`, `shellcheck`, `markdownlint` et `trivy fs` (config + secrets)
  pour conserver un dépôt propre et sécurisé.
- Les caches pip/npm/collections s'appuient sur des clés dérivées du contenu pour
  garantir l'idempotence.

## Sécurité et conformité

- Remplacez les clés SSH de démonstration par vos propres clés.
- Générez les mots de passe via `mkpasswd -m yescrypt` ou `openssl passwd -6`.
- Les templates appliquent BBR, `irqbalance`, `rp_filter=2` et désactivent les
  redirections ICMP sortantes.
- Conservez les ISO produites dans un stockage contrôlé (artefacts CI, dépôt
  interne, etc.).

## Ressources supplémentaires

- [Guide débutant](docs/getting-started-beginner.md)
- [Documentation originale en anglais](README.en.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
