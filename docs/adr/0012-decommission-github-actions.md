# 0012 — Désactivation complète de GitHub Actions

- Date: 2025-02-15
- Status: Accepted
- Deciders: Platform Team
- Tags: ci, github-actions, governance

## Contexte

Les workflows GitHub Actions `build-iso`, `repository-integrity` et
`secret-scanning` ne sont plus utilisés par les équipes d'intégration. Les
lintings, scans de secrets et reconstructions d'ISO sont désormais déclenchés via
les commandes `make` exécutées sur des runners internes gérés par un autre
système d'orchestration. Les pipelines GitHub Actions consommaient malgré tout
quota et minutes sans apporter de valeur supplémentaire.

## Décision

- Supprimer les workflows GitHub Actions inutilisés de `.github/workflows/`.
- Centraliser les contrôles (`make lint`, `make secrets-scan`, `make baremetal/gen`)
  dans la documentation comme prérequis aux revues.
- Confier l'exécution automatisée à la plateforme GitOps interne (Flux/Argo CD)
  qui tire les artefacts depuis le dépôt.

## Conséquences

- **Positives**
  - Réduction des coûts associés aux minutes GitHub Actions.
  - Simplification de la maintenance CI côté dépôt GitHub.
  - Alignement avec l'outillage interne unique pour les validations.
- **Négatives**
  - Perte de garde-fous automatiques côté GitHub : une PR peut être fusionnée
    sans exécution vérifiée si les contributeurs omettent les commandes locales.
  - Visibilité réduite pour les externes qui ne voient plus l'état des pipelines
    directement sur GitHub.
- **Mitigations**
  - Documentation renforcée pour rappeler l'exécution obligatoire des commandes
    locales avant toute PR.
  - Les pipelines GitOps internes conservent la responsabilité de refuser un
    déploiement si les artefacts n'ont pas été régénérés.
