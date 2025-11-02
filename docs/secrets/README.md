# Secrets GitOps (SOPS + age)

Ce répertoire rassemble les secrets chiffrés du dépôt. Toute donnée sensible
doit être stockée sous forme chiffrée avec [SOPS](https://github.com/getsops/sops)
et la couche de chiffrement [age](https://age-encryption.org/). Cette page
reprend les fondamentaux pour les débutant·e·s.

## 1. Comprendre les rôles de SOPS et age

- **age** gère la cryptographie. Chaque personne possède une clé privée stockée
  localement (`~/.config/sops/age/keys.txt`) et partage une clé publique via Git
  (`.sops.yaml`).
- **SOPS** est l'outil qui s'occupe d'ouvrir/modifier les fichiers YAML chiffrés
  (`*.sops.yaml`). Lors de la sauvegarde, SOPS chiffre automatiquement le
  contenu pour toutes les clés publiques listées dans `.sops.yaml`.

👉 Résultat : les secrets sont illisibles dans Git, mais toutes les personnes
autorisées peuvent les ouvrir localement ou dans la CI/CD.

## 2. Préparer son environnement

1. **Installer les binaires** (Linux amd64) :
   ```bash
   ./scripts/install-age.sh
   ./scripts/install-sops.sh
   ```
2. **Installer la clé age de l'équipe** :
   ```bash
   ./scripts/bootstrap-demo-age-key.sh   # crée ~/.config/sops/age/keys.txt si besoin
   export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
   ```
   En production, remplacez la clé de démonstration par la vôtre et soumettez la
   clé publique dans `.sops.yaml` via PR.

> 💡 Pour vérifier que tout fonctionne, lancez `sops -d docs/secrets/baremetal-luks.sops.yaml`
> (ou tout autre fichier) : si la commande affiche du YAML lisible, votre clé est
> correctement chargée.

## 3. Où placer les secrets ?

- `baremetal/inventory/host_vars/<hote>/secrets.sops.yaml` : secrets spécifiques
  à une machine (hash de mot de passe administrateur, clés SSH, jetons API).
- `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml` : passphrase
  LUKS partagée entre plusieurs hôtes.
- `docs/secrets/baremetal-luks.sops.yaml` : exemple de secret global utilisé par
  les profils Autoinstall sécurisés.

Tous ces fichiers sont chiffrés et versionnés. La CI/CD reçoit la clé privée via
un secret chiffré (`SOPS_AGE_KEY`) et peut donc les déchiffrer pour rejouer les
playbooks.

## 4. Créer ou mettre à jour un fichier chiffré

1. **Ouvrir le fichier avec SOPS** (le fichier est créé s'il n'existe pas) :
   ```bash
   sops baremetal/inventory/host_vars/<hote>/secrets.sops.yaml
   ```
2. **Saisir les valeurs en clair** dans votre éditeur, puis sauvegarder. À la
   fermeture, SOPS chiffre le fichier et laisse seulement les métadonnées
   visibles (`sops: ...`).
3. **Vérifier le rendu chiffré** :
   ```bash
   git diff baremetal/inventory/host_vars/<hote>/secrets.sops.yaml
   ```
   ou affichez le contenu en clair sans l'éditer :
   ```bash
   sops -d baremetal/inventory/host_vars/<hote>/secrets.sops.yaml
   ```

## 5. Exemple minimal (passphrase LUKS)

```bash
sops --age age1examplepublickey123 --encrypt --input-type yaml --output-type yaml \
  --output docs/secrets/baremetal-luks.sops.yaml <(cat <<'YAML'
disk_luks_passphrase: "votre-passphrase-super-secrete"
YAML
)
```

Remplacez `age1examplepublickey123` par votre clé publique `age`. L'entrée sera
ensuite utilisée par la CI/CD et par les playbooks Ansible.

## 6. Bonnes pratiques

- Ne jamais committer un secret en clair : lancez `make secrets-scan` avant
  chaque PR.
- Documenter dans votre PR la mise à jour des clés publiques (`.sops.yaml`) et
  le plan de rotation des clés.
- Conserver les clés privées `age` dans un gestionnaire de secrets (Vault,
  1Password…) et uniquement injecter la clé nécessaire dans `SOPS_AGE_KEY` côté
  pipeline.
