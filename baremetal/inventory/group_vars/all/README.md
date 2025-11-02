# Group vars (SOPS)

Ce répertoire héberge les secrets chiffrés via SOPS/age pour les déploiements
bare metal.

- `disk_encryption.sops.yaml` : contient la variable `disk_encryption_passphrase`
  (ou toute clé `*_secret`) utilisée lors du rendu Autoinstall.
- Aucun secret ne doit être committé en clair. Utilisez `sops` pour éditer.
- Référencez ces variables depuis les `host_vars` via des expressions Jinja, par
  exemple `"{{ disk_encryption_passphrase }}"`.

> ℹ️ Ajoutez vos propres fichiers `.sops.yaml` si vous segmentez les secrets par
> site/équipe. Respectez le pattern défini à la racine du dépôt.
