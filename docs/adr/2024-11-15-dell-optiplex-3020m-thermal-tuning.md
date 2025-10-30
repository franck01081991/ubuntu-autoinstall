# ADR: Optimiser le profil Dell OptiPlex 3020M pour la stabilité thermique

## Contexte

- Les OptiPlex 3020M déployés disposent d'un CPU Intel Core i5-4590T (Haswell)
  et d'un chipset H81 dans un châssis ultra-compact avec une ventilation
  limitée.
- Les installations Ubuntu Server 24.04 reposaient jusqu'ici sur le profil
  minimal (`htop`, `irqbalance`) sans microcode ni services thermiques dédiés.
- Les tests de charge (stress-ng CPU/mémoire, compilation prolongée) montraient
  des pics de température supérieurs à 90 °C et un throttling agressif après
  quelques minutes.
- Le gabarit `user-data.j2` permet déjà d'activer `powertop-autotune` via une
  variable booléenne, mais le profil Dell ne l'exploitait pas et n'activait pas
  `thermald`.

## Décision

- Enrichir le profil matériel `dell-optiplex-3020m` avec :
  - installation par défaut de `intel-microcode`, `thermald`, `powertop`,
    `lm-sensors` et `linux-tools-generic` via `extra_packages` ;
  - activation automatique de `powertop-autotune` (`enable_powertop_autotune`)
    pour appliquer les réglages d'économie d'énergie au démarrage ;
  - nouvelle variable `enable_thermald` pour activer le service `thermald`
    directement depuis le gabarit autoinstall.
- Étendre `user-data.j2` afin d'activer/ démarrer `thermald` lorsque la variable
  `enable_thermald` est vraie.
- Documenter ces optimisations dans le README pour que les autres profils
  puissent répliquer le pattern.

## Statut

Acceptée (2024-11-15).

## Conséquences

- Les OptiPlex 3020M bénéficient d'une mise à jour microcode et d'un contrôle
  thermique actif dès l'installation, réduisant les risques de throttling et les
  arrêts intempestifs.
- Le gabarit autoinstall devient plus modulaire : n'importe quel profil ou host
  vars peut désormais activer `thermald` sans tâche Ansible supplémentaire.
- La CI continue de valider la génération des fichiers autoinstall pour le
  profil Dell tout en garantissant l'idempotence du rendu.
- Les opérateurs disposent d'un historique GitOps retraçant la décision
  d'optimisation matérielle, facilitant les audits.

## Références

- [Intel® Core™ i5-4590T Processor](https://www.intel.com/content/www/us/en/products/sku/80819/intel-core-i54590t-processor-6m-cache-up-to-3-00-ghz/specifications.html)
- [Dell OptiPlex 3020M Owner's Manual](https://dl.dell.com/topicspdf/optiplex-3020m-desktop_Owner's%20Manual_en-us.pdf)
- [Ubuntu thermald documentation](https://ubuntu.com/server/docs/service-thermald)
