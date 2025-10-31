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

## 3. Préparer un fichier `host_vars`

Chaque hôte possède un fichier YAML dédié sous
`baremetal/inventory/host_vars/`.

```bash
cp baremetal/inventory/host_vars/example.yml \
  baremetal/inventory/host_vars/site-a-m710q1.yml
```

Éditez le fichier copié et personnalisez notamment :

- `hostname` : nom attribué durant l'installation ;
- `hardware_profile` : profil matériel (ex. `lenovo-m710q`) pour hériter des
  valeurs par défaut ;
- `disk_device` : disque système principal ;
- `netmode`, `nic`, `ip`, `gw`, `dns` si vous utilisez une configuration
  statique ;
- `ssh_authorized_keys` et `password_hash` (YESCRYPT recommandé).

> 💡 Les profils matériels (`baremetal/inventory/profiles/hardware/`) contiennent
> des valeurs de référence. Inspirez-vous-en pour créer vos propres fichiers
> `host_vars`.

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
   git add baremetal/inventory/host_vars/site-a-m710q1.yml
   git commit -m "feat: add site-a-m710q1 host"
   ```

3. Poussez et ouvrez la PR :

   ```bash
   git push origin feat/site-a-m710q1
   ```

La CI exécutera automatiquement :

- `make lint` pour contrôler YAML, Ansible, Shell et Markdown ;
- `make baremetal/gen` pour reconstruire les artefacts ;
- `make baremetal/seed` et `make baremetal/fulliso` selon les profils suivis.

## 7. Déploiement GitOps

Une fois la PR fusionnée, votre plateforme GitOps (Argo CD, Flux, etc.) récupère
les ISO publiées par la CI. Aucun accès manuel aux hôtes n'est requis.

## Check-list de sortie

- [ ] `make doctor` est au vert.
- [ ] Les fichiers `host_vars` passent `yamllint` / `ansible-lint`.
- [ ] `make baremetal/gen` produit les artefacts attendus.
- [ ] `make baremetal/seed` (et éventuellement `make baremetal/fulliso`) réussit.
- [ ] La PR décrit l'objectif et les tests réalisés.

> ✅ Une fois cette check-list validée, vos changements sont prêts pour revue de
> code et intégration continue.
