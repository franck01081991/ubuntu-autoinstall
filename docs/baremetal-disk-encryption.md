# Chiffrement du disque système (LUKS)

Ce guide décrit comment activer le chiffrement intégral du disque système
(LUKS + LVM) durant l'installation Ubuntu Autoinstall générée par ce dépôt.
Toutes les étapes restent **GitOps** : seules des modifications versionnées et
revues alimentent la génération des ISO.

## Vue d'ensemble

- **Moteur** : `dm-crypt` (LUKS) encapsulant un volume LVM (`vg0/lv_root`).
- **Passphrase** : stockée dans `SOPS` sous
  `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.
- **Activation** : variable `disk_encryption.enabled: true` dans les `host_vars`
  ou profils matériels.
- **Compatibilité** : si `enabled` est `false` (valeur par défaut), le rendu
  conserve le partitionnement LVM non chiffré existant.

## Pré-requis

1. Une paire de clés `age` dédiée au dépôt (publique dans `.sops.yaml`, privée
   stockée hors dépôt).
2. Le binaire `sops` (installable via `scripts/install-sops.sh`).
3. Un `host_vars` ou profil matériel à sécuriser.

> ⚠️ Ne stockez jamais la passphrase en clair dans le dépôt, la CI ou les
> journaux. Toute donnée sensible doit passer par `sops`.

## 1. Définir la passphrase avec SOPS

Créez (ou mettez à jour) `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`
via `sops` :

```bash
sops baremetal/inventory/group_vars/all/disk_encryption.sops.yaml
```

Insérez une structure similaire :

```yaml
# Ce fichier est chiffré par SOPS. Exemple de contenu une fois déchiffré :
disk_encryption_passphrase: "Phrase de passe très forte"
```

Sauvegardez : `sops` chiffre automatiquement le fichier pour tous les
`recipients` définis dans `.sops.yaml`.

## 2. Activer le chiffrement pour un hôte

Dans `baremetal/inventory/host_vars/<hote>.yml`, ajoutez :

```yaml
disk_encryption:
  enabled: true
  passphrase: "{{ disk_encryption_passphrase }}"
  device_name: cryptroot            # optionnel, défaut `cryptroot`
  cipher: aes-xts-plain64           # optionnel
  keysize: 512                      # optionnel
  hash: sha512                      # optionnel
  pbkdf:                            # optionnel
    type: argon2id
    time: 5
    memory: 1048576
    threads: 4
```

> 💡 Définissez uniquement les champs nécessaires. Les paramètres optionnels sont
> transmis tels quels au bloc `dm_crypt` de Curtin.

## 3. Regénérer l'autoinstall

```bash
make baremetal/gen HOST=<hote>
```

La CI/commande échoue si `disk_encryption.enabled: true` mais que la passphrase
est absente (grâce au filtre `mandatory`). Vérifiez ensuite que le fichier
`user-data` contient :

```yaml
- type: dm_crypt
  id: luks-root
  volume: luks-root-partition
  dm_name: cryptroot
  key: "********"
```

Les volumes LVM montés (`/boot`, `/`, `/boot/efi`) restent inchangés.

## 4. Tests et validation

- `make baremetal/gen HOST=<hote>` : vérifie la compilation Autoinstall.
- `make lint` : contrôle la cohérence YAML/Jinja.
- Booter l'ISO générée sur un environnement de test et valider :
  1. Saisie de la passphrase LUKS pendant l'installation.
  2. Déchiffrement automatique au premier boot.

## 5. Rotation de la passphrase

1. Mettez à jour `disk_encryption_passphrase` via `sops`.
2. Regénérez les fichiers (`make baremetal/gen`).
3. Déployez la nouvelle ISO et planifiez la rotation (redéploiement complet ou
   re-chiffrement manuel selon votre politique).

## 6. Dépannage

- **Erreur `mandatory`** : la passphrase est absente ou vide. Vérifiez votre
  fichier SOPS et l'inclusion `passphrase: "{{ disk_encryption_passphrase }}"`.
- **CI en échec** : assurez-vous que la clé publique `age` renseignée dans
  `.sops.yaml` est valide. Sans quoi `sops` ne peut pas chiffrer/déchiffrer.
- **Besoin d'autres volumes chiffrés** : adaptez le template en suivant le même
  schéma `dm_crypt` + `lvm_volgroup`.

## Bonnes pratiques

- Utilisez une passphrase longue et générée aléatoirement (p. ex. `pwgen 32`).
- Conservez la clé privée `age` dans un gestionnaire de secrets.
- Réalisez des tests de restauration : assurez-vous de pouvoir booter et
  déchiffrer une machine déployée avec cette configuration.
- Documentez toute rotation de secrets via une PR incluant un changelog.

---

Pour plus de détails sur la mise en œuvre, consultez également l'ADR
`docs/adr/0003-os-disk-encryption.md`.
