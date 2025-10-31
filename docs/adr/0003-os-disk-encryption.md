# 0003 - Chiffrement du disque OS via Autoinstall

- Status: Accepted
- Date: 2024-05-14
- Décideurs: Équipe Plateforme / Sécurité
- Contexte: Sécurisation des installations bare metal via LUKS

## Contexte

Les ISO Autoinstall généraient jusqu'ici des installations LVM non chiffrées.
Les exigences de conformité internes imposent désormais le chiffrement intégral
du disque système (root) durant l'installation, sans intervention manuelle et
avec traçabilité GitOps.

## Décision

- Ajouter un bloc `dm_crypt` optionnel dans le template `user-data.j2`.
- Piloter l'activation via la variable `disk_encryption.enabled` exposée dans les
  `host_vars` / profils matériels.
- Exiger la présence d'une passphrase fournie par `SOPS` lorsque le chiffrement
  est activé (`mandatory` sur `disk_encryption.passphrase`).
- Documenter la procédure (guide dédié + README) et imposer le stockage des
  secrets dans `baremetal/inventory/group_vars/all/*.sops.yaml`.

## Conséquences

### Positives

- Conformité : chiffrement LUKS reproductible et versionné.
- Sécurité : aucune passphrase en clair dans le dépôt, la CI ou les journaux.
- Extensibilité : possibilité de personnaliser `cipher`, `keysize`, `pbkdf`.

### Négatives / risques

- Dépendance forte à `sops` + `age` pour la génération des ISO.
- Echec de génération si la passphrase manque ou si la configuration SOPS est
  invalide.
- Complexité accrue pour la rotation des secrets (processus documenté).

## Alternatives étudiées

1. **Passphrase saisie manuellement pendant l'installation** : rejeté car non
   GitOps et non auditables.
2. **Utilisation de TPM ou Tang** : hors périmètre court terme, nécessite une
   infrastructure additionnelle.

## Actions de suivi

- Intégrer la création du fichier SOPS dans les check-lists d'onboarding.
- Prévoir des tests automatisés (CI) utilisant un secret factice chiffré lorsque
  les clés publiques seront disponibles.
- Étudier l'ajout futur d'un slot TPM/Tang pour la dérivation automatique de la
  clé.
