# ADR: Hardware-profile based CI for autoinstall validation

## Contexte

La pipeline GitHub Actions `build-iso` exécutait jusqu'ici la génération
d'autoinstall pour chaque site ainsi qu'un VPS. Cette approche augmentait la
durée d'exécution (multiplication des matrices), obligeait à recréer les mêmes
artefacts pour des variantes matérielles identiques et conservait un scénario
VPS qui ne relève pas du périmètre des ISO matérielles.

## Décision

- Introduire des profils matériels versionnés dans
  `baremetal/inventory/profiles/hardware/`.
- Adapter le playbook `generate_autoinstall.yml` et le `Makefile` afin
  d'accepter `PROFILE=<profil>` pour générer les artefacts correspondants.
- Simplifier la matrice CI sur les profils matériels (`lenovo-m710q-nvme`,
  `lenovo-m710q-sata`, `dell-optiplex-3020m`) et supprimer la cible VPS.
- Ajouter des caches GitHub Actions pour `~/.cache/pip` et `.cache/` (ISO
  téléchargées) afin d'accélérer la pipeline.

## Statut

Acceptée (2024-09-08).

## Conséquences

- La CI valide le processus de génération autoinstall pour chaque modèle de
  matériel couvert tout en réduisant le temps de traitement.
- Les sites/hôtes continuent à disposer de leurs variables dédiées dans
  `baremetal/inventory/host_vars/`, avec un lien vers le profil matériel de
  référence.
- L'intégration de nouveaux modèles se fait en ajoutant un fichier YAML dans
  `baremetal/inventory/profiles/hardware/` et en l'ajoutant à la matrice CI.
- Le téléchargement de l'ISO officielle est conservé mais désormais mis en cache
  pour limiter l'usage réseau.
- La maintenance des scénarios VPS bascule intégralement sur l'automatisation
  Ansible post-installation.
