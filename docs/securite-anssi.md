# Durcissement inspiré de l'ANSSI

Ce dépôt applique un profil basé sur les recommandations de l'ANSSI :
- **Recommandations de configuration d'un système GNU/Linux** (03/10/2022).
- **Recommandations relatives à l'administration sécurisée des SI**.

## Mesures appliquées automatiquement
- Chiffrement intégral LUKS2 (`aes-xts-plain64`, clé 512 bits, PBKDF `argon2id`) pour le disque système (`profiles/anssi.yml`). La passphrase est fournie par l'inventaire et jamais stockée dans l'ISO.
- Authentification SSH par clés uniquement (`PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PermitRootLogin no`).
- Compte administrateur nominatif sans mot de passe local (`lock-passwd: true`) et sudo journalisé (`/etc/sudoers.d/zz-logfile`).
- Désactivation des services non essentiels (avahi, cups, bluetooth) et masquage de `ctrl-alt-del`.
- Persistance des journaux (`/var/log/journal`) et archivage des logs d'installation (`/root/autoinstall-logs.tgz`).
- Marqueur `/etc/anssi-profile` avec date ISO-8601 et commit Git pour tracer la conformité.

## Gestion des secrets
- Chaque hôte possède `baremetal/inventory/host_vars/<host>/secrets.sops.yaml` chiffré via age/SOPS.
- `encrypt_disk_passphrase` doit être renseigné avant toute génération (`scripts/check_inventory.sh` vérifie la présence et la déchiffre via `sops -d`).
- Les secrets ne sont jamais copiés dans l'ISO : seul l'autoinstall final les consomme au moment de l'installation.

## Vérifications recommandées
1. `make gen HOST=<host>` : vérifie les templates et refuse une passphrase manquante.
2. `make iso HOST=<host>` : produit une ISO autonome avec NoCloud local.
3. `scripts/check_inventory.sh <host>` : contrôle rapide avant de lancer une build.
