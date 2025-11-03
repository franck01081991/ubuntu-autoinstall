# CI/CD

Le workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) automatise les contrôles suivants :

1. Installation des dépendances (make, ansible, sops, age, yamllint, gitleaks).
2. Création d'un hôte de démonstration (`make new-host HOST=ci-demo DISK=/dev/sda`).
3. Chiffrement de `encrypt_disk_passphrase` via SOPS (clef age éphémère stockée uniquement pendant le job).
4. Génération de l'autoinstall (`make gen HOST=ci-demo`).
5. Analyse secrets (`gitleaks detect --no-git --source .`).
6. Lint YAML (`yamllint .`).
7. Publication des artefacts (`user-data`, `meta-data`) pour inspection.

L'objectif est de garantir la reproductibilité (ISO unique, inventaire obligatoire) et d'empêcher toute génération sans passphrase chiffrée.
