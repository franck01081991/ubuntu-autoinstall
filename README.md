# Ubuntu Autoinstall

Bienvenue ! Ce dépôt vous aide à fabriquer des images d'installation Ubuntu Server 24.04 LTS en suivant une approche **GitOps**. Tout est défini dans Git, vérifié par la CI/CD, puis reproduit à la demande sur votre poste ou dans une usine d'image. Aucune opération manuelle en production : on automatise, on révise, on rejoue.

> 🙋 Première visite ? Commencez par le [guide débutant](docs/getting-started-beginner.md) pour suivre un cas concret pas à pas.

---

## Pourquoi ce projet ?

- **Automatiser vos installations bare metal** : les fichiers Autoinstall (`user-data` et `meta-data`) sont générés à partir de modèles Jinja2 et de variables YAML.
- **Garder un historique clair** : chaque changement (inventaire, template, scripts) passe par revue de code et reste traçable.
- **Rester reproductible** : la CI s'assure que tout se rend correctement avant d'intégrer une modification.

## Ce que vous allez produire

| Type d'image | À quoi ça sert ? | Comment l'obtenir ? |
|--------------|------------------|----------------------|
| **ISO seed (`CIDATA`)** | Un mini ISO à monter à côté de l'ISO officielle Ubuntu. | `make baremetal/seed HOST=<nom>` |
| **ISO complète** | L'ISO Ubuntu Live Server qui embarque directement les fichiers NoCloud. | `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=/chemin/ubuntu.iso` |

Les composants historiques (provisioning applicatif, VPS, etc.) ont été retirés pour se concentrer uniquement sur la chaîne bare metal. Ils restent disponibles dans l'historique Git si besoin.

## Les bases à connaître

- **Autoinstall + cloud-init (NoCloud)** : mécanisme officiel d'Ubuntu pour automatiser l'installation.
- **GitOps** : toute configuration vit dans le dépôt. Les changements sont revus, testés, puis synchronisés vers les environnements.
- **SOPS + age** : secrets chiffrés par fichier. La CI peut les déchiffrer grâce à la clé stockée côté plateforme (GitHub Actions par défaut).

## Prérequis rapides

1. ISO officielle *Ubuntu 24.04 Live Server* (fichier `.iso`).
2. Outils côté poste : `python3`, `ansible-core`, `xorriso`, `mkpasswd`, `sops`, `age`.
3. Accès Git avec revue de code (aucun commit direct sur la branche de production).

Vérifiez votre environnement avec :

```bash
make doctor
```

