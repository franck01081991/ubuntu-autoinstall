# Fiche mémo technicien

Gardez ce mémo à portée de main pour exploiter la chaîne Ubuntu Autoinstall
après votre formation initiale. Chaque commande est idempotente et passe par
Git afin de respecter les principes GitOps.

---

## Routine quotidienne

| Action | Commande | Détails |
|--------|----------|---------|
| Vérifier la station de travail | `make doctor` | Contrôle dépendances (python3, ansible-core, xorriso, mkpasswd, sops, age, cloud-init). |
| Synchroniser un hôte | `make baremetal/host-init HOST=<nom> PROFILE=<profil>` | Crée ou met à jour `baremetal/inventory-local/host_vars/` + `baremetal/inventory-local/hosts.yml` (gitignorés). Relancez après toute modification. |
| Capturer les faits matériels | `make baremetal/discover HOST=<nom>` | Écrit `.cache/discovery/<nom>.json` (non versionné) via le playbook `discover_hardware.yml`. |
| Regénérer Autoinstall | `make baremetal/gen HOST=<nom>` | Produit `user-data` / `meta-data` à relire et versionner. |
| Construire l'ISO seed | `make baremetal/seed HOST=<nom>` | Génère `seed-<nom>.iso`. Résultat identique à chaque exécution. |
| Construire l'ISO complète | `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` | Ajoute l'installateur officiel Ubuntu Live Server. |
| Lancer les linters | `make lint` | `yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`. |
| Scanner les secrets | `make secrets-scan` | `gitleaks detect --config gitleaks.toml --exit-code 2`. |
| Générer une clé age | `make age/keygen OUTPUT=~/.config/sops/age/keys.txt` | Crée ou régénère l'identité `age` locale (`OVERWRITE=1`). |
| Afficher la clé publique age | `make age/show-recipient OUTPUT=~/.config/sops/age/keys.txt` | Affiche le recipient à ajouter dans `.sops.yaml`. |
| Lister inventaire + profils | `make baremetal/list` | Vérifie rapidement la cohérence de vos hôtes et profils matériels. |
| Nettoyer les artefacts | `make baremetal/clean` | Supprime les fichiers générés localement. |

---

## Bonnes pratiques GitOps

- **Toujours via Git** : branche dédiée + PR avec relecture. Aucun ajustement
  manuel sur les serveurs ou dans les ISO publiées.
- **Secrets chiffrés** : utilisez `sops` + `age` pour tous les fichiers
  `*.sops.yaml`. Vérifiez avec `make secrets-scan` avant d'ouvrir une PR.
- **CI obligatoire** : la revue doit montrer `make lint`, `make baremetal/gen`,
  `make baremetal/seed` et `make secrets-scan` au vert. La CI relance les mêmes
  contrôles et ajoute `trivy fs` + `gitleaks`.
- **Traçabilité** : associez chaque génération d'ISO à un commit/tag et
  conservez les artefacts dans un stockage maîtrisé et chiffré.
- **Rollback prêt** : décrivez dans la PR la marche arrière prévue
  (commit précédent, ISO de secours, etc.).

---

## Diagnostiquer vite

- `make baremetal/list-hosts` : s'assurer qu'un hôte est bien versionné avant de
  lancer `make baremetal/gen` ou l'assistant ISO.
- `python3 baremetal/scripts/iso_wizard.py` : assistant interactif pour guider
  un technicien pas à pas (dépendances, gestion des clés SOPS/age, playbooks,
  génération ISO, nettoyage).
- Placez l'ISO officielle dans `files/`, `~/Downloads/` ou `~/Téléchargements/`
  pour que l'assistant la détecte automatiquement lors de la génération
  `baremetal/fulliso`.
- Depuis le menu « Personnaliser la configuration d'un hôte », ouvrez les
  fichiers `host_vars/<HOST>/` dans votre éditeur (ou `sops` pour les secrets)
  juste après l'initialisation.
- [`docs/troubleshooting.md`](troubleshooting.md) : recense les erreurs les plus
  fréquentes (dépendances manquantes, clé SOPS absente, ISO introuvable) et les
  résolutions GitOps associées.

Respectez ces réflexes pour rester conforme aux exigences d'idempotence et de
sécurité du projet.
