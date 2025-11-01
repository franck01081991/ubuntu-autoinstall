# Guide débutant : générer sa première ISO Autoinstall

Ce guide vous accompagne du clonage du dépôt à la production d'une ISO seed,
sans prérequis sur Autoinstall ou GitOps. Chaque étape est idempotente : vous
pouvez relancer les commandes, la CI reproduira exactement les mêmes artefacts.

## Objectifs

1. Comprendre la structure minimale du dépôt centrée sur les ISO.
2. Installer les dépendances locales nécessaires.
3. Générer les fichiers `user-data`/`meta-data` pour un hôte ou un profil.
4. Construire une ISO seed prête pour l'installateur Ubuntu.
5. Préparer une contribution conforme (branche, commit, PR).

## 1. Cloner le dépôt et explorer l'arborescence

```bash
# Clonage via SSH (recommandé)
git clone git@github.com:example/ubuntu-autoinstall.git
cd ubuntu-autoinstall

# Visualiser les dossiers clés
ls baremetal
```

- `baremetal/` : templates, inventaire et scripts pour générer les ISO.
- `ansible/` : dépendances partagées (`collections`, requirements Python, tâches
  communes).
- `docs/` : guides utilisateurs (dont ce document).

> 🔁 Toute modification doit transiter par Git (branche dédiée + PR). Aucun
> ajustement manuel n'est toléré sur les environnements cibles.

## 2. Installer les dépendances locales

Les cibles `make` reposent sur des outils standards. Vérifiez leur présence :

```bash
make doctor
```

La commande contrôle :

- `python3` et `ansible-playbook` ;
- `xorriso` (construction d'ISO) et `mkpasswd` (hash yescrypt/SHA512) ;
- `sops` et un binaire `age` dans le `PATH`.

Elle signale également (sans échouer) l'absence des linters utilisés en CI :
`yamllint`, `ansible-lint`, `shellcheck` et `markdownlint`.

> ℹ️ Corrigez toute dépendance manquante avant de poursuivre. Les scripts ne
> fournissent pas de contournement local.

## 3. Préparer un répertoire `host_vars`

Chaque hôte dispose d'un **répertoire** contenant :

- `main.yml` : variables non sensibles ;
- `secrets.sops.yaml` : secrets chiffrés (hash du mot de passe, clés SSH,
  tokens). Ce fichier doit rester chiffré dans Git.

Initialisez le dossier et l'inventaire avec la cible automatisée :

```bash
make baremetal/host-init HOST=site-a-m710q1 PROFILE=lenovo-m710q
```

La commande :

- crée `baremetal/inventory/host_vars/site-a-m710q1/` ;
- génère un `main.yml` minimal (`hostname`, `hardware_profile`, `netmode: dhcp`) ;
- copie `secrets.sops.yaml` depuis l'exemple ;
- ajoute l'hôte dans `baremetal/inventory/hosts.yml`.

La cible est idempotente : relancez-la après avoir supprimé un fichier ou pour
ajouter l'hôte à l'inventaire.

Ensuite, personnalisez `main.yml` (profil matériel, disques, réseau) puis
éditez les secrets via SOPS :

```bash
$EDITOR baremetal/inventory/host_vars/site-a-m710q1/main.yml
SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
  sops baremetal/inventory/host_vars/site-a-m710q1/secrets.sops.yaml
```

> 🔐 Pour activer le chiffrement OS, ajoutez `disk_encryption.enabled: true`
> et référençez la passphrase fournie par SOPS
> (`passphrase: "{{ disk_encryption_passphrase }}"`). Suivez le guide
> [Chiffrement du disque système](baremetal-disk-encryption.md) pour créer
> le secret `SOPS` requis.
> 💡 Les profils matériels (`baremetal/inventory/profiles/hardware/`) fournissent
> des valeurs de référence. Inspirez-vous-en pour compléter `main.yml`.
> 🧩 Exemple : pour un Raspberry Pi 4B sur carte SD, rendez directement le profil matériel `raspberry-pi-4b-sd` avec :
> `make baremetal/gen PROFILE=raspberry-pi-4b-sd`.

## 4. Générer les fichiers Autoinstall

```bash
make baremetal/gen HOST=site-a-m710q1
```

La commande produit :

```text
baremetal/autoinstall/generated/site-a-m710q1/
├── meta-data
└── user-data
```

Relisez `user-data` pour valider le rendu des variables critiques.

## 5. Construire l'ISO seed

```bash
make baremetal/seed HOST=site-a-m710q1
```

Le dépôt génère un fichier ISO idempotent :

```text
baremetal/autoinstall/generated/site-a-m710q1/
└── seed-site-a-m710q1.iso
```

Pour produire une ISO complète intégrant l'installateur Ubuntu :

```bash
make baremetal/fulliso HOST=site-a-m710q1 \
  UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso
```

## 6. Préparer la Pull Request

1. Créez une branche descriptive :

   ```bash
   git checkout -b feat/site-a-m710q1
   ```

2. Vérifiez et validez vos changements :

   ```bash
   git status
   git diff
   git add baremetal/inventory/host_vars/site-a-m710q1
   git commit -m "feat: add site-a-m710q1 host"
   ```

3. Poussez et ouvrez la PR :

   ```bash
   git push origin feat/site-a-m710q1
   ```

La CI exécutera automatiquement :

- `make lint` pour contrôler YAML, Ansible, Shell et Markdown ;
- `make baremetal/gen` pour reconstruire les artefacts.

> ℹ️ Les images ISO ne sont plus construites en CI : elles sont générées et
> publiées par les pipelines internes après validation GitOps.

## 7. Déploiement GitOps

Une fois la PR fusionnée, la responsabilité de générer et de distribuer les ISO
incombe aux pipelines internes (usine d'image, orchestrateur interne, etc.).
Votre plateforme GitOps (Argo CD, Flux, etc.) consomme ensuite ces artefacts
validés. Aucun accès manuel aux hôtes n'est requis.

## Check-list de sortie

- [ ] `make doctor` est au vert.
- [ ] Les fichiers `host_vars` passent `yamllint` / `ansible-lint`.
- [ ] `make baremetal/gen` produit les artefacts attendus.
- [ ] `make baremetal/seed` (et éventuellement `make baremetal/fulliso`) réussit.
- [ ] La PR décrit l'objectif et les tests réalisés.

> ✅ Une fois cette check-list validée, vos changements sont prêts pour revue de
> code et intégration continue.