La commande alerte sur les dépendances manquantes et rappelle les linters utilisés par la CI (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`).

## Structure du dépôt

```text
baremetal/
├── ansible/            # Playbooks pour rendre Autoinstall
├── autoinstall/        # Templates Jinja2 + sorties générées
├── inventory/          # Variables d'hôtes et profils matériels
└── scripts/            # Génération des ISO seed/full
ansible/                # Rôles et collections partagés
docs/                   # Guides utilisateurs, ADR et secrets chiffrés
scripts/install-sops.sh # Installation rapide de SOPS (Linux amd64)
```

Gardez ce découpage : il garantit la reproductibilité et l'idempotence.

## Comment démarrer ?

1. **Copier un exemple de variables**
   ```bash
   cp -R baremetal/inventory/host_vars/example \
     baremetal/inventory/host_vars/mon-premier-hote
   ```

2. **Éditer les variables claires**
   - Fichier : `baremetal/inventory/host_vars/mon-premier-hote/main.yml`
   - Renseignez `hostname`, `profile`, réseau, disque, etc.

3. **Chiffrer les secrets**
   ```bash
   SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
     sops baremetal/inventory/host_vars/mon-premier-hote/secrets.sops.yaml
   ```
   Stockez-y uniquement des valeurs sensibles (`password_hash`, `ssh_authorized_keys`, tokens). Les passphrases LUKS se déclarent dans `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.

4. **Générer l'autoinstall**
   ```bash
   make baremetal/gen HOST=mon-premier-hote
   ```
   Les fichiers `user-data` et `meta-data` apparaissent sous `baremetal/autoinstall/generated/mon-premier-hote/`.

5. **Créer l'ISO seed**
   ```bash
   make baremetal/seed HOST=mon-premier-hote
   ```

6. **Créer l'ISO complète (optionnel)**
   ```bash
   make baremetal/fulliso HOST=mon-premier-hote \
     UBUNTU_ISO=/chemin/vers/ubuntu-24.04-live-server-amd64.iso
   ```

> 💡 Pensez à valider votre branche via la CI avant d'utiliser une ISO sur un serveur réel.

## Aller plus loin

### Inventaire et templates

- **Profils matériels** : `baremetal/inventory/profiles/hardware/` fournit des bases par type de machine (disques, NIC, paquets). Dupliquez puis adaptez :
  - `lenovo-m710q` : ThinkCentre M710q (NVMe principal + SATA secondaire).
  - `raspberry-pi-4b-sd` : Raspberry Pi 4 Model B ARM64 sur carte SD (`/dev/mmcblk0`, miroir `ports.ubuntu.com`).
- **Variables d'hôte** : chaque serveur possède un dossier `baremetal/inventory/host_vars/<hote>/` avec `main.yml` (clair) + `secrets.sops.yaml` (chiffré).
- **Inventaire Ansible** : `baremetal/inventory/hosts.yml` est volontairement vide. Ajoutez uniquement les hôtes que vous voulez rendre.
- **Templates** : `baremetal/autoinstall/templates/` décrit la structure commune de `user-data`/`meta-data`. Modifiez-les uniquement si le produit évolue.
- **Profil sécurisé** : `baremetal/autoinstall/secure-ubuntu-22.04.yaml` propose un système durci (LUKS+LVM, UFW, durcissement SSH). La passphrase LUKS est injectée dynamiquement par la CI via `SOPS_DECRYPTED_DISK_PASSPHRASE`.
- **Paramètres avancés** :
  - `apt_primary_arches` ajuste l'architecture APT rendue par `user-data` (par défaut `['amd64']`).
  - `apt_primary_uri` pointe vers le miroir Ubuntu (par défaut `http://archive.ubuntu.com/ubuntu`).
  - `storage_swap_size` personnalise la taille du swap (par défaut `0`).
  - `storage_config_override` remplace entièrement la configuration disque générée par défaut (utile pour ARM/Raspberry Pi).

### Exemple d'injection GitOps d'une passphrase LUKS

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

Ensuite, lancez `make baremetal/seed` ou `make baremetal/fulliso` en pointant vers le fichier rendu.

### Après installation

1. Vérifiez que l'accès SSH repose bien sur votre clé publique.
2. Confirmez le chiffrement avec `lsblk --fs`.
3. Assurez-vous que `ufw`, `fail2ban` et `unattended-upgrades` sont actifs.

## Validation, CI/CD et sécurité

- **Workflows GitHub Actions**
  - `.github/workflows/build-iso.yml` : rend automatiquement les fichiers Autoinstall impactés par une PR. Les exécutions redondantes sont annulées (`concurrency`).
  - `.github/workflows/repository-integrity.yml` : exécute `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint` et `trivy fs`. Le scan Trivy échoue sur toute branche (PR incluses) en cas de faille `HIGH`/`CRITICAL`.
  - `.github/workflows/secret-scanning.yml` : télécharge le binaire `gitleaks` (`v8.16.1`) dans `${RUNNER_TEMP}`, l'ajoute au `PATH` puis exécute `gitleaks detect --config gitleaks.toml --report-format sarif --report-path gitleaks.sarif --redact --exit-code 2` à chaque push/PR, sur déclenchement manuel ou via le cron hebdomadaire (lundi 05:00 UTC). Les rapports SARIF sont importés dans Code Scanning hors PR.
- **Détection de secrets** : `scripts/ci/check-no-plaintext-secrets.py` vérifie qu'aucun secret ne fuit dans l'inventaire. `trivy fs` et `gitleaks` complètent le contrôle.
- **Clé `SOPS_AGE_KEY`** : ajoutez-la dans les secrets GitHub pour que la CI puisse déchiffrer. Sans elle, le workflow *Validate Bare Metal Configurations* est ignoré.
- **Stockage des ISO** : exportez-les vers un stockage maîtrisé (dépôt interne, artefacts chiffrés, etc.).

## Commandes Make utiles

| Commande | Usage |
|----------|-------|
| `make doctor` | Vérifie les dépendances et linters attendus par la CI. |
| `make baremetal/gen HOST=<nom>` | Rend `user-data`/`meta-data` pour un hôte. |
| `make baremetal/seed HOST=<nom>` | Crée une image CIDATA minimale. |
| `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` | Construit une ISO autonome. |
| `make baremetal/clean` | Supprime les artefacts générés. |
| `make lint` | Lance tous les linters (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`). |
| `make secrets-scan` | Exécute `gitleaks detect --config gitleaks.toml --report-format sarif --report-path gitleaks.sarif --redact --exit-code 2`, identique au workflow CI. |

## Chiffrement disque

- Activez-le via `disk_encryption.enabled: true` dans vos variables d'hôte.
- Stockez les passphrases chiffrées dans `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.
- Suivez le guide [Chiffrement du disque système](docs/baremetal-disk-encryption.md) pour créer et faire tourner les secrets.

## Générer une ISO hors CI

1. Vérifiez votre branche via la CI.
2. Rendez les fichiers avec `make baremetal/gen HOST=<nom>` ou `PROFILE=<profil>`.
3. Téléchargez et vérifiez l'ISO officielle 24.04 (pour l'ISO complète).
4. Lancez `make baremetal/seed` et/ou `make baremetal/fulliso`.
5. Contrôlez les fichiers produits dans `baremetal/autoinstall/generated/<nom>/` et vérifiez leurs empreintes avant diffusion.

## Ressources utiles

- [Guide débutant](docs/getting-started-beginner.md)
- [ADR 0001 — recentrage bare metal](docs/adr/0001-focus-baremetal.md)
- [ADR 0006 — rationalisation CI GitHub Actions](docs/adr/0006-ci-rationalization.md)
- [Documentation anglaise](README.en.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Datasource Cloud-init NoCloud](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)

---

Ce dépôt applique des pratiques GitOps strictes : idempotence, sécurité des secrets, déploiements tirés par la plateforme (Flux/Argo CD). Toute nouvelle contribution doit respecter ces principes et mettre à jour la documentation ou un ADR si l'architecture évolue.
