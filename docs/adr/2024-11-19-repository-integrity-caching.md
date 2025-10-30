# ADR: Mise en cache de la pipeline d'intégrité du dépôt

## Contexte

La pipeline GitHub Actions « Repository Integrity » installe à chaque exécution
les dépendances Python (linters Ansible), les collections Ansible et
`markdownlint-cli`. Malgré une exécution parallélisée par jobs, la phase de
configuration représentait ~60 % du temps total du job « Static analysis ».
Réduire ce temps améliore le feedback des revues de code sans introduire de
risque d'état mutable hors Git, conformément à notre approche GitOps.

## Décision

- Introduire `actions/cache@v4` pour conserver :
  - `~/.cache/pip` (dépendances `ansible/requirements.txt`).
  - `~/.ansible/collections` (collections définies dans
    `ansible/collections/requirements.yml`).
  - `~/.npm` (téléchargements `markdownlint-cli`).
- Dériver les clés de cache des manifestes versionnés (fichiers requirements) et
  de la version épinglée de `markdownlint-cli` pour garantir l'idempotence.
- Pinner `markdownlint-cli` en version `0.39.0` côté CI/CD et documentation
  développeur.

## Statut

Acceptée (2024-11-19).

## Conséquences

- Les jobs CI réutilisent les artefacts téléchargés, divisant par ~3 la phase
  d'installation lors des exécutions chaudes.
- La mise à jour d'une dépendance invalide automatiquement le cache correspondant
  grâce aux clés basées sur `hashFiles` ou la version épinglée.
- Les environnements locaux sont alignés sur la CI via la documentation
  (`npm install -g markdownlint-cli@0.39.0`).
- Aucun secret ni artefact mutable n'est stocké hors des chemins utilisateur
  standard, ce qui respecte l'approche GitOps et les bonnes pratiques de sécurité.
