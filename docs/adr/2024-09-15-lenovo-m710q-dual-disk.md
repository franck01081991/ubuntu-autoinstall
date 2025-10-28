# ADR: Unifier le profil Lenovo M710q Tiny et gérer la double baie NVMe + SATA

## Contexte
- Les profils matériels `lenovo-m710q-nvme` et `lenovo-m710q-sata` du dépôt décrivaient le même châssis ThinkCentre M710q Tiny avec des variantes de disques.
- Chaque ThinkCentre M710q Tiny dispose en réalité d'un slot M.2 NVMe et d'une baie 2,5" SATA selon la fiche technique Lenovo (PSREF).
- Maintenir deux profils distincts compliquait la matrice CI/CD et créait des divergences entre hôtes alors que le matériel est identique.

## Décision
- Remplacer les deux profils par un profil unique `lenovo-m710q` qui déclare à la fois le disque NVMe principal et le SSD SATA supplémentaire.
- Étendre le gabarit `user-data.j2` pour prendre en charge la liste `additional_disk_devices` et agréger tous les disques dans le même groupe de volumes LVM (`vg0`).
- Mettre à jour la documentation (FR/EN) et la pipeline GitHub Actions afin de référencer le nouveau profil unique.

## Statut
Acceptée (2024-09-15).

## Conséquences
- Le stockage est provisionné de manière homogène sur tout M710q : le NVMe porte le boot/EFI tandis que le(s) SSD SATA rejoint(ent) le VG LVM.
- Les hôtes héritent de la configuration disque via le profil matériel et n'ont plus besoin de doubler la variable `disk_device`.
- La matrice CI est simplifiée (`lenovo-m710q`, `dell-optiplex-3020`) tout en reflétant fidèlement le hardware réellement déployé.
- La variable `additional_disk_devices` devient disponible pour d'autres profils si nécessaire.

## Références
- [Lenovo ThinkCentre M710q Tiny Product Specifications Reference](https://psref.lenovo.com/Product/ThinkCentre/ThinkCentre_M710q_Tiny)
