# Guide débutant : produire sa première ISO en autonomie

Ce tutoriel accompagne un·e technicien·ne qui découvre la chaîne
**Ubuntu Autoinstall GitOps**. Chaque action est idempotente : relancez une
commande sans risque pour retrouver un état cohérent.

> 🎯 Objectif final : générer et versionner une ISO *seed* prête à l'emploi pour
> un hôte bare metal donné.

---

## Vue d'ensemble

| Étape | Résultat obtenu | Commandes principales |
|-------|-----------------|-----------------------|
| 1. Préparer l'environnement | Dépôt cloné et dépendances vérifiées | `git clone`, `make doctor` |
| 2. Créer l'hôte | Inventaire `host_vars` + secrets chiffrés | `make baremetal/host-init`, `sops` |
| 3. Découvrir le matériel | Cache JSON local pour enrichir les profils | `make baremetal/discover` |
| 4. Générer les fichiers Autoinstall | `user-data` et `meta-data` contrôlés | `make baremetal/gen`, revue manuelle |
| 5. Construire l'ISO | ISO seed (et ISO complète optionnelle) | `make baremetal/seed`, `make baremetal/fulliso` |
| 6. Soumettre la contribution | Branche, commit, PR décrivant la livraison | `git checkout -b`, `git commit`, `git push` |

Gardez la [fiche mémo technicien](technician-cheatsheet.md) pour vos
opérations ultérieures et le [guide de dépannage](troubleshooting.md)
pour résoudre les anomalies courantes.

---

## 1. Préparer l'environnement

1. **Cloner le dépôt et entrer dans le dossier** :
   ```bash
   git clone git@github.com:example/ubuntu-autoinstall.git
   cd ubuntu-autoinstall
   ```
2. **Contrôler les prérequis** :
   ```bash
   make doctor
   ```
   Cette commande vérifie la présence de `python3`, `ansible-core`, `xorriso`,
   `mkpasswd`, `sops`, `age` et `cloud-init`. Corrigez toute dépendance manquante
   avant d'aller plus loin. Elle rappelle également les linters utilisés par la CI
   (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`).

> ℹ️ Si vous devez installer `sops`, un script est disponible :
> `./scripts/install-sops.sh` (Linux amd64).

---

## 2. Créer l'hôte et protéger les secrets

1. **Initialiser l'hôte** :
   ```bash
   make baremetal/host-init HOST=site-a-m710q1 PROFILE=lenovo-m710q
   ```
   Effets :
   - création de `baremetal/inventory/host_vars/site-a-m710q1/` ;
   - génération d'un `main.yml` minimal (`hostname`, `hardware_profile`, `netmode`) ;
   - copie d'un `secrets.sops.yaml` d'exemple ;
   - ajout automatique de l'hôte dans `baremetal/inventory/hosts.yml`.

2. **Compléter les variables claires** :
   ```bash
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1/main.yml
   ```
   Renseignez le profil matériel, les interfaces réseau, les disques et toute
   variable requise par vos templates.

3. **Chiffrer les secrets** :
   ```bash
   SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
     sops baremetal/inventory/host_vars/site-a-m710q1/secrets.sops.yaml
   ```
   Stockez-y uniquement des données sensibles (hash de mot de passe,
   `ssh_authorized_keys`, passphrases LUKS). Les passphrases globales se placent
   dans `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.

4. **Valider l'inventaire** :
   ```bash
   make baremetal/list
   ```
   L'hôte doit apparaître dans la section « Hôtes déclarés ».

> 🔐 GitOps oblige : aucun secret en clair dans Git. Si vous avez un doute,
> exécutez `make secrets-scan` avant de pousser votre branche.

---

## 3. Découvrir le matériel automatiquement

1. **Exécuter la découverte** :
   ```bash
   make baremetal/discover HOST=site-a-m710q1
   ```
   Cette commande lance le playbook `discover_hardware.yml` qui collecte les
   `ansible_facts`, le rendu `lsblk --json` et `ip -j link`. Un fichier JSON est
   créé sous `.cache/discovery/site-a-m710q1.json` (non versionné) afin de
   faciliter la mise à jour des profils matériels.

2. **Analyser le cache** : ouvrez le fichier généré pour confirmer les noms
   d'interfaces, les disques et les caractéristiques CPU/RAM avant de finaliser
   vos profils.

---

## 4. Générer et contrôler les fichiers Autoinstall

1. **Rendre les fichiers** :
   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```
2. **Vérifier le rendu** :
   ```bash
   ls baremetal/autoinstall/generated/site-a-m710q1
   ```
   Vous devez obtenir :
   ```text
   meta-data
   user-data
   ```
3. **Relire `user-data`** pour confirmer les sections sensibles :
   ```bash
   $EDITOR baremetal/autoinstall/generated/site-a-m710q1/user-data
   ```
4. **Optionnel : valider le schéma cloud-init** :
   ```bash
   make baremetal/validate HOST=site-a-m710q1
   ```

---

## 5. Construire l'ISO

1. **ISO seed** (recommandé) :
   ```bash
   make baremetal/seed HOST=site-a-m710q1
   ```
   Résultat : `baremetal/autoinstall/generated/site-a-m710q1/seed-site-a-m710q1.iso`.

2. **ISO complète** (optionnel, nécessite l'ISO officielle Ubuntu) :
   ```bash
   make baremetal/fulliso HOST=site-a-m710q1 \
     UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso
   ```
   Conservez les ISO dans un stockage maîtrisé et chiffré.

3. **Nettoyage si besoin** :
   ```bash
   make baremetal/clean
   ```

> 📦 Les artefacts générés localement servent à la validation. La production
> officielle doit être rejouée par la CI/pipeline GitOps après revue de code.

---

## 6. Soumettre la contribution

1. **Créer une branche descriptive** :
   ```bash
   git checkout -b feat/site-a-m710q1
   ```
2. **Inspecter et valider les changements** :
   ```bash
   git status
   git diff
   make lint
   make secrets-scan
   git add baremetal/inventory/host_vars/site-a-m710q1
   git commit -m "feat: add site-a-m710q1 host"
   ```
3. **Pousser et ouvrir la PR** :
   ```bash
   git push origin feat/site-a-m710q1
   ```
   Dans la PR, détaillez :
   - l'objectif (nouvel hôte, modification de profil…) ;
   - les tests effectués (`make gen`, `make seed`, `make lint`, `make secrets-scan`) ;
   - le plan de rollback (commit ou tag précédent) en cas de problème.

4. **Laisser la CI travailler** :
   - reconstruction automatique des Autoinstall touchés ;
   - `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`, `trivy fs` ;
   - `gitleaks detect` pour la chasse aux secrets.

5. **Après fusion** :
   Vos pipelines GitOps (Flux/Argo CD) récupèrent les artefacts validés et
   orchestrent la distribution. Aucun déploiement manuel n'est autorisé.

---

## Check-list finale

- [ ] `make doctor` sans erreur.
- [ ] `make baremetal/discover` exécuté pour capturer les faits matériels.
- [ ] `make baremetal/gen` et `make baremetal/seed` exécutés avec succès.
- [ ] `make lint` et `make secrets-scan` au vert.
- [ ] Secrets uniquement dans des fichiers `*.sops.yaml` chiffrés.
- [ ] PR créée avec tests, impacts et rollback documentés.

✅ Si tout est coché, votre contribution est prête pour revue et intégration
GitOps.
