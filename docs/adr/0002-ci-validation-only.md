# 0002 — CI validates autoinstall payloads only

- Date: 2024-06-07
- Status: Accepted
- Deciders: Platform Team
- Tags: ci, gitops, baremetal

## Contexte

Le workflow historique `build-iso` générait les ISO seed et complètes pour chaque
profil matériel depuis GitHub Actions. Cette approche provoquait des temps
d'exécution élevés, une pression accrue sur le stockage des artefacts et ne
couvrait pas l'intégralité des machines déclarées (hôtes individuels).

## Décision

La CI ne construit plus d'images. Elle se limite désormais à rendre les
fichiers `user-data` et `meta-data` pour tous les profils matériels et pour tous
les hôtes définis dans l'inventaire. Les ISO doivent être assemblées en dehors
du dépôt (poste d'admin, usine d'image interne, etc.) en utilisant les scripts
versionnés.

## Conséquences

- **Positives**
  - Réduction significative du temps d'exécution et de la consommation
    d'artefacts dans GitHub Actions.
  - Couverture fonctionnelle étendue : chaque hôte est validé automatiquement.
  - Alignement renforcé avec la philosophie GitOps (CI = validation, build
    final contrôlé par les équipes).
- **Négatives**
  - Les équipes doivent télécharger ou régénérer les artefacts pour produire
    elles-mêmes les ISO.
  - Perte de la distribution automatique des images dans GitHub Actions.
- **Neutres/Mitigations**
  - La documentation fournit un guide détaillé pour générer les ISO hors CI.
  - Les scripts `make baremetal/seed` et `make baremetal/fulliso` restent
    idempotents pour simplifier la génération locale.
