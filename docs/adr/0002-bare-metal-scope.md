# ADR 0002 — Focalisation sur le bare metal

## Contexte

Le dépôt avait brièvement intégré des composants IaC cloud (Terraform,
Kubernetes, secrets chiffrés) pour gérer l'infrastructure distante. Cette
orientation dépassait le besoin initial : produire et maintenir des images
autoinstall pour des hôtes physiques.

## Décision

- Supprimer les briques Terraform/Kubernetes du dépôt et revenir à un périmètre
  strictement **bare metal**.
- Conserver uniquement les automatisations nécessaires à la génération d'ISO
  seed/complet et aux playbooks Ansible associés.
- Documenter explicitement ce périmètre afin d'éviter la réintroduction
  accidentelle de dépendances cloud.

## Conséquences

- Les évolutions cloud devront vivre dans un dépôt séparé avec leur propre cycle
  GitOps.
- Les tests CI se concentrent sur la génération d'artefacts autoinstall et la
  validation Ansible/YAML.
- Les contributeurs disposent d'un socle épuré pour étendre les profils matériels
  sans se soucier d'IaC distant.
