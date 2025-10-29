# ubuntu-autoinstall-git

Provisionner **Ubuntu Server 24.04 LTS** hôte par hôte (ThinkCentre M710q, Dell 3020 Tiny) grâce à **Autoinstall + cloud-init (NoCloud)**, entièrement piloté par Git dans une approche GitOps.

## Table des matières
- [Vue d'ensemble](#vue-densemble)
- [Architecture GitOps](#architecture-gitops)
- [Périmètre bare metal](#périmètre-bare-metal)
- [Prérequis](#prérequis)
- [Démarrage rapide](#démarrage-rapide)
- [Profils matériels](#profils-matériels)
- [Variables d'hôte](#variables-dhôte)
- [Commandes Make disponibles](#commandes-make-disponibles)
- [Tests et validation](#tests-et-validation)
- [Intégration continue](#intégration-continue)
- [Sécurité et conformité](#sécurité-et-conformité)
- [Provisioning VPS avec Ansible](#provisioning-vps-avec-ansible)
- [Ressources supplémentaires](#ressources-supplémentaires)

## Vue d'ensemble
Ce dépôt fournit les fichiers modèles et l'automatisation nécessaires pour créer des supports d'installation Ubuntu totalement automatisés. Chaque hôte possède ses propres variables inventoriées, ce qui garantit des déploiements reproductibles et idempotents. Les ISO générées (seed ou complètes) sont archivées dans les artefacts de pipeline pour assurer l'auditabilité. Une bibliothèque de **profils matériels** dans `inventory/profiles/hardware/` permet de valider la génération d'autoinstall par modèle via la CI.

## Architecture GitOps
- **Définition déclarative** :
  - les paramètres spécifiques à chaque hôte résident dans `inventory/host_vars/<hôte>.yml` ;
  - les profils matériels standards vivent dans `inventory/profiles/hardware/<profil>.yml` et servent de référence partagée.
- **Rendu automatisé** : Ansible et Jinja2 génèrent les fichiers `user-data`/`meta-data` dans `autoinstall/generated/<hôte>/`.
  - Le playbook `ansible/playbooks/generate_autoinstall.yml` calcule dynamiquement les chemins `autoinstall/` et `inventory/host_vars/` via `{{ playbook_dir }}` pour rester fiable quel que soit le répertoire d'exécution (ex. `make gen`).
- **Distribution contrôlée** : la CI construit les ISO d'installation, stockées en artefacts et récupérées lors du déploiement.
- **Aucune intervention manuelle** : l'intégralité du flux passe par Git, CI/CD et les commandes documentées.

## Périmètre bare metal
- **Infrastructure ciblée** : ce dépôt gère exclusivement le provisioning **bare metal** (ISO seed ou complète) pour les hôtes Ubuntu Server.
- **Pas d'IaC cloud** : aucune ressource distante (Terraform, Kubernetes, secrets chiffrés) n'est gérée ici ; tout changement d'infrastructure cloud doit être traité dans un dépôt dédié.
- **Traçabilité GitOps** : chaque hôte ou profil matériel est décrit via Ansible/Jinja et suivi par la CI, ce qui assure une auditabilité complète sans scripts ad hoc.

## Prérequis
- Ubuntu 24.04 Live Server ISO officiel (pour `make fulliso`).
- Python 3.10+ et Ansible installés dans l'environnement de build.
- Outils systèmes : `mkpasswd`, `cloud-localds`, `xorriso`, `genisoimage` ou équivalents selon la distribution.
- [SOPS](https://github.com/getsops/sops) et une paire de clés [age](https://age-encryption.org/) pour chiffrer les variables sensibles.
- Clés SSH valides et un mot de passe chiffré (YESCRYPT recommandé) pour chaque hôte.

## Démarrage rapide
1. **Choisir un profil matériel (optionnel)**
   ```bash
   ls inventory/profiles/hardware
   make gen PROFILE=lenovo-m710q
   ```
   Les artefacts sont générés sous `autoinstall/generated/lenovo-m710q/`.
2. **Définir les variables de l'hôte**
   ```bash
   cp inventory/host_vars/example.yml inventory/host_vars/site-a-m710q1.yml
   $EDITOR inventory/host_vars/site-a-m710q1.yml
   ```
3. **Générer les fichiers autoinstall pour l'hôte**
   ```bash
   make gen HOST=site-a-m710q1
   ```
4. **Construire l'ISO seed (`CIDATA`)**
   ```bash
   make seed HOST=site-a-m710q1
   ```
   L'ISO est exportée dans `autoinstall/generated/site-a-m710q1/seed-site-a-m710q1.iso`.
5. **Lancer l'installation**
   - Graver l'ISO officielle d'Ubuntu sur une clé USB (USB #1).
   - Monter l'ISO seed sur une deuxième clé USB ou via une clé USB dédiée (USB #2).
   - Démarrer sur l'installateur Ubuntu, appuyer sur `e` dans GRUB et ajouter `autoinstall` à la ligne Linux.
   - L'installation est ensuite entièrement automatisée via cloud-init (NoCloud).
6. **(Optionnel) Construire une ISO complète avec autoinstall intégré**
    ```bash
    make fulliso HOST=site-a-m710q1 UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso
    ```
    Le script `scripts/make_full_iso.sh` rejoue la configuration de démarrage de l'ISO source via `xorriso` afin d'ajouter le dossier `nocloud/` sans dépendre d'`isolinux/` (flag `-boot_image any replay`).

## Profils matériels
Les profils sous `inventory/profiles/hardware/` décrivent les valeurs minimales par modèle pour valider la génération autoinstall (disque, interface réseau, clés SSH de test, etc.). Chaque fichier peut être référencé via `make gen PROFILE=<profil>` et sert de base pour définir des sites spécifiques via Ansible.

- `lenovo-m710q` : ThinkCentre M710q Tiny équipé d'un NVMe et d'un emplacement SATA 2,5". Le profil assemble les deux disques dans le même volume LVM afin d'offrir une capacité unique.
  - Optimisations : microcode Intel, `thermald`, `powertop` (service d'auto-tune) et `lm-sensors` sont préinstallés pour stabiliser les températures et l'efficacité énergétique du châssis compact.

## Variables d'hôte
Chaque fichier `inventory/host_vars/<hôte>.yml` peut contenir les paramètres suivants :

| Variable | Description |
| --- | --- |
| `hostname` | Nom d'hôte configuré pendant l'installation |
| `disk_device` | Disque système principal (ex. `/dev/nvme0n1`) |
| `additional_disk_devices` | Liste de disques supplémentaires à intégrer au VG LVM (ex. `['/dev/sda']`) |
| `netmode` | `dhcp` ou `static` |
| `nic` | Interface réseau (ex. `enp1s0`) pour IP statique |
| `ip`, `cidr`, `gw`, `dns` | Paramètres réseau statiques |
| `ssh_authorized_keys` | Liste des clés publiques autorisées |
| `password_hash` | Hash de mot de passe (YESCRYPT ou SHA512) |
| `extra_packages` | Liste additionnelle de paquets à installer (ex. optimisations matérielles) |
| `enable_powertop_autotune` | Active la création/activation du service systemd `powertop-autotune` |

## Gestion des variables et secrets partagés

- Les variables communes aux VPS vivent maintenant dans `inventory/group_vars/vps/` pour rester proches de l'inventaire GitOps.
- Les secrets sont versionnés sous forme **chiffrée** avec [SOPS](https://github.com/getsops/sops) :
  1. Copier le modèle :
     ```bash
     cp inventory/group_vars/vps/secrets.sops.yaml.example inventory/group_vars/vps/secrets.sops.yaml
     ```
  2. Ajouter votre clé publique age à `.sops.yaml` (`age1...`).
  3. Chiffrer le fichier :
     ```bash
     sops --encrypt --in-place inventory/group_vars/vps/secrets.sops.yaml
     ```
  4. Éditer le secret de façon sécurisée :
     ```bash
     sops inventory/group_vars/vps/secrets.sops.yaml
     ```

Les clés `vps_external_dns_api_token` et `vps_keycloak_admin_password` doivent être présentes dans ce fichier pour que le playbook `vps_provision.yml` aboutisse. Un échec explicite est déclenché si ces valeurs manquent.

## Commandes Make disponibles
- `make gen HOST=<nom>` : génère `user-data` et `meta-data` dans `autoinstall/generated/<nom>/`.
- `make gen PROFILE=<profil>` : génère les artefacts pour un profil matériel sous `autoinstall/generated/<profil>/`.
- `make seed HOST=<nom>` : construit `seed-<nom>.iso` (NoCloud `CIDATA`).
- `make fulliso HOST=<nom> UBUNTU_ISO=<chemin>` : construit un installateur complet avec autoinstall et boot flags.
- `make clean` : supprime les artefacts générés.

## Tests et validation
- `make lint` *(si défini)* : lancer l'éventuelle cible de linting/validation.
- `ansible-lint` : valider les rôles et playbooks.
- `yamllint inventory ansible autoinstall` : vérifier la syntaxe YAML.

## Intégration continue
- La pipeline GitHub Actions définie dans `.github/workflows/build-iso.yml` rend désormais les fichiers autoinstall **par modèle matériel** (`PROFILE`) pour valider le processus sans dépendance aux sites.
- Pour lancer manuellement : **Actions → Build Host ISOs → Run workflow** et, si besoin, surcharger `UBUNTU_ISO_URL`.
  - Par défaut, la CI télécharge l'image depuis `https://old-releases.ubuntu.com/releases/24.04/ubuntu-24.04-live-server-amd64.iso` pour garantir la disponibilité dans le temps. Un cache ISO (`.cache/`) évite les téléchargements répétés.
- Les artefacts générés sont regroupés par profil matériel pour simplifier la traçabilité.

## Sécurité et conformité
- Toujours remplacer les clés SSH de démonstration par des clés réelles spécifiques.
- Générer des mots de passe via `mkpasswd -m yescrypt` (paquet `whois`) ou `openssl passwd -6` pour SHA512.
- Les configurations réseau appliquent BBR, `rp_filter=2`, désactivent les redirections ICMP et activent `irqbalance`.
- Les artefacts ISO publiés dans la CI doivent être stockés dans un espace contrôlé (ex. artefacts GitHub Actions).

## Provisioning VPS avec Ansible
Pour finaliser la configuration d'un VPS après installation :

```bash
ansible-playbook -i inventory/hosts.yml ansible/playbooks/vps_provision.yml -u ubuntu --become
```

Définir les variables via `inventory/group_vars/vps/` (voir section précédente) ou, pour des tests ponctuels, l'option `-e`.

Avant exécution :

```bash
ansible-galaxy collection install -r ansible/collections/requirements.yml
```

## Ressources supplémentaires
- [Documentation originale en anglais](README.en.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)

