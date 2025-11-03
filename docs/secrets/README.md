# Secrets GitOps (SOPS + age)

Ce répertoire rassemble les secrets chiffrés du dépôt. Toute donnée sensible
doit être stockée sous forme chiffrée avec [SOPS](https://github.com/getsops/sops)
et la couche de chiffrement [age](https://age-encryption.org/). Cette page
reprend les fondamentaux pour les débutant·e·s. Les variables spécifiques à un
hôte ne sont **plus** versionnées : elles résident dans l'overlay local
`baremetal/inventory-local/` (gitignoré) afin de respecter la politique de
non-diffusion des secrets sur GitHub.

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

## 3. Où placer les secrets (hors Git) ?

- `baremetal/inventory-local/host_vars/<hote>/secrets.sops.yaml` : secrets
  spécifiques à une machine (hash de mot de passe administrateur, clés SSH,
  jetons API). Le fichier reste local et doit être synchronisé via un support
  chiffré (Vault, disque LUKS, coffre 1Password…).
- `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml` : passphrase
  LUKS partagée entre plusieurs hôtes (optionnel, à versionner uniquement si le
  contenu est générique et anonymisé).
- `docs/secrets/baremetal-luks.sops.yaml` : exemple de secret global utilisé par
  les profils Autoinstall sécurisés. Il sert de modèle et peut être rechiffré
  avec vos propres clés.

> ℹ️ **Overlay local** : aucun fichier situé sous `baremetal/inventory-local/`
> n'est versionné. Les pipelines CI/CD et GitOps doivent reconstituer cet
> overlay à partir d'un coffre de secrets avant d'exécuter les tests ou de
> générer des ISO. Utilisez le modèle `baremetal/inventory/examples/secrets.template.yaml`
> comme base à chiffrer.

## 4. Créer ou mettre à jour un fichier chiffré

1. **Ouvrir le fichier avec SOPS** (le fichier est créé s'il n'existe pas) :
   ```bash
   sops baremetal/inventory-local/host_vars/<hote>/secrets.sops.yaml
   ```
2. **Saisir les valeurs en clair** dans votre éditeur, puis sauvegarder. À la
   fermeture, SOPS chiffre le fichier et laisse seulement les métadonnées
   visibles (`sops: ...`).
3. **Vérifier le rendu chiffré** :
   Comme le fichier est gitignoré, `git diff` ne remontera aucune modification.
   Utilisez plutôt :
   ```bash
   sops -d baremetal/inventory-local/host_vars/<hote>/secrets.sops.yaml
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
