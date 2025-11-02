# 0006 — Rationalisation de la CI GitHub Actions

- Date: 2024-09-05
- Status: Superseded by ADR-0008 (2025-02-14)
- Superseded-by: ADR-0008
- Deciders: Platform Team
- Tags: ci, github-actions, optimisation

## Contexte

Les workflows GitHub Actions déclenchaient systématiquement l'intégralité des
lintings et scans de sécurité à chaque commit ou pull request, même en absence
de modifications pertinentes. Cette exécution systématique consommait un volume
important de minutes GitHub Actions et rallongeait les boucles de feedback.

> [!NOTE]
> Cette décision est remplacée par l'ADR-0008 — Security guardrails
> (`docs/adr/0008-security-guardrails.md`).
> Trivy est de nouveau exécuté sur les pull requests conformément aux nouvelles
> guardrails.

## Décision

- Ajouter un bloc `concurrency` aux workflows `build-iso` et `repository-integrity`
  (Superseded)
  afin d'annuler les exécutions redondantes sur une même branche.
- Restreindre les événements `push`/`pull_request` du workflow `repository-integrity`
  (Superseded)
  aux fichiers et répertoires concernés par les linters.
- Déplacer l'exécution de Trivy sur les `push` vers `main`/`master`, sur une
  (Superseded)
  planification hebdomadaire et sur `workflow_dispatch`, en le désactivant pour
  les pull requests.
- Fournir une étape idempotente qui n'installe `shellcheck` que si l'outil est
  (Superseded)
  absent sur le runner pour éviter un `apt-get` systématique.

## Conséquences

- **Positives**
  - Réduction du nombre de jobs exécutés à chaque commit, donc une facture GitHub
    Actions allégée.
    (Superseded)
  - Temps de feedback amélioré pour les contributeurs tout en conservant la
    couverture linting et sécurité.
    (Superseded)
  - Meilleure prévisibilité grâce à la planification hebdomadaire du scan Trivy.
    (Superseded)
- **Négatives**
  - Les secrets ou mauvaises configurations introduits uniquement dans une pull
    request ne seront détectés par Trivy qu'après merge ou via un déclenchement
    manuel.
    (Superseded)
- **Neutres/Mitigations**
  - La documentation rappelle la possibilité de lancer manuellement le workflow
    en cas de besoin urgent sur une branche de travail.
