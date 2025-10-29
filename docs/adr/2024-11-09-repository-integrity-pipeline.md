# ADR: Pipeline d'intégrité du dépôt

## Contexte

Les contrôles syntaxiques (YAML, Ansible, Shell) étaient déclenchés
ponctuellement via `make vps/lint`, sans couverture globale du dépôt. Aucun scan
de configuration/secrets n'était automatisé et les contributions reposaient sur
des exécutions manuelles. Cette approche ne garantissait pas l'idempotence GitOps
exigée : une régression sur un profil bare metal, un script shell ou la
documentation pouvait passer en revue sans alerte.

## Décision

- Ajouter un workflow GitHub Actions `.github/workflows/repository-integrity.yml`
  déclenché sur chaque push/PR.
- Décomposer la pipeline en deux jobs complémentaires :
  - **Static analysis** (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`)
    pour l'ensemble du dépôt.
  - **Trivy configuration scan** (`trivy fs` avec `--security-checks
    config,secret` et seuil **HIGH/CRITICAL**).
- Introduire la cible `make lint` pour reproduire localement les contrôles
  statiques et documenter la marche à suivre.
- Étendre la documentation (FR/EN) et le référentiel ADR pour acter cette
  exigence d'intégrité.

## Statut

Acceptée (2024-11-09).

## Conséquences

- Chaque contribution est validée automatiquement contre les linters et le scan
  de sécurité, évitant les entrées en production non conformes.
- Les développeurs disposent d'une commande unique (`make lint`) pour aligner
  leur environnement local sur la CI.
- `markdownlint` et `shellcheck` deviennent des dépendances de développement
  explicites ; leur absence déclenche un échec clair.
- Trivy fournit une visibilité continue sur les secrets accidentellement
  commités ou les configurations risquées.
- Les dépendances Python critiques (ex. `ansible-core`) sont maintenues à jour
  pour satisfaire les contrôles de sécurité automatisés (CVE-2024-8775 corrigée
  via la version 2.16.13).
