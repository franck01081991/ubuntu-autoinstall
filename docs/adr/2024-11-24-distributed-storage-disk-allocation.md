# ADR: Réserver les disques supplémentaires pour le stockage distribué

## Contexte

- Les clusters bare metal doivent exposer plusieurs disques: le premier dédié au
  système et les suivants à des couches de stockage distribué (Ceph, Gluster,
  MinIO, etc.).
- L'ADR du 2024-09-15 (« lenovo-m710q dual disk ») agrégait tous les disques
  dans un volume LVM unique (`vg0`), empêchant l'usage brut par les solutions de
  stockage.
- Les retours d'exploitation indiquent que les noeuds multi-disques doivent
  conserver les disques secondaires intacts afin qu'une stack de stockage puisse
  les consommer (LVM local, RAID matériel, Ceph OSD, etc.).

## Décision

- L'installateur autoinstall/curtin doit toujours provisionner l'OS sur le
  premier disque (`disk_device`).
- Les disques listés dans `additional_disk_devices` sont déclarés avec
  `preserve: true` afin de n'être ni effacés ni ajoutés au groupe de volumes
  système.
- La documentation (`README*`) est mise à jour pour refléter le fait que ces
  disques sont réservés aux couches de stockage externes.
- L'ADR 2024-09-15 est marqué comme « Superseded » par cette nouvelle politique.

## Statut

Acceptée (2024-11-24).

## Conséquences

- Les installations restent idempotentes : Curtin configure uniquement le disque
  système, les autres restent disponibles pour être gérés par une stack
  d'orchestration (Ceph, Gluster, Longhorn, etc.).
- Les playbooks/roles en aval doivent, le cas échéant, préparer les disques
  supplémentaires (partitionnement, RAID) après installation.
- Les tests de génération d'autoinstall pour les profils multi-disques doivent
  vérifier que les disques supplémentaires sont référencés mais préservés.
- Les opérateurs bénéficient d'une séparation stricte entre disque système et
  disques de données, facilitant les upgrades ou réinstallations sans effacer la
  couche de stockage distribuée.

## Références

- [Ubuntu Autoinstall Storage Configuration](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html#storage)
- ADR 2024-09-15 (« lenovo-m710q dual disk »)
