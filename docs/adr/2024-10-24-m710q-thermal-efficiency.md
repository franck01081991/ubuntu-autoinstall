# ADR: Optimiser le profil Lenovo M710q Tiny pour l'efficacité énergétique

## Contexte
- Les ThinkCentre M710q Tiny déployés disposent d'un CPU Intel Core i7-7700T (4C/8T, 2.9/3.8 GHz) avec un TDP de 35 W dans un châssis compact.
- La configuration standard reposait uniquement sur les paquets génériques (`htop`, `irqbalance`, etc.) sans microcode ni outils thermiques dédiés.
- Les sites utilisent deux SSD (NVMe + SATA) qui chauffent rapidement lors de charges prolongées (ex. compilation, workloads containerisés), ce qui augmente le throttling.

## Décision
- Ajouter une variable `extra_packages` consommée par le gabarit `autoinstall/templates/user-data.j2` pour installer des paquets spécifiques au matériel.
- Activer par défaut, pour le profil `lenovo-m710q`, l'installation de `intel-microcode`, `thermald`, `powertop`, `lm-sensors` et `linux-tools-generic`.
- Introduire la variable booléenne `enable_powertop_autotune` afin de créer/activer automatiquement un service systemd `powertop-autotune`.
- Mettre à jour le playbook `generate_autoinstall.yml` pour charger les variables du profil matériel référencé par un hôte (fusion GitOps entre profil et host vars).
- Documenter ces paramètres dans les README (FR/EN) pour que les autres profils puissent réutiliser le mécanisme.

## Statut
Acceptée (2024-10-24).

## Conséquences
- Les hôtes M710q reçoivent le microcode Intel et `thermald`, réduisant les risques de throttling et améliorant la stabilité.
- Le service `powertop-autotune` applique automatiquement les réglages d'économie d'énergie à chaque démarrage sans intervention manuelle.
- Le gabarit autoinstall devient plus flexible et peut accueillir d'autres optimisations matérielles en définissant `extra_packages` et `enable_powertop_autotune` dans n'importe quel profil ou hôte.
- La pipeline CI réutilise les profils matériels enrichis sans modification supplémentaire.

## Références
- [Lenovo ThinkCentre M710q Tiny PSREF](https://psref.lenovo.com/Product/ThinkCentre/ThinkCentre_M710q_Tiny)
- [Intel Powertop](https://01.org/powertop)
