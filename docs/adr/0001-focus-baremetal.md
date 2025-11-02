# ADR 0001: Depot recentré sur les serveurs bare metal

## Statut

Accepté

## Contexte

Le dépôt `ubuntu-autoinstall` a historiquement inclus plusieurs flux (bare metal,
VPS, provisioning applicatif). La stratégie GitOps impose désormais une chaîne
unique et auditée pour produire des images Ubuntu Autoinstall. Les dossiers VPS
et scripts associés complexifiaient la maintenance, augmentaient la surface des
linters et nuisaient à la lisibilité pour les nouveaux contributeurs.

## Décision

- Supprimer l'arborescence `vps/` et toute référence dans les makefiles,
  workflows et configurations Ansible.
- Documenter explicitement que le dépôt cible uniquement la génération d'ISO
  bare metal.
- Ajouter cette décision au référentiel documentaire (`docs/adr`).

## Conséquences

- **Positives** :

  - Réduction de la surface à maintenir et des pipelines CI.
  - Lisibilité accrue pour les contributeurs qui trouvent uniquement les
    composants bare metal.
  - Alignement avec la stratégie GitOps (une source de vérité, périmètre clair).

- **Négatives** :

  - Les utilisateurs du flux VPS doivent se référer à l'historique Git ou à un
    dépôt dédié.
  - Nécessité de créer un fork si un périmètre VPS doit renaître ultérieurement.

- **Suivi** :

  - Surveiller les issues/PR demandant le retour du flux VPS et envisager un
    dépôt séparé si besoin.
