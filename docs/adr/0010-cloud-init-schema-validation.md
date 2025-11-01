# ADR 0010 — Validation schema cloud-init dans la chaîne bare metal

## Statut

Accepté

## Contexte

Les fichiers `user-data` rendus pour Autoinstall sont consommés par `cloud-init` pendant
l'installation Ubuntu. Une erreur de syntaxe YAML ou une clé incompatible avec le schéma
peut bloquer l'installation en phase précoce, sans feedback immédiat côté CI. Jusqu'ici,
nous ne validions pas ces fichiers au-delà des linters YAML génériques.

## Décision

- Ajouter une cible Make `baremetal/validate` qui exécute `cloud-init schema` sur
  `baremetal/autoinstall/generated/<target>/user-data`.
- Fournir un script dédié `baremetal/scripts/validate_cloud_init.sh` (mode strict) pour
  encapsuler l'appel et contrôler l'existence du fichier.
- Étendre le workflow GitHub Actions `build-iso.yml` afin qu'il installe le paquet
  `cloud-init` et exécute la validation après rendu des fichiers Autoinstall.

## Conséquences

- **Développeurs** : disposent d'une commande locale (`make baremetal/validate`) pour
  détecter les erreurs de schéma avant de pousser leurs modifications.
- **CI/CD** : tout `user-data` généré lors de la validation est garanti conforme au schéma
  officiel `cloud-init`, limitant les régressions runtime.
- **Dépendances** : `cloud-init` devient un outil recommandé (optionnel) pour reproduire la
  validation en local ; `make doctor` le signale.

## Alternatives considérées

- **Validation via yamllint uniquement** : insuffisant pour détecter les erreurs de schéma
  ou de champs obsolètes.
- **Validation différée sur machine de test** : rejetée car introduit un feedback tardif et
  repose sur des actions manuelles hors GitOps.

## Actions

1. Ajouter la cible `baremetal/validate` et le script associé.
2. Installer `cloud-init` dans le job `validate` du workflow `build-iso.yml`.
3. Documenter la dépendance et la nouvelle commande dans le `README`.

## Considérations de sécurité

- La validation est purement locale (lecture seule) et n'expose aucune donnée sensible.
- Aucun secret n'est transmis à `cloud-init schema` ; le binaire s'exécute sur les artefacts
  générés depuis Git.

## Références

- Documentation officielle `cloud-init`: [https://cloudinit.readthedocs.io/en/latest/](https://cloudinit.readthedocs.io/en/latest/)
