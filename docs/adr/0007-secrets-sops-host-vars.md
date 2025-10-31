# ADR-0007 — Host secret management with SOPS

## Statut

Accepté — 2025-10-31

## Contexte

Les inventaires bare metal exposaient encore des secrets en clair (`password_hash`,
`ssh_authorized_keys`) directement dans `host_vars/*.yml` et les profils
matériels. Cette pratique contredisait les objectifs GitOps/SecOps du dépôt et
bloquait l'intégration continue de contrôles automatiques.

## Décision

- Chaque hôte dispose désormais d'un répertoire dédié (`host_vars/<hôte>/`)
  contenant :
  - `main.yml` pour les variables non sensibles ;
  - `secrets.sops.yaml` pour les secrets chiffrés via SOPS/age.
- Les profils matériels ne portent plus aucun secret. Ils référencent les
  secrets SOPS situés aux côtés des hôtes.
- `.sops.yaml` force le chiffrement des secrets (`password_hash`,
  `ssh_authorized_keys`, passphrases) pour `host_vars`, `group_vars` et `docs/secrets`.
- Un contrôle CI (`scripts/ci/check-no-plaintext-secrets.py`) échoue si un secret
  est committé en clair dans l'inventaire.
- Les workflows GitHub Actions installent SOPS/age et exigent une clé privée
  `SOPS_AGE_KEY` (stockée dans les secrets GitHub) pour déchiffrer les fichiers.

## Conséquences

- Les contributeurs doivent disposer de la clé `age` commune pour éditer les
  secrets (`sops host_vars/<hôte>/secrets.sops.yaml`).
- Toute absence ou corruption de secrets chiffrés est détectée tôt par la CI.
- Les documents utilisateur/README ont été mis à jour pour refléter le nouveau
  flux GitOps et rappeler l'usage obligatoire de SOPS.
- Les secrets existants doivent être régénérés/rechiffrés avec la clé commune
  avant de pousser une modification.
