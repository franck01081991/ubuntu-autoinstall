# Ubuntu Autoinstall

Ce dépôt fournit **une usine GitOps** pour créer des ISO Ubuntu Server 24.04 LTS
prêtes à déployer sur des serveurs bare metal. Tout passe par Git : on modifie,
on révise, on teste et l'automatisation interne (Make + Ansible) regénère les
artefacts. Aucune action manuelle n'est tolérée en production.

> 🆕 Première prise en main ? Enchaînez directement les étapes de la section
> ["Démarrage express"](#démarrage-express).
>
> 🛠️ Besoin d'un aide-mémoire une fois formé·e ? Gardez la
> [fiche mémo technicien](docs/technician-cheatsheet.md) et le
> [guide de dépannage](docs/troubleshooting.md) à proximité.
>
> 🔐 Besoin d'un rappel sur les secrets ? Consultez le
> [guide simplifié SOPS + age](docs/sops-age-guide.md).

---

## Ce dépôt en bref

- **Ce que l'on produit** :
  - un ISO *seed* (NoCloud/CIDATA) à monter en plus de l'ISO officielle ;
  - un ISO complet qui embarque l'installateur Ubuntu Live Server + vos fichiers Autoinstall.
- **Comment c'est géré** :
  - modèles Jinja2 et inventaire de référence versionnés dans `baremetal/` ;
  - overlay local `baremetal/inventory-local/` (gitignoré) pour les variables d'hôte et secrets chiffrés ;
  - validations locales orchestrées par `make lint`, `make baremetal/gen` et `make secrets-scan` ;
  - livraison via pipelines GitOps (Flux ou Argo CD) qui tirent les artefacts depuis Git.
- **Ce que l'on garantit** :
  - reproductibilité (idempotence des cibles `make`),
  - traçabilité (commits + PR revues),
  - sécurité (SOPS/age, scans Trivy et Gitleaks, aucun secret en clair).

### Glossaire rapide

| Terme | Signification | Pourquoi c'est important ? |
|-------|---------------|-----------------------------|
| **ISO seed** | Image minimale contenant `user-data` et `meta-data` cloud-init. | Permet d'automatiser une installation Ubuntu en gardant l'ISO officielle intacte. |
| **ISO complète** | ISO Ubuntu Live Server + vos fichiers Autoinstall intégrés. | Pratique pour les technicien·ne·s sans réseau ou sans seconde clé USB. |
| **Autoinstall** | Fichiers `user-data` / `meta-data` générés depuis vos templates. | Décrit comment configurer l'hôte (réseau, partitions, utilisateurs). |
| **Idempotent** | Une commande peut être relancée sans effet de bord. | Garantit que la chaîne GitOps reste prédictible et sûre. |
| **SOPS + age** | Couple outil + format de chiffrement pour secrets YAML. | Assure que les données sensibles ne sortent jamais en clair de Git. |

## Démarrage express

Cette section condense tout le nécessaire pour produire une ISO *seed*
autonome. Elle complète le [guide débutant détaillé](docs/getting-started-beginner.md).

### Avant de commencer

- Poste Linux avec `python3`, `ansible-core`, `xorriso`, `mkpasswd`, `sops`,
  `age` et `cloud-init`. Lancer `make doctor` listera tout manque.
- Accès Git SSH au dépôt (clé configurée côté forge).
- Une clé `age` (de test via `./scripts/bootstrap-demo-age-key.sh`, ou votre clé
  d'équipe référencée dans `.sops.yaml`).

> 💡 **Astuce** : les scripts `./scripts/install-sops.sh` et
> `./scripts/install-age.sh` (Linux amd64) sont idempotents. Relancez-les pour
> mettre à jour ou réparer une installation.
>
> 📁 **Inventaire local** : le dossier `baremetal/inventory-local/` est ignoré
> par Git (`.gitignore`). Synchronisez-le via un stockage sécurisé (Vault,
> chiffrement de disque, partage chiffré) et recréez-le dans la CI/CD avant les
> tests.

### Parcours en 7 étapes

| # | Action | Ce que vous obtenez | Commandes |
|---|--------|---------------------|-----------|
| 1 | **Cloner le dépôt** | Répertoire de travail local | `git clone … && cd ubuntu-autoinstall` |
| 2 | **Contrôler la station** | Dépendances validées | `make doctor` |
| 3 | **Initialiser l'hôte** | Dossier local `inventory-local/host_vars/<HOST>/` + entrée dans `inventory-local/hosts.yml` | `make baremetal/host-init HOST=<HOST> PROFILE=<PROFIL>` |
| 4 | **Découvrir le matériel** | Cache JSON non versionné `.cache/discovery/<HOST>.json` | `make baremetal/discover HOST=<HOST>` |
| 5 | **Déclarer variables & secrets** | Fichiers clairs + secrets chiffrés (hors Git) | Éditer `baremetal/inventory-local/host_vars/<HOST>/main.yml`, chiffrer `secrets.sops.yaml` (voir le [guide des variables](docs/autoinstall-variables.md)) |
| 6 | **Générer Autoinstall** | `meta-data` + `user-data` prêts à relire | `make baremetal/gen HOST=<HOST>` |
| 7 | **Construire l'ISO** | ISO seed, ISO complète ou ISO multi-hôtes | `make baremetal/seed HOST=<HOST>`<br>`make baremetal/fulliso HOST=<HOST> UBUNTU_ISO=/chemin/iso`<br>`make baremetal/multiiso HOSTS="<H1> <H2>" UBUNTU_ISO=/chemin/iso NAME=site-a` |

### Détails complémentaires

- `make baremetal/host-init` est idempotent : relancez-le si vous supprimez un
  dossier ou ajustez un profil matériel.
- Pour chiffrer vos secrets, positionnez `SOPS_AGE_KEY_FILE` si besoin puis
  lancez `sops baremetal/inventory-local/host_vars/<HOST>/secrets.sops.yaml`.
  La procédure détaillée est décrite dans le
  [guide SOPS + age](docs/sops-age-guide.md).
- Après `make baremetal/gen`, relisez `baremetal/autoinstall/generated/<HOST>/user-data`
  pour confirmer les sections sensibles (`users`, `late-commands`, etc.).
- `make baremetal/fulliso` nécessite l'ISO officielle Ubuntu téléchargée
  manuellement ; la variable `UBUNTU_ISO` doit pointer vers ce fichier.
- `make baremetal/multiiso` agrège plusieurs hôtes rendus dans un seul ISO avec menu GRUB ; passez `HOSTS="h1 h2"` et `NAME=<artefact>` pour personnaliser l'entrée par défaut.
- Consultez [docs/multi-host-iso.md](docs/multi-host-iso.md) pour la procédure complète multi-hôtes.
- L'ISO complète générée injecte automatiquement `autoinstall ds=nocloud;s=/cdrom/nocloud/`
  dans les chargeurs GRUB (UEFI) **et** ISOLINUX (BIOS) afin de démarrer l'installation
  sans intervention.
- Le gabarit GRUB par défaut (`baremetal/autoinstall/grub/default.cfg`) est versionné.
  Modifiez-le si vous devez adapter l'entrée `Auto Install Ubuntu Server`.

Une fois vos validations locales terminées et la PR fusionnée, vos pipelines
GitOps reconstruisent les artefacts de référence. Pensez à regénérer les ISO
avant de demander une revue afin que les diffs soient à jour.

### Automatisation Ansible au premier démarrage

Chaque hôte installé active désormais un service `firstboot-ansible.service`
qui lance un playbook depuis un dépôt Git externe juste après le premier
redémarrage. Le template `baremetal/autoinstall/templates/user-data.j2` installe
`git`, `ansible` et `python3-apt`, rend le script `/root/firstboot-ansible.sh`
et enregistre un marqueur (`/var/lib/firstboot-ansible.done`) pour garantir
l'idempotence.

- Configurez le dépôt cible via `ansible_repo_url` dans
  `baremetal/inventory-local/host_vars/<HÔTE>/main.yml`. Valeur par défaut :
  `https://github.com/franck01081991/infra-ansible.git`.
- Ajustez la portée d'inventaire avec `ansible_inventory_limit` (défaut :
  `hostname`). La commande exécutée est :

  ```bash
  ansible-playbook -i inventory/hosts.ini ansible/site.yml --limit "<valeur>" -c local
  ```

Pour un dépôt privé SSH, injectez une clé dédiée depuis un secret SOPS puis
remplacez l'URL par `git@github.com:ORG/REPO.git`. Exemple dans
`host_vars/<HÔTE>/main.yml` et `secrets.sops.yaml` :

```yaml
# host_vars/<HÔTE>/main.yml
ansible_repo_url: git@github.com:example/infra-ansible.git
```

```yaml
# host_vars/<HÔTE>/secrets.sops.yaml
cloud_init_private_keys:
  infra_ansible: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    (clé chiffrée via SOPS)
    -----END OPENSSH PRIVATE KEY-----
```

Ajoutez ensuite un bloc `write_files` supplémentaire (via un profil ou une
commande Jinja) qui restitue la clé sous `/root/.ssh/id_ed25519_infra_ansible`
avec les permissions `0600`. Exemple minimal :

```yaml
    write_files:
      - path: /root/.ssh/id_ed25519_infra_ansible
        permissions: '0600'
        owner: root:root
        content: "{{ cloud_init_private_keys.infra_ansible }}"
```

Référez-vous à SOPS pour chiffrer le secret.

## Workflow GitOps complet

| Phase | Objectif | Commandes clefs | Point d'attention |
|-------|----------|-----------------|-------------------|
| Préparation | Vérifier l'environnement | `make doctor` | Installez les binaires manquants avant de poursuivre. |
| Inventaire | Créer/mettre à jour `host_vars` | `make baremetal/host-init` | Idempotent : relancez après toute suppression ou ajout. |
| Découverte | Capturer les faits matériels | `make baremetal/discover` | Cache JSON non versionné sous `.cache/discovery/`. |
| Configuration | Définir variables & secrets | `$EDITOR baremetal/inventory-local/host_vars/<nom>/main.yml`, `sops baremetal/inventory-local/host_vars/<nom>/secrets.sops.yaml` | Secrets uniquement via `sops` + `age`. |
| Validation | Vérifier rendu & lint | `make baremetal/gen`, `make lint`, `make secrets-scan` | `make lint` exécute `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`. |
| Construction | Produire ISO | `make baremetal/seed`, `make baremetal/fulliso`, `make baremetal/multiiso` | Téléchargez l'ISO officielle avant la version complète. |
| Livraison | Soumettre via PR | `git status`, `git commit`, `git push` | Décrivez l'objectif, les tests, le plan de rollback. |

### Structure à connaître

```text
baremetal/
├── ansible/            # Rôles et tâches partagés (templates, scripts)
├── autoinstall/        # Templates Jinja2 + rendus générés
├── inventory/          # Profils matériels + exemples versionnés
├── inventory-local/    # Variables d'hôtes + secrets chiffrés (gitignorés)
└── scripts/            # Génération ISO et assistants
ansible/                # Collections et dépendances Ansible mutualisées
docs/                   # Guides utilisateurs, ADR, secrets chiffrés
scripts/install-sops.sh # Installation simplifiée de SOPS (Linux amd64)
scripts/install-age.sh  # Installation simplifiée de age (Linux amd64)
```

Respectez ce découpage pour rester compatible avec l'usine GitOps.

### Commandes Make utiles

| Usage | Commande | Commentaire |
|-------|----------|-------------|
| Vérifier l'environnement | `make doctor` | Contrôle dépendances et rappelle les linters attendus. |
| Initialiser un hôte | `make baremetal/host-init HOST=<nom> PROFILE=<profil>` | Crée `inventory-local/host_vars/` + met à jour `inventory-local/hosts.yml`. |

> ℹ️ Depuis l'assistant ISO et la CLI, la variable d'environnement `PROFILE` peut
> pointer soit vers un profil matériel (`inventory/profiles/hardware/`), soit
> vers un hôte (`inventory-local/host_vars/<HOST>/`). Dans ce second cas, les tâches
> Ansible rechargeront les variables d'hôte avant de résoudre le profil
> matériel référencé.
| Regénérer Autoinstall | `make baremetal/gen HOST=<nom>` | Produit `user-data` / `meta-data` à versionner. |
| Construire un ISO seed | `make baremetal/seed HOST=<nom>` | Génère `seed-<nom>.iso` idempotent. |
| Construire un ISO complet | `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` | Intègre l'installateur officiel Ubuntu (stockez l'ISO dans `files/`, `~/Downloads/` ou `~/Téléchargements/` pour la détection automatique). |
| Construire un ISO multi-hôtes | `make baremetal/multiiso HOSTS="<h1> <h2>" UBUNTU_ISO=<chemin> NAME=<artefact>` | Ajoute un menu GRUB permettant de choisir l'hôte cible (prérequis : rendre chaque hôte). |
| Découvrir le matériel | `make baremetal/discover HOST=<nom>` | Alimente `.cache/discovery/<nom>.json` via Ansible. |
| Lancer les linters | `make lint` | `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`. |
| Scanner les secrets | `make secrets-scan` | `gitleaks detect --config gitleaks.toml --exit-code 2`. |
| Générer une clé age | `make age/keygen OUTPUT=~/.config/sops/age/keys.txt` | Produit une identité `age` idempotente (`OVERWRITE=1` pour la régénérer). |
| Afficher la clé publique age | `make age/show-recipient OUTPUT=~/.config/sops/age/keys.txt` | Récupère le recipient (`age1...`) à publier dans `.sops.yaml`. |
| Inspecter l'inventaire | `make baremetal/list` | Résumé hôtes + profils matériels (`FORMAT=json` pour une sortie machine). |
| Nettoyer les artefacts | `make baremetal/clean` | Supprime les rendus locaux. |

