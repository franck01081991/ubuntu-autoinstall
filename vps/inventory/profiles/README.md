# Profils VPS

Ce répertoire contient des profils matériels/logiques réutilisables pour la
chaîne VPS. Chaque profil décrit un ensemble minimal de variables autoinstall à
appliquer lors de l'exécution de `make vps/gen PROFILE=<profil>`.

- Placez vos fichiers dans `hardware/` et utilisez l'extension `.yml`.
- Les champs disponibles sont identiques à ceux des hôtes (`hostname`,
  `disk_device`, `netmode`, `ssh_authorized_keys`, etc.).
- Les valeurs peuvent être spécialisées par environnement (ex. `generic-kvm`,
  `generic-lxd`).
- Les secrets doivent rester chiffrés via SOPS dans `group_vars/`.

Reportez-vous à `hardware/generic-kvm.yml` comme point de départ.
