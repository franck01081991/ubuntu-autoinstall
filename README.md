# Ubuntu Autoinstall

Ce dépôt fournit **une usine GitOps** pour créer des ISO Ubuntu Server 24.04 LTS
prêtes à déployer sur des serveurs bare metal. Tout passe par Git : on modifie,
on révise, on teste, puis la CI reconstruit les artefacts. Aucune action
manuelle n'est tolérée en production.

> 🆕 Première prise en main ? Enchaînez directement les étapes de la section
> ["Démarrage express"](#démarrage-express).
>
> 🛠️ Besoin d'un aide-mémoire une fois formé·e ? Gardez la
> [fiche mémo technicien](docs/technician-cheatsheet.md) et le
> [guide de dépannage](docs/troubleshooting.md) à proximité.

---

## Ce dépôt en bref

- **Ce que l'on produit** :
  - un ISO *seed* (NoCloud/CIDATA) à monter en plus de l'ISO officielle ;
  - un ISO complet qui embarque l'installateur Ubuntu Live Server + vos fichiers Autoinstall.
- **Comment c'est géré** :
  - modèles Jinja2, inventaire YAML et secrets SOPS versionnés dans `baremetal/` ;
  - CI GitHub Actions qui relance les linters, regénère les Autoinstall et scanne les secrets ;
  - livraison via pipelines GitOps (Flux ou Argo CD) qui tirent les artefacts depuis Git.
- **Ce que l'on garantit** :
  - reproductibilité (idempotence des cibles `make`),
  - traçabilité (commits + PR revues),
  - sécurité (SOPS/age, scans Trivy et Gitleaks, aucun secret en clair).

## Démarrage express

Suivez ces sept étapes pour produire une ISO seed prête à l'emploi :

1. **Cloner et se placer dans le dépôt**
   ```bash
   git clone git@github.com:example/ubuntu-autoinstall.git
   cd ubuntu-autoinstall
   ```
2. **Vérifier la station de travail**
   ```bash
   make doctor
   ```
   Corrigez toute dépendance manquante (`python3`, `ansible-core`, `xorriso`,
   `mkpasswd`, `sops`, `age`, `cloud-init`).
3. **Initialiser l'hôte cible**
   ```bash
   make baremetal/host-init HOST=site-a-m710q1 PROFILE=lenovo-m710q
   ```
   La commande crée `host_vars/`, alimente `hosts.yml` et reste idempotente.
   Le fichier `baremetal/inventory/host_vars/<HOST>/main.yml` généré contient
   immédiatement `hostname: <HOST>` et `hardware_profile: <PROFILE>`, ce qui
   évite toute valeur placeholder à corriger manuellement.
4. **Découvrir automatiquement le matériel**
   ```bash
   make baremetal/discover HOST=site-a-m710q1
   ```
   Le playbook `discover_hardware.yml` collecte `ansible_facts`, `lsblk` et
   `ip -j link`, puis écrit un cache JSON local dans `.cache/discovery/`.
   Servez-vous-en pour pré-remplir vos profils matériels avant de les
   versionner.
5. **Déclarer les variables et secrets**
   - Éditez `baremetal/inventory/host_vars/site-a-m710q1/main.yml` (profil
     matériel, réseau, disques).
   - Chiffrez les secrets :
     ```bash
     SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
       sops baremetal/inventory/host_vars/site-a-m710q1/secrets.sops.yaml
     ```
6. **Générer les fichiers Autoinstall**
   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```
   Les fichiers `user-data` et `meta-data` apparaissent sous
   `baremetal/autoinstall/generated/site-a-m710q1/`.
7. **Construire l'ISO souhaitée**
   ```bash
   make baremetal/seed HOST=site-a-m710q1
   make baremetal/fulliso HOST=site-a-m710q1 \
     UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso   # optionnel
   ```

Une fois la PR fusionnée, vos pipelines internes tirent les artefacts
validés. Ne déployez jamais un ISO qui n'a pas été reconstruit par la CI.

## Workflow GitOps complet

| Phase | Objectif | Commandes clefs | Point d'attention |
|-------|----------|-----------------|-------------------|
| Préparation | Vérifier l'environnement | `make doctor` | Installez les binaires manquants avant de poursuivre. |
| Inventaire | Créer/mettre à jour `host_vars` | `make baremetal/host-init` | Idempotent : relancez après toute suppression ou ajout. |
| Découverte | Capturer les faits matériels | `make baremetal/discover` | Cache JSON non versionné sous `.cache/discovery/`. |
| Configuration | Définir variables & secrets | `$EDITOR main.yml`, `sops secrets.sops.yaml` | Secrets uniquement via `sops` + `age`. |
| Validation | Vérifier rendu & lint | `make baremetal/gen`, `make lint`, `make secrets-scan` | `make lint` exécute `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`. |
| Construction | Produire ISO | `make baremetal/seed`, `make baremetal/fulliso` | Téléchargez l'ISO officielle avant la version complète. |
| Livraison | Soumettre via PR | `git status`, `git commit`, `git push` | Décrivez l'objectif, les tests, le plan de rollback. |

### Structure à connaître

```text
baremetal/
├── ansible/            # Rôles et tâches partagés (templates, scripts)
├── autoinstall/        # Templates Jinja2 + rendus générés
├── inventory/          # Profils matériels + variables d'hôtes chiffrées
└── scripts/            # Génération ISO et assistants
ansible/                # Collections et dépendances Ansible mutualisées
docs/                   # Guides utilisateurs, ADR, secrets chiffrés
scripts/install-sops.sh # Installation simplifiée de SOPS (Linux amd64)
```

Respectez ce découpage pour rester compatible avec la CI et l'usine GitOps.

### Commandes Make utiles

| Usage | Commande | Commentaire |
|-------|----------|-------------|
| Vérifier l'environnement | `make doctor` | Contrôle dépendances et rappelle les linters attendus. |
| Initialiser un hôte | `make baremetal/host-init HOST=<nom> PROFILE=<profil>` | Crée `host_vars/` + met à jour `inventory/hosts.yml`. |
| Regénérer Autoinstall | `make baremetal/gen HOST=<nom>` | Produit `user-data` / `meta-data` à versionner. |
| Construire un ISO seed | `make baremetal/seed HOST=<nom>` | Génère `seed-<nom>.iso` idempotent. |
| Construire un ISO complet | `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` | Intègre l'installateur officiel Ubuntu. |
| Découvrir le matériel | `make baremetal/discover HOST=<nom>` | Alimente `.cache/discovery/<nom>.json` via Ansible. |
| Lancer les linters | `make lint` | `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`. |
| Scanner les secrets | `make secrets-scan` | `gitleaks detect --config gitleaks.toml --exit-code 2`. |
| Inspecter l'inventaire | `make baremetal/list` | Résumé hôtes + profils matériels (`FORMAT=json` pour une sortie machine). |
| Nettoyer les artefacts | `make baremetal/clean` | Supprime les rendus locaux. |

### Assistant interactif

Pour guider un·e technicien·ne étape par étape :

```bash
python3 baremetal/scripts/iso_wizard.py
```

Le script vérifie l'environnement, synchronise le dépôt, initie les hôtes,
construit les ISO et nettoie les artefacts en s'appuyant uniquement sur les
cibles `make` (idempotence garantie). Les profils matériels proposés
correspondent désormais aux manifestes `*.yml`/`*.yaml` présents dans
`baremetal/inventory/profiles/hardware/`. Pour préparer un nouveau matériel,
collectez d'abord les faits via `make baremetal/discover`, puis nourrissez vos
profils à partir du cache JSON généré.

## CI/CD, sécurité et conformité

- **Workflows GitHub Actions**
  - `build-iso.yml` : régénère les Autoinstall touchés par une PR.
  - `repository-integrity.yml` : lance `yamllint`, `ansible-lint`, `shellcheck`,
    `markdownlint`, `trivy fs` et contrôle la cohérence de l'inventaire.
  - `secret-scanning.yml` : exécute `gitleaks detect` (push, PR, cron, manuel).
- **Gestion des secrets**
  - Secrets chiffrés avec `sops` + `age` (clé privée stockée côté plateforme CI).
  - `scripts/ci/check-no-plaintext-secrets.py` vérifie qu'aucune donnée sensible
    n'est commitée en clair.
- **Livraison GitOps**
  - Les artefacts produits par la CI sont consommés par Flux/Argo CD.
  - Préparez un plan de rollback (tag ou commit précédent) avant diffusion sur
    un nouvel environnement.
- **Stockage**
  - Archivez les ISO validées dans un stockage maîtrisé et chiffré.

## Ressources complémentaires

- [Guide débutant pas à pas](docs/getting-started-beginner.md)
- [Fiche mémo technicien](docs/technician-cheatsheet.md)
- [Partitionnement ANSSI et disques chiffrés](docs/baremetal-partitioning.md)
- [Chiffrement disque (SOPS)](docs/baremetal-disk-encryption.md)
- [ADR 0001 — recentrage bare metal](docs/adr/0001-focus-baremetal.md)
- [ADR 0006 — rationalisation CI](docs/adr/0006-ci-rationalization.md)
- [ADR 0009 — partitionnement ANSSI](docs/adr/0009-anssi-disk-layout.md)
- [ADR 0011 — inventaire matériel automatisé](docs/adr/0011-automated-hardware-inventory.md)
- [Guide de dépannage](docs/troubleshooting.md)
- [Documentation anglaise](README.en.md)

---

Toute contribution doit rester **idempotente**, documentée et validée par la
CI. Mettez à jour cette documentation ou rédigez un ADR si vous modifiez
l'architecture de la chaîne GitOps.
Pour intégrer l'inventaire bare metal dans un pipeline d'automatisation, vous
pouvez demander une sortie JSON. Exemple :

```bash
make baremetal/list FORMAT=json
```

Le script sous-jacent accepte également `hosts` ou `profiles` pour ne récupérer
qu'un extrait spécifique :

```bash
make baremetal/list-hosts FORMAT=json
make baremetal/list-profiles FORMAT=json
```

Ces commandes restent idempotentes : la sortie reflète uniquement les fichiers
`baremetal/inventory` versionnés.
