# ADR: Séparation des chaînes ISO bare metal et provisioning VPS

## Contexte
Le dépôt mélangeait la génération des ISO Ubuntu autoinstall (ciblant le bare metal) et le provisioning applicatif des VPS. Les VPS ne peuvent pas être reprovisionnés proprement via ISO (accès console et support virtuel indisponibles), ce qui rendait la présence d'une chaîne ISO dédiée inutile et source de confusion. De plus, les chemins `inventory/` étaient partagés entre ces deux usages, compliquant les inventaires et les déclencheurs CI.

## Décision
- Introduire deux racines indépendantes : `baremetal/` pour la génération d'ISO et `vps/` pour l'automatisation applicative.
- Déplacer les inventaires, scripts et playbooks ISO sous `baremetal/` et scoper la chaîne VPS à `vps/`.
- Actualiser le `Makefile`, la documentation et la CI afin de refléter les nouveaux chemins et d'éviter tout couplage ISO ↔ VPS.
- Clarifier dans la documentation que les VPS sont gérés exclusivement via Ansible (sans ISO).

## Statut
Acceptée (2024-11-07).

## Conséquences
- Les chemins sont explicitement séparés, ce qui simplifie la lecture du dépôt et les déclencheurs CI/CD (GitHub Actions ne rebuild plus les ISO quand seul le provisioning VPS évolue).
- Les inventaires bare metal vivent sous `baremetal/inventory/` ; les variables VPS sont centralisées sous `vps/inventory/` avec secrets chiffrés via SOPS.
- Les commandes Make deviennent explicites (`make baremetal/*` et `make vps/*`), réduisant le risque d'exécuter la mauvaise chaîne.
- Toute nouvelle automatisation (ex. Terraform, Helm) pourra se brancher sur la racine concernée sans perturber l'autre périmètre.
