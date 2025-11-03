# 0013 — Inventaire local et ISO multi-hôtes

- Date: 2025-02-28
- Status: Accepted
- Deciders: Platform Team
- Tags: inventory, secrets, iso

## Contexte

Le dépôt versionnait jusqu'ici des répertoires `baremetal/inventory/host_vars/`
contenant parfois des secrets chiffrés avec SOPS. Malgré le chiffrement, la
politique de sécurité impose désormais que les secrets et variables spécifiques
aux environnements ne résident plus dans GitHub. En parallèle, les équipes
techniques ont exprimé le besoin de générer des images Autoinstall capables de
cibler plusieurs machines via un menu GRUB unique.

## Décision

- Introduire un overlay local `baremetal/inventory-local/` (ignoré par Git) pour
  stocker `host_vars/` et `hosts.yml`. Les scripts et playbooks recherchent
  d'abord cet overlay puis retombent sur les exemples versionnés.
- Remplacer la copie de secrets d'exemple par un modèle
  `baremetal/inventory/examples/secrets.template.yaml` à chiffrer manuellement
  via SOPS avant renommage en `secrets.sops.yaml`.
- Étendre les playbooks Ansible, les scripts Shell et l'assistant
  `iso_wizard.py` afin qu'ils détectent automatiquement l'overlay local.
- Ajouter une cible `make baremetal/multiiso` et un script Python
  `baremetal/scripts/make_multi_iso.py` qui agrègent plusieurs hôtes dans un ISO
  multi-entrées GRUB.
- Publier un CLI `scripts/iso_manager.py` pour orchestrer les rendus et la
  construction des ISO (seed, full, multi).
- Documenter le flux multi-hôtes (`docs/multi-host-iso.md`) et mettre à jour les
  guides existants pour pointer vers `inventory-local/`.
- Supprimer les workflows GitHub Actions résiduels (`ci.yml`, `lint.yml`) en
  cohérence avec l'ADR 0012.

## Conséquences

- **Positives**
  - Aucun secret, même chiffré, ne transite par GitHub. Les inventaires locaux
    peuvent être montés via des volumes sécurisés.
  - Le CLI `iso_manager.py` facilite l'automatisation GitOps en encapsulant les
    cibles Make idempotentes.
  - Les ISO multi-hôtes réduisent le nombre de supports à transporter pour les
    interventions terrain.
- **Négatives**
  - Chaque collaborateur doit provisionner `inventory-local/` en amont (script
    `make baremetal/host-init` ou `scripts/new_host.py`).
  - Les tests automatisés ne peuvent plus s'appuyer sur un inventaire complet en
    l'absence de secrets ; ils doivent injecter un overlay temporaire.
- **Mitigations**
  - Les scripts `bootstrap-host.sh`, `iso_wizard.py` et `iso_manager.py`
    vérifient la présence de l'overlay et guident l'opérateur.
  - La documentation (FR/EN) souligne explicitement les nouvelles étapes et
    fournit des modèles prêts à l'emploi.
