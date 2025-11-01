# 0013 — Réactiver lint YAML/Ansible via workflow GitHub Actions

- Date: 2025-02-19
- Status: Accepted
- Deciders: Platform Team
- Tags: ci, github-actions, lint, governance

## Contexte

La génération Autoinstall a échoué pour le profil `thinkcentre1` à cause d'une
ligne YAML mal formatée (`-#` en tête de fichier) dans
`ansible/playbooks/common/generate_autoinstall.yml`. Le dépôt ne disposait plus
d'une automatisation pour détecter ces erreurs depuis l'abandon temporaire des
workflows GitHub Actions (ADR-0012). Seul `make lint` local exécutait
`yamllint` et `ansible-lint`, laissant la CI sans garde-fou systématique.

## Décision

- Introduire un workflow GitHub Actions (`.github/workflows/lint.yml`) dédié à
  l'analyse statique.
- Exécuter `yamllint` sur les répertoires `ansible/` et `baremetal/` pour
  détecter les erreurs de syntaxe YAML.
- Exécuter `ansible-lint` sur les playbooks Autoinstall partagés pour garantir
  la conformité Ansible.
- Mutualiser l'installation des dépendances Python via `actions/setup-python`
  (`python:3.11`) et le cache pip natif de GitHub Actions.

## Conséquences

- **Positives**
  - Les erreurs de syntaxe YAML ou de style Ansible sont détectées avant merge.
  - La CI reste GitOps-first : toute correction passe par commit/PR.
  - Le pipeline est léger (<2 jobs) et repose sur des outils déjà documentés.
- **Négatives**
  - Un léger allongement des pipelines (`pip install` au démarrage).
- **Mitigations**
  - Le cache `pip` accélère les exécutions suivantes.
  - `make lint` conserve la même couverture localement pour reproduire la CI.

## Liens

- ADR-0012 — Désactivation complète de GitHub Actions
- README.md — section "Gouvernance, sécurité et conformité"
