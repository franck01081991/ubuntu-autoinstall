# ADR 0009 — Partitionnement ANSSI pour Ubuntu Autoinstall

## Statut

Accepté

## Contexte

Les déploiements bare metal destinés à des environnements sensibles doivent appliquer
un découpage disque aligné sur les recommandations de l’ANSSI (compartimentation des
points de montage, chiffrement complet du disque, séparation des journaux et espaces
temporaires). La base actuelle d’Autoinstall ne propose pas encore de gabarit prêt
à l’emploi pour ce cas d’usage, obligeant chaque équipe à maintenir des overrides
Curtin spécifiques.

## Décision

Nous introduisons un layout `anssi-luks-lvm` rendu par Curtin :

- GPT + LUKS (`dm-crypt`) chiffrant le volume LVM principal.
- Volumes logiques dédiés pour `/`, `/var`, `/var/log`, `/var/log/audit`, `/tmp`,
  `/var/tmp`, `/home`, `/srv` et le swap.
- Options de montage durcies (`noatime`, `nodev`, `nosuid`, `noexec` selon le point
  de montage).
- Commandes tardives garantissant les permissions (`/var/log/audit`, sticky bit).

Les équipes activent ce layout via `storage_layout: anssi-luks-lvm` dans leurs profils matériels existants pour faciliter les tests et la génération des ISO. Le redimensionnement automatique étend les volumes vers les tailles recommandées et consacre l’espace résiduel à `/srv`.

## Conséquences

- Documentation : ajout d’un guide de partitionnement détaillé et mise à jour du
  README pour expliquer l’activation du layout sur les profils existants.
- Sécurité : la passphrase LUKS reste gérée via SOPS ; l’absence de passphrase
  déclenche une erreur (`mandatory`).
- CI/CD : la génération Autoinstall et les linters existants couvrent automatiquement
  le nouveau layout.
- Exploitation : toute machine utilisant ce profil doit disposer d’un disque NVMe
  suffisamment dimensionné pour atteindre les tailles recommandées ; l’espace
  supplémentaire bénéficie automatiquement à `/home` puis `/srv`.

## Alternatives considérées

- **Overrides par hôte** : rejeté car difficile à maintenir et non mutualisé.
- **ZFS natif** : non retenu faute de recommandation ANSSI officielle sur Ubuntu
  serveur, et complexité de maintenance dans Curtin.

## Actions

1. Ajouter le template `anssi-luks-lvm`.
2. Créer la documentation et l’ADR.
3. Documenter l’activation du layout sur les profils matériels existants.
4. Communiquer le plan de tests (Autoinstall + VM de validation).

## Considérations de sécurité

- Le chiffrement LUKS impose la présence de la passphrase (`mandatory`) afin
  d’empêcher tout rendu incomplet.
- Les points de montage critiques (`/tmp`, `/var/tmp`, `/var/log`, `/var/log/audit`)
  sont protégés via `nosuid`, `noexec`, `nodev` et des permissions explicites.
- Les opérateurs doivent vérifier la rotation des passphrases via SOPS/age.

## Références

- Recommandations ANSSI « Configuration sécurisée des systèmes GNU/Linux ».
- Documentation Ubuntu Curtin et Autoinstall.
