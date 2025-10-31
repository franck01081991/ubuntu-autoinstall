# 0004 — Sélection dynamique des validations bare metal

- Date: 2024-07-05
- Status: Accepted
- Deciders: Platform Team
- Tags: ci, gitops, baremetal

## Contexte

Chaque commit exécutait neuf jobs parallèles dans `Validate Bare Metal Configurations`.
La matrice fixe relançait l'intégralité des validations, y compris lorsque seuls
un ou deux hôtes/profils étaient modifiés. Résultat : consommation excessive de
minutes CI, temps d'attente long pour les revues et charge inutile sur les
runners GitHub Actions.

## Décision

Introduire une étape de planification qui compare le commit courant à sa base et
sélectionne uniquement les cibles bare metal (profils matériels ou hôtes)
affectées. Les modifications globales (playbooks communs, templates, scripts)
continuent de déclencher une validation complète. La sélection est implémentée
par un script Python idempotent versionné sous `scripts/ci/` et orchestré par un
job `plan` dédié dans le workflow GitHub Actions.

## Conséquences

- **Positives**
  - Réduction drastique du nombre de jobs lancés lorsque les changements sont
    localisés (minutes CI économisées, feedback plus rapide).
  - Conservation d'une couverture complète dès qu'un artefact partagé est modifié
    (sécurité fonctionnelle inchangée).
  - Logiciel de sélection écrit en Python testé via `compileall`, simple à
    étendre pour de nouveaux dossiers cibles.
- **Négatives**
  - L'étape de planification ajoute un job préalable, augmentant légèrement la
    durée minimale avant la première validation.
  - Une logique de détection erronée pourrait ignorer un cas limite ; la revue de
    code surveille ce point.
- **Neutres/Mitigations**
  - Les chemins déclenchant une validation complète sont documentés dans le
    script et pourront être ajustés si nécessaire.
  - Un changement ne ciblant aucun profil/hôte explicite force une validation
    globale pour rester prudent.