### CLI GitOps (iso_manager.py)

L'application en ligne de commande permet de rejouer les étapes clés sans scripts supplémentaires :
```bash
python3 scripts/iso_manager.py list-hosts
python3 scripts/iso_manager.py render --host srv01 --host srv02
python3 scripts/iso_manager.py multi --host srv01 --host srv02 --ubuntu-iso files/ubuntu-24.04-live-server-amd64.iso --name prod-2025-03 --render
```

Chaque sous-commande s'appuie sur les cibles `make` idempotentes du dépôt et échoue immédiatement si un hôte n'a pas encore été initialisé dans `baremetal/inventory-local/`.

### Assistant interactif

Pour guider un·e technicien·ne étape par étape :

```bash
python3 baremetal/scripts/iso_wizard.py
```

Le script vérifie l'environnement, synchronise le dépôt, initie les hôtes,
gère les clés SOPS/age, déclenche les playbooks Ansible courants, construit les
ISO et nettoie les artefacts en s'appuyant uniquement sur les
cibles `make` (idempotence garantie). Il détecte automatiquement les ISO Ubuntu
stockées dans `files/`, `~/Downloads/` ou `~/Téléchargements/` et vous permet de
sélectionner l'artefact via un simple numéro. Les profils matériels proposés
correspondent désormais aux manifestes `*.yml`/`*.yaml` présents dans
`baremetal/inventory/profiles/hardware/`. Pour préparer un nouveau matériel,
collectez d'abord les faits via `make baremetal/discover`, puis nourrissez vos
profils à partir du cache JSON généré.

> 🆕 Les menus proposent également la gestion des clés SOPS/age, la détection
> automatique des ISO et l'exécution
> des playbooks `baremetal/*`. Utilisez `0` ou `:q` pour annuler et revenir au
> menu principal sans modifier l'état local.
> ✏️ Après avoir initialisé un hôte, ouvrez directement ses fichiers
> `host_vars/<HOST>/` via l'option « Personnaliser la configuration d'un hôte »
> pour lancer votre éditeur (ou `sops` pour les secrets) sans quitter
> l'assistant.
> ✅ Si vous fermez `sops` sans modifier le secret, l'assistant continue
> désormais sans erreur bloquante et journalise simplement qu'aucun changement
> n'a été détecté.

## Gouvernance, sécurité et conformité

- **Validations à lancer avant toute PR**
  - `make lint` : `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`.
  - `make secrets-scan` : `gitleaks detect --config gitleaks.toml --exit-code 2`.
- `make baremetal/gen HOST=<nom>` : regénère les fichiers Autoinstall impactés.
- Les validations sont rejouées sur les runners GitOps internes ; aucun workflow GitHub Actions n'est conservé dans ce dépôt (voir l'ADR 0013).
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
