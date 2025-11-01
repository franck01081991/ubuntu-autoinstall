# Fiche mémo technicien

Ce mémo regroupe les commandes et contrôles essentiels pour opérer la
chaîne Autoinstall en mode GitOps. Utilisez-le une fois l'onboarding
terminé afin de gagner du temps sur les opérations quotidiennes.

## Commandes incontournables

| Objectif | Commande | Notes |
|----------|----------|-------|
| Vérifier l'environnement local | `make doctor` | Contrôle dépendances obligatoires et linters recommandés. |
| Initialiser / resynchroniser un hôte | `make baremetal/host-init HOST=<nom> PROFILE=<profil>` | Crée ou remet à niveau `host_vars/` et l'inventaire Ansible. |
| Regénérer les fichiers Autoinstall | `make baremetal/gen HOST=<nom>` | Rejouer pour valider un rendu après modification de variables. |
| Construire une ISO seed | `make baremetal/seed HOST=<nom>` | Produit `seed-<hote>.iso` idempotent. |
| Construire une ISO complète | `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>` | Nécessite l'ISO officielle Ubuntu en entrée. |
| Lancer tous les linters | `make lint` | Reflète la CI (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`). |
| Scanner les secrets | `make secrets-scan` | Alias local de `gitleaks detect`, identique au pipeline CI. |

## Rappels GitOps obligatoires

- **Toujours via Git** : aucune modification hors PR (ni inventaire, ni script).
- **Branches descriptives** : `feat/`, `fix/`, `ops/` selon la nature du
  changement. Documentez la PR pour contextualiser.
- **Secrets chiffrés** : utilisez `sops` + `age`. Les fichiers `*.sops.yaml`
  ne doivent jamais être commités en clair.
- **CI comme garde-fou** : `make lint` et `make secrets-scan` doivent passer
  localement avant toute revue. Les pipelines reconstruisent automatiquement
  les artefacts impactés.
- **Traçabilité** : associez chaque production d'ISO à un tag ou un artefact
  référencé dans la PR pour assurer l'audit.
- **Rollback** : préparez un plan de retour (tag, commit précédent) avant
  d'appliquer une ISO en production.

Gardez cette fiche à portée pour accélérer vos opérations tout en respectant
les exigences d'idempotence et de conformité GitOps.
