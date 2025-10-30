# ADR: Maintenir des disques indépendants par machine

## Contexte

- Le gabarit `baremetal/autoinstall/templates/user-data.j2` agrégait jusqu'ici
  tous les disques déclarés (`disk_device` + `additional_disk_devices`) dans un
  volume logique unique (`vg0`).
- Cette approche complexifie l'exploitation : diagnostics plus difficiles,
  dépendance à LVM sur toutes les cibles et absence de séparation claire entre
  le disque système et les disques de données.
- La demande produit est de conserver chaque disque autonome afin d'éviter les
  effets de bord lors du remplacement ou de la maintenance d'un disque.

## Décision

- Ne provisionner LVM sur aucun disque dans le scénario par défaut.
- Partitioner le disque principal (`disk_device`) pour `/boot/efi`, `/boot` et
  `/` (ext4) uniquement.
- Formater chaque disque additionnel (`additional_disk_devices`) en ext4 et les
  monter indépendamment sous `/mnt/diskX` (`disk1`, `disk2`, etc.).
- Documenter ce comportement dans les READMEs (FR/EN) et consigner la décision
  dans les ADR.

## Statut

Acceptée (2024-11-26).

## Conséquences

- Les machines disposent d'un disque système isolé et de disques de données
  indépendants, simplifiant l'observabilité et le remplacement à chaud.
- L'ancienne ADR sur l'agrégation LVM (`2024-09-15-lenovo-m710q-dual-disk`) est
  supplantée par la présente décision.
- Les scripts et playbooks qui s'appuyaient sur le VG `vg0` doivent être adaptés
  pour consommer les nouveaux points de montage `/mnt/diskX`.

## Références

- [Ubuntu autoinstall storage configuration](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html#storage)
