# Variables d'inventaire Autoinstall

Ce guide récapitule les variables à renseigner avant de générer un ISO (seed ou complet).
Les valeurs sont réparties entre les fichiers `host_vars/<HÔTE>/main.yml`,
`host_vars/<HÔTE>/secrets.sops.yaml` et les profils matériels
`profiles/hardware/<PROFIL>.yml`.

## Rappel sur la hiérarchie

1. `profiles/hardware/<PROFIL>.yml` définit les valeurs par défaut communes à un même matériel
   (modèle, disque, interface réseau, optimisations, etc.).
2. `host_vars/<HÔTE>/main.yml` sélectionne le profil matériel et peut surcharger des valeurs
   spécifiques à l'hôte (nom DNS, réseau, stockage, options). Les surcharges priment sur le profil.
3. `host_vars/<HÔTE>/secrets.sops.yaml` contient **uniquement** les secrets (hash de mot de passe,
   clés SSH, passphrases). Ce fichier est toujours chiffré avec SOPS + age.

## `host_vars/<HÔTE>/main.yml`

| Clé | Obligatoire | Description |
|-----|-------------|-------------|
| `hostname` | Oui | Nom d'hôte final injecté dans `identity.hostname`. |
| `hardware_profile` | Oui | Nom du fichier `profiles/hardware/<PROFIL>.yml` à utiliser. |
| `netmode` | Oui | Mode réseau : `dhcp` ou `static`. Doit rester aligné avec le profil matériel. |
| `nic` | Non (si fourni par le profil) | Interface réseau à configurer. Utile pour surcharger un profil. |
| `disk_device` | Non (si fourni par le profil) | Disque système (`/dev/sda`, `/dev/nvme0n1`, etc.). |
| `additional_disk_devices` | Non | Liste de disques supplémentaires laissés intacts. |
| `management_interface` | Non | Interface dédiée à la gestion hors bande si besoin. |
| `locale` | Non | Locale à appliquer (`fr_FR.UTF-8` par défaut). |
| `keyboard_layout` / `keyboard_variant` | Non | Disposition clavier installateur. |
| `apt_primary_uri` / `apt_primary_arches` | Non | Miroir APT personnalisé et architectures autorisées. |
| `extra_packages` | Non | Paquets supplémentaires à installer. |
| `ansible_repo_url` | Non | URL Git du dépôt Ansible exécuté au premier démarrage (`https://` ou `ssh://`). |
| `ansible_inventory_limit` | Non | Valeur passée à `ansible-playbook --limit` (défaut : `hostname`). |
| `storage_swap_size` | Non | Taille du swap en Mio (0 par défaut). |
| `storage_config_override` | Non | Remplace entièrement la section `storage.config` (YAML brut). |
| `storage_additional_late_commands` | Non | Liste de commandes `late-commands` à ajouter. |
| `enable_powertop_autotune` / `enable_thermald` / `enable_zram_generator` | Non | Active des optimisations d'alimentation/thermiques proposées par certains profils. |
| `zram_generator_config` | Non | Paramètres détaillés du générateur ZRAM (`swap.zram-fraction`, etc.). |
| `disk_encryption.enabled` | Non | `true` pour activer LUKS (nécessite une passphrase dans les secrets). |
| `disk_encryption.device_name` / `cipher` / `keysize` / `hash` / `pbkdf` | Non | Options avancées LUKS si `enabled: true`. |

### Réseau statique

Lorsque `netmode: static` est utilisé, ajouter les clés suivantes :

| Clé | Description |
|-----|-------------|
| `ip` | Adresse IPv4 de l'hôte. |
| `cidr` | Préfixe CIDR (ex : `24`). |
| `gw` | Passerelle par défaut. |
| `dns` | Liste YAML ou JSON de serveurs DNS (ex : `["1.1.1.1", "9.9.9.9"]`). |

Ces valeurs alimentent directement la section `network:` du `user-data`.

## `profiles/hardware/<PROFIL>.yml`

| Clé | Obligatoire | Description |
|-----|-------------|-------------|
| `hostname` | Recommandé | Étiquette indicative pour l'équipement. |
| `hardware_model` | Oui | Référence constructeur pour validation d'inventaire. |
| `storage_profile` | Oui | Nom logique du schéma de stockage (utile pour distinguer les variantes). |
| `netmode` | Oui | Mode réseau recommandé (`dhcp` ou `static`). |
| `nic` | Oui | Interface réseau principale. |
| `disk_device` | Oui | Disque système par défaut. |
| `additional_disk_devices` | Non | Disques supplémentaires à préserver. |
| `hardware_specs.cpu.*` | Oui | Informations CPU (modèle, architecture, cœurs, threads, turbo). |
| `hardware_specs.memory.*` | Oui | Spécifications mémoire (capacité, type, fréquence). |
| `extra_packages` | Non | Paquets additionnels recommandés. |
| `enable_powertop_autotune` / `enable_thermald` / `enable_zram_generator` | Non | Optimisations activées par défaut. |
| `zram_generator_config` | Non | Configuration par défaut de ZRAM. |
| `storage_swap_size` / `storage_config_override` | Non | Ajustements de partitionnement (ex : profils chiffrés). |

Les profils servent de base à tous les hôtes identiques. Toute clé peut être surchargée dans
`host_vars/<HÔTE>/main.yml` si un cas particulier l'exige.

## `host_vars/<HÔTE>/secrets.sops.yaml`

| Clé | Obligatoire | Description |
|-----|-------------|-------------|
| `ssh_authorized_keys` | Oui | Liste de clés publiques autorisées pour l'utilisateur administrateur. |
| `password_hash` | Oui | Hash `mkpasswd --method=SHA-512` injecté dans `identity.password`. |
| `disk_encryption.passphrase` | Oui si `disk_encryption.enabled: true` | Passphrase LUKS utilisée pendant l'installation. |
| Toute autre donnée sensible | Non | Exemple : tokens, certificats, secrets applicatifs nécessaires aux `late-commands`.

> ℹ️ **Rappel** : ne conservez aucune donnée en clair. Utilisez `sops baremetal/inventory/host_vars/<HÔTE>/secrets.sops.yaml`
pour éditer ces valeurs.

## Checklist avant de générer l'ISO

1. `main.yml` contient au minimum `hostname`, `hardware_profile`, `netmode` et correspond au profil matériel.
2. Le profil matériel référencé expose bien `disk_device`, `nic`, `hardware_specs` et (si besoin) les disques additionnels.
3. Les secrets (hash + clés SSH + passphrase LUKS) sont présents et chiffrés.
4. En cas de réseau statique, les variables `ip`, `cidr`, `gw`, `dns` sont définies.
5. Lancez `make baremetal/gen HOST=<HÔTE>` pour vérifier le rendu, puis `make baremetal/seed HOST=<HÔTE>`.

Ainsi, toutes les informations nécessaires à la génération de l'ISO sont centralisées et traçables dans Git.
