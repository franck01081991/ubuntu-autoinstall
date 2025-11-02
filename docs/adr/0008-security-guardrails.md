# ADR-0008 — Renforcer la conformité sécurité CI/CD

## Statut

Accepté — 2025-02-14

## Contexte

Les contrôles automatiques se concentraient sur la génération d'autoinstall et
le linting, mais la détection de secrets reposait uniquement sur un script
maison et Trivy ne s'exécutait pas sur les Pull Requests. Cette configuration
laissait un angle mort pour les fuites accidentelles de secrets ou les erreurs
réintroduites avant merge, réduisant la conformité vis-à-vis des pratiques
SecOps/GitOps attendues.

## Décision

- Ajouter un workflow GitHub Actions dédié (`.github/workflows/secret-scanning.yml`)
  exécutant `gitleaks` sur chaque push, PR, exécution manuelle et via un cron
  hebdomadaire. Les rapports SARIF sont téléversés dans Code Scanning hors PR et
  archivés comme artefact.
- Conserver la configuration par défaut de `gitleaks` tout en fournissant
  `gitleaks.toml` pour ignorer uniquement les artefacts chiffrés SOPS et les
  sorties générées afin de limiter les faux positifs.
- Étendre le workflow `repository-integrity` pour que le scan `trivy fs` échoue
  aussi sur les Pull Requests (et pas uniquement sur `main`) dès qu'une faille
  `HIGH`/`CRITICAL` est détectée.
- Fournir une commande reproductible (`make secrets-scan`) afin d'exécuter
  localement les mêmes contrôles `gitleaks` que la CI.
- Mettre à jour la documentation (`README.md`) pour refléter les nouveaux
  garde-fous de sécurité et rappeler l'étendue des pipelines CI/CD.

## Conséquences

- Toute fuite de secret en clair est détectée par `gitleaks` avant merge, avec un
  rapport SARIF exploitable par l'équipe sécurité.
- Les contributeurs disposent d'une commande locale pour valider leur branche
  avant de pousser (`make secrets-scan`), facilitant l'itération.
- L'exécution de Trivy sur les PR garantit que les dépendances/configurations
  non conformes sont bloquées avant intégration sur `main`.
- Les pipelines CI/CD sont légèrement plus longs ; la planification hebdomadaire
  et la stratégie de concurrency limitent toutefois la charge.
- Les règles `gitleaks` devront être ajustées si de nouvelles zones chiffrées ou
  artefacts générés apparaissent.
