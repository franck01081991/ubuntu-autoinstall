# ADR 0011 — Inventaire matériel automatisé

## Statut

Accepté

## Contexte

La collecte d'informations matérielles se faisait jusqu'ici manuellement (notes
technicien, commandes ad hoc sur chaque hôte). Résultat : profils matériels
incomplets (`hardware_model`, disques, NIC) et absence de spécifications CPU/RAM
consolidées. Cette situation compliquait la maintenance de l'inventaire GitOps
et empêchait toute validation automatique en CI.

## Décision

Nous introduisons un flux de découverte matériel idempotent :

- un playbook Ansible `discover_hardware.yml` collecte `ansible_facts`, `lsblk`
  et `ip -j link` ;
- le script `scripts/discover_hardware.py` exécute ce playbook et écrit un cache
  JSON local sous `.cache/discovery/` ;
- un contrôle CI `scripts/ci/check_inventory_consistency.py` vérifie la présence
  de `hardware_model`, `disk_device`, `nic`, des spécifications CPU/RAM et
  l'alignement des `netmode` entre profils et hôtes ;
- la cible `make baremetal/discover` facilite l'adoption du flux pour les
  techniciens.

## Conséquences

- **Documentation** : README (FR/EN), guide débutant, fiche mémo et nouvel ADR
  décrivent le flux automatisé et le cache `.cache/discovery/`.
- **CI/CD** : `repository-integrity.yml` invoque le nouveau script de cohérence
  et ajoute le playbook de découverte à `ansible-lint`.
- **Inventaire** : tous les profils matériels doivent définir les champs
  obligatoires (`hardware_model`, `disk_device`, `nic`, `hardware_specs` CPU/RAM,
  `netmode`). Des profils distincts sont créés lorsque des `netmode` différents
  coexistent pour un même matériel.
- **Exploitation** : les techniciens disposent d'une source de vérité JSON pour
  alimenter ou auditer l'inventaire avant de pousser une PR.

## Alternatives considérées

- **Scripts shell ad hoc** : écartés, absence d'idempotence et de validation en
  CI.
- **Découverte 100 % manuelle** : non retenue, car source d'erreurs et
  incompatible avec la traçabilité GitOps.
- **Ansible facts uniquement** : rejeté, les commandes `lsblk` et `ip -j link`
  fournissent des détails indispensables (disques additionnels, alias réseau).

## Actions

1. Ajouter le playbook de découverte et le script CLI associé.
2. Étendre le Makefile (`make baremetal/discover`).
3. Mettre à jour la documentation utilisateur et ajouter cet ADR.
4. Renforcer la CI (`ansible-lint`, contrôle de cohérence inventaire).

## Considérations de sécurité

- Les caches `.cache/discovery/*.json` restent locaux et ignorés par Git.
- L'exécution Ansible se fait en lecture seule (`lsblk`, `ip link`).
- Aucun secret n'est exposé : seules des caractéristiques matérielles sont
  collectées.

## Références

- `baremetal/ansible/playbooks/discover_hardware.yml`
- `scripts/discover_hardware.py`
- `scripts/ci/check_inventory_consistency.py`
- `.github/workflows/repository-integrity.yml`
