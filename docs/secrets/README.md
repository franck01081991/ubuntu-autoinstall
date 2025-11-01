# Secrets GitOps (SOPS)

Ce répertoire référence les emplacements attendus pour les secrets chiffrés via
[SOPS](https://github.com/getsops/sops) et la clé `age` partagée par l'équipe.
Aucun secret en clair ne doit être committé. Ajoutez votre clé publique `age`
dans `.sops.yaml` (section `key_groups`) et distribuez la clé privée via les
secrets CI/CD (`SOPS_AGE_KEY`). Pour un atelier, exécutez
`./scripts/bootstrap-demo-age-key.sh` afin d’installer l’identité `age`
partagée par défaut.

## Fichiers attendus

- `baremetal-luks.sops.yaml` : contient la clé `disk_luks_passphrase` utilisée
  pour remplacer le champ `SOPS_DECRYPTED_DISK_PASSPHRASE` du profil
  `baremetal/autoinstall/secure-ubuntu-22.04.yaml`.
- `../baremetal/inventory/host_vars/<hote>/secrets.sops.yaml` : secrets
  spécifiques à chaque machine (`password_hash`, `ssh_authorized_keys`,
  jetons API éventuels).

Initialisez le fichier ainsi :

```bash
sops --age <AGE_RECIPIENT> --encrypt --input-type yaml --output-type yaml \
  --output docs/secrets/baremetal-luks.sops.yaml <(cat <<'YAML'
disk_luks_passphrase: "votre-passphrase-super-secrete"
YAML
)
```

La passphrase sera ensuite injectée via la CI/CD (voir README principal).
