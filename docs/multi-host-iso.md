# Construire un ISO multi-hôtes

Ce guide explique comment assembler un ISO autonome contenant plusieurs cibles
Autoinstall. L'image repose sur un menu GRUB généré dynamiquement qui permet de
sélectionner l'hôte à installer au démarrage.

## Pré-requis

1. Chaque hôte doit disposer de `user-data` et `meta-data` à jour dans
   `baremetal/autoinstall/generated/<hôte>/`. Relancez si besoin :

   ```bash
   make baremetal/gen HOST=<hote>
   ```

2. L'ISO Ubuntu officiel (`ubuntu-24.04-live-server-amd64.iso`) doit être
   accessible localement. Placez-le dans `files/` ou transmettez son chemin via
   la variable `UBUNTU_ISO`.

3. Les secrets doivent être chiffrés et stockés hors Git, sous
   `baremetal/inventory-local/`.

## Construction avec `make`

```bash
make baremetal/multiiso \
  HOSTS="site-a-m710q1 site-a-m710q2" \
  UBUNTU_ISO=files/ubuntu-24.04-live-server-amd64.iso \
  NAME=prod-2025-03 \
  DEFAULT_HOST=site-a-m710q1 \
  GRUB_TIMEOUT=15
```

La cible produit :

- `baremetal/autoinstall/generated/_multi/prod-2025-03/ubuntu-autoinstall-prod-2025-03.iso`
- `manifest.json` (liste des hôtes inclus et ISO source)
- `SUMMARY.txt` (mémo opérationnel)

Le menu GRUB propose une entrée par hôte. La variable `DEFAULT_HOST` sélectionne
l'entrée activée automatiquement à l'expiration du `GRUB_TIMEOUT`.

## Construction via `iso_manager.py`

L'application CLI orchestre les rendus et la génération en une commande :

```bash
python3 scripts/iso_manager.py multi \
  --host site-a-m710q1 --host site-a-m710q2 \
  --ubuntu-iso files/ubuntu-24.04-live-server-amd64.iso \
  --name prod-2025-03 \
  --default-host site-a-m710q1 \
  --render
```

Le drapeau `--render` regénère `user-data` et `meta-data` pour chaque hôte avant
la construction de l'ISO.

## Validation

1. Vérifiez le contenu du manifest :

   ```bash
   jq '.' baremetal/autoinstall/generated/_multi/prod-2025-03/manifest.json
   ```

2. Montez l'ISO et assurez-vous que les répertoires `nocloud/<hôte>/` contiennent
   bien les paires `user-data` / `meta-data` attendues.

3. En environnement de test (ex : QEMU), démarrez l'ISO et validez que chaque
   entrée du menu démarre l'installation Autoinstall correspondante.

## Bonnes pratiques

- Conservez les ISO multi-hôtes dans un registre interne ou un coffre-fort.
- Documentez dans vos PR la liste des hôtes agrégés et la version de l'ISO
  Ubuntu utilisée (`manifest.json`).
- Rejouez `make baremetal/gen` pour chaque hôte avant toute regeneration afin de
  capturer les dernières modifications d'inventaire.
