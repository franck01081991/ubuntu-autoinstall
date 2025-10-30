# ADR: Profil Lenovo M710q Tiny i7 + 16 Go et mémoire compressée

## Contexte

- Les sites bare metal exploitent des ThinkCentre M710q Tiny avec un processeur
  Intel Core i7-7700T (4 cœurs / 8 threads) et 16 Go de DDR4-2400 après mise à
  niveau matérielle.
- Les workloads containerisés et CI locale génèrent des pics d'utilisation de
  mémoire et d'I/O qui provoquaient du swap disque agressif sur les SSD.
- Le profil `lenovo-m710q` embarquait déjà des optimisations thermiques, mais
  n'exposait pas la configuration CPU/RAM ni de stratégie de swap adaptée au
  nouveau gabarit mémoire.

## Décision

- Documenter explicitement le matériel validé via une clé `hardware_specs`
  (CPU, architecture, threads, mémoire totale/type/vitesse) pour faciliter les
  rapports d'inventaire GitOps.
- Étendre le profil `lenovo-m710q` avec `systemd-zram-generator` activé par
  défaut (`enable_zram_generator: true`) et une configuration
  (`zram_generator_config`) dimensionnée à 50 % de la RAM avec une limite à
  8 Go, compression `zstd` et priorité de swap à 100.
- Activer systématiquement `thermald` (`enable_thermald: true`) afin de garantir
  que le démon soit lancé post-installation et tire parti des paquets déjà
  présents.
- Mettre à jour les README (FR/EN) pour décrire les nouvelles variables et le
  comportement de la mémoire compressée.

## Statut

Acceptée (2024-11-22).

## Conséquences

- Les inventaires GitOps disposent d'attributs CPU/RAM exploitables pour les
  rapports d'actifs et l'automatisation avale.
- Le swap compressé en RAM réduit l'usure des SSD tout en maintenant une
  réserve de mémoire pour les pics de charge, ce qui stabilise les pipelines CI
  locaux.
- `thermald` est systématiquement démarré, alignant le comportement avec les
  autres profils matériels optimisés.
- La pipeline CI reste inchangée : les nouveaux champs YAML n'impactent pas
  les autres profils mais deviennent disponibles pour de futures validations.

## Références

- [systemd-zram-generator][systemd-zram-generator]
- [Lenovo ThinkCentre M710q Tiny PSREF][psref]

[systemd-zram-generator]: https://github.com/systemd/zram-generator
[psref]: https://psref.lenovo.com/Product/ThinkCentre/ThinkCentre_M710q_Tiny
