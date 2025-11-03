# Guide simplifié SOPS + age

Ce guide explique comment gérer vos secrets chiffrés avec [SOPS](https://github.com/getsops/sops)
et [age](https://github.com/FiloSottile/age) dans cette usine GitOps. Les étapes sont
idempotentes, reproductibles et adaptées aux flux Pull GitOps.

## Objectifs

- Générer ou réutiliser une clé `age` d'équipe.
- Configurer SOPS pour chiffrer/déchiffrer automatiquement les secrets.
- Éditer les secrets en restant dans Git, sans fuite de données en clair.
- Intégrer ces secrets dans vos pipelines (CI/CD, GitOps) de façon sécurisée.

## Pré-requis

- `age` et `sops` installés (Linux amd64 : `./scripts/install-age.sh`, `./scripts/install-sops.sh`).
- Variables d'environnement :
  - `SOPS_AGE_KEY_FILE` (chemin vers la clé privée age, ex. `~/.config/sops/age/keys.txt`).
  - Optionnel : `SOPS_AGE_RECIPIENTS` (clé(s) publique(s) supplémentaires pour partager le secret).
- Accès au dépôt Git en lecture/écriture.

> 💡 Les clés privées `age` **ne sont jamais** versionnées. Le fichier `.sops.yaml`
définit quelles clés publiques peuvent déchiffrer les secrets stockés dans Git.

## 1. Générer une clé age

```bash
# Clé de test locale (à adapter dans un coffre d'équipe ensuite)
make age/keygen OUTPUT=~/.config/sops/age/keys.txt

# Afficher la clé publique à partager dans `.sops.yaml`
make age/show-recipient OUTPUT=~/.config/sops/age/keys.txt
```

- Conservez la clé privée dans un coffre (1Password, Vault, etc.).
- Diffusez uniquement la clé publique (`age1...`).
- L'assistant `python3 baremetal/scripts/iso_wizard.py` propose les mêmes
  actions via le menu « Gérer les clés SOPS/age ».

## 2. Enregistrer la clé publique dans `.sops.yaml`

Ajoutez votre clé publique dans la section `creation_rules`. Exemple :

```yaml
creation_rules:
  - path_regex: baremetal/inventory-local/host_vars/.*/secrets\.sops\.ya?ml
    age: ["age1teamkey...", "age1technicien..."]
```

Les règles sont évaluées du haut vers le bas. L'objectif est de garantir que tous les
fichiers secrets sont chiffrés pour chaque personne / robot autorisé(e).

## 3. Initialiser un fichier de secrets

```bash
# Crée un squelette idempotent pour un hôte
make baremetal/host-init HOST=srv01 PROFILE=default

# Ouvre le fichier chiffré avec votre éditeur $EDITOR
SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
  sops baremetal/inventory-local/host_vars/srv01/secrets.sops.yaml
```

- `sops` déchiffre en mémoire, lance l'éditeur, puis rechiffre automatiquement.
- Les valeurs sont stockées en clair dans votre buffer local uniquement.

## 4. Éditer sans fuite

- **Ne copiez jamais** de secret dans un fichier `.yaml` en clair.
- Pour importer une valeur existante :

  ```bash
  echo -n "monSecret" | sops --input-type binary \
    --output-type yaml --set "[cle]" baremetal/.../secrets.sops.yaml
  ```

- `sops` conserve l'historique chiffré ; seul Git trace que le secret a changé.

## 5. Déchiffrer dans un pipeline CI/CD

1. Stockez la clé privée `age` dans un secret CI (GitHub Actions, GitLab CI).
2. Exposez-la comme variable `SOPS_AGE_KEY` ou fichier `SOPS_AGE_KEY_FILE`.
3. Avant d'exécuter Ansible / Terraform / etc. :

   ```bash
   export SOPS_AGE_KEY_FILE=$(mktemp)
   printf '%s' "$CI_SECRET_AGE_KEY" > "$SOPS_AGE_KEY_FILE"
   trap 'rm -f "$SOPS_AGE_KEY_FILE"' EXIT
   make secrets-decrypt-check
   ```

4. Utilisez uniquement des commandes idempotentes (`make baremetal/gen`, `ansible-playbook`, …).

## 6. Rotation de clés

- Ajoutez la nouvelle clé publique dans `.sops.yaml` en **tête** de liste.
- Rechiffrez tous les fichiers concernés :

  ```bash
  SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
    make secrets-reencrypt
  ```

- Retirez l'ancienne clé uniquement après validation par la CI et les pipelines GitOps.

## 7. Diagnostic rapide

```bash
# Vérifier qu'aucun secret en clair n'est committé
make secrets-scan

# Lister les fichiers SOPS et les clés utilisées
sops --config .sops.yaml --decrypt baremetal/.../secrets.sops.yaml >/dev/null
```

En cas d'échec, contrôlez :

1. `SOPS_AGE_KEY_FILE` pointe vers une clé valide.
2. Votre clé publique figure bien dans `.sops.yaml`.
3. Le fichier n'a pas été édité hors de `sops` (sinon rechargez une version valide depuis Git).

## 8. Intégration GitOps (Flux / Argo CD)

- Les contrôleurs GitOps tirent les manifests chiffrés depuis Git.
- Les clés privées `age` sont injectées via Secrets (Kubernetes) chiffrés en amont.
- Les manifests décrivent l'étape de déchiffrement (Helm hook, Kustomize SOPS plugin, etc.).

Veillez à versionner chaque modification de clé ou de règle SOPS via PR pour garder un audit complet.
