# Guide débutant : générer sa première ISO autoinstall

Ce guide explique comment passer du clonage du dépôt à la génération d'une ISO
seed **sans connaissances préalables** sur Autoinstall ou GitOps. Chaque étape
est idempotente : vous pouvez relancer les commandes sans risque, la CI
reproduira exactement les mêmes artefacts.

## Objectifs

1. Comprendre la structure minimale du dépôt.
2. Installer les dépendances locales nécessaires.
3. Générer les fichiers `user-data`/`meta-data` pour un hôte.
4. Produire une ISO seed prête à être injectée dans l'installateur Ubuntu.
5. Vérifier que vos changements seront validés par la CI/CD.

## 1. Cloner le dépôt et explorer l'arborescence

```bash
# Clonage via SSH (recommandé)
git clone git@github.com:example/ubuntu-autoinstall.git
cd ubuntu-autoinstall

# Visualiser les dossiers clés
ls baremetal
ls vps
```

- `baremetal/` : tout ce qui concerne la génération autoinstall.
- `vps/` : rôles Ansible pour le provisioning post-installation.
- `docs/` : ADR, guides et documentation d'architecture.

> 🔁 Chaque modification doit être versionnée dans une branche dédiée, puis
> intégrée via PR. Aucun ajustement manuel en production.

## 2. Installer les dépendances locales

Les commandes Make utilisent des outils standards. Vérifiez leur disponibilité :

```bash
make doctor
```

Le `Makefile` contrôle la présence :

- de `python3` et `ansible-playbook` ;
- de `xorriso` (construction d'ISO) et `mkpasswd` (hash de mot de passe) ;
- de `sops` et d'un binaire `age` dans le `PATH`.

Il signale également (sans échouer) l'absence des linters utilisés en CI :
`yamllint`, `ansible-lint`, `shellcheck` et `markdownlint`.

> ℹ️ Si `make doctor` échoue, installez les dépendances requises puis relancez
> la commande. Aucun contournement n'est proposé dans le dépôt.

## 3. Préparer un fichier `host_vars`

Chaque hôte bare metal possède un fichier `YAML` dédié sous
`baremetal/inventory/host_vars/`.

```bash
cp baremetal/inventory/host_vars/example.yml \
  baremetal/inventory/host_vars/site-a-m710q1.yml
```

Éditez le fichier copié et personnalisez :

- `hostname` : nom attribué à la machine pendant l'installation ;
- `hardware_profile` : profil matériel (ex. `lenovo-m710q`) pour hériter des
  paramètres standards ;
- `netmode` : `dhcp` ou `static` selon votre réseau ;
- `ssh_authorized_keys` : remplacez la clé de démonstration ;
- `password_hash` : générez un hash yescrypt/SHA512 via `mkpasswd`.

> 💡 Ajoutez des champs comme `disk_device`, `ip`, `gw` ou `extra_packages` si
> vous devez dépasser les valeurs fournies par le profil matériel choisi.

## 4. Générer les fichiers autoinstall

```bash
make baremetal/gen HOST=site-a-m710q1
```

La commande rendra :

```text
baremetal/autoinstall/generated/site-a-m710q1/
├── meta-data
└── user-data
```

Vous pouvez relire `user-data` pour confirmer que les variables attendues sont
présentes.

## 5. Construire l'ISO seed

```bash
make baremetal/seed HOST=site-a-m710q1
```

Le dépôt génère un fichier ISO idempotent :

```text
baremetal/autoinstall/generated/site-a-m710q1/
└── seed-site-a-m710q1.iso
```

Enregistrez l'ISO dans votre gestionnaire d'artefacts ou attendez la génération
CI pour récupérer une copie officielle.

## 6. Préparer la Pull Request

1. Créez une branche descriptive :

   ```bash
   git checkout -b feat/site-a-m710q1
   ```

2. Validez vos changements :

   ```bash
   git status
   git diff
   git add baremetal/inventory/host_vars/site-a-m710q1.yml
   # suivez le format Conventional Commits pour vos messages de commit
   git commit -m "feat: add site-a-m710q1 host"
   ```

3. Poussez et ouvrez une PR :

   ```bash
   git push origin feat/site-a-m710q1
   ```

La CI exécutera automatiquement :

- `make lint` pour vérifier les linting YAML et Ansible.
- `make baremetal/gen` sur chaque hôte pour garantir la reproductibilité.
- `make baremetal/seed` afin de publier les ISO en artefact.

## 7. Déploiement GitOps

Une fois la PR fusionnée, Argo CD détectera la nouvelle version et appliquera
les changements décrits dans Git. Aucun accès manuel aux hôtes n'est requis.

## Check-list de sortie

- [ ] `make doctor` passe en local.
- [ ] Les fichiers `host_vars` sont validés par `yamllint` / `ansible-lint`.
- [ ] La génération autoinstall fonctionne (`make baremetal/gen`).
- [ ] L'ISO seed est produite (`make baremetal/seed`).
- [ ] Une PR documente clairement l'objectif et les tests réalisés.

> ✅ Une fois cette check-list remplie, vos changements sont prêts pour revue de
> code et déploiement automatisé.
