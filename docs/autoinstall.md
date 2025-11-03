# Ubuntu Autoinstall

Ubuntu 24.04 utilise Subiquity et le datasource **NoCloud** pour l'automatisation. La référence officielle est le [Autoinstall configuration reference manual](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html) publiée par Canonical.

## Principes retenus
- Un seul ISO pour tous les serveurs : la configuration spécifique se fait via `user-data` et `meta-data` générés depuis `baremetal/inventory/host_vars/<host>/`.
- Deux modes de déploiement sont supportés :
  1. ISO autonome (`autoinstall ds=nocloud;s=/cdrom/nocloud/`) où les fichiers sont embarqués dans l'image.
  2. ISO réseau (`autoinstall ds=nocloud-net;s=http://<ip>/autoinstall/`) pointant vers un serveur HTTP qui expose les fichiers rendus.
- Le stockage impose GPT, une partition EFI de 512 Mio, le reste chiffré en LUKS2 (`cipher: aes-xts-plain64`, `key_size: 512`, `pbkdf: argon2id`). À l'intérieur, un VG LVM `vg_system` héberge un LV `lv_root` monté sur `/`.
- Si `install_disk` n'est pas renseigné dans l'inventaire, le template utilise `match: { size: largest }` pour sélectionner automatiquement le plus grand disque disponible (SATA ou NVMe).

## Exemple de menu GRUB multi-hôtes
Ajoutez dans `boot/grub/grub.cfg` un menu permettant de choisir quel hôte installer sans régénérer l'ISO :

```cfg
menuentry "Installer serveur1 (NoCloud local)" {
    set gfxpayload=keep
    linux   /casper/vmlinuz autoinstall quiet --- ds=nocloud;s=/cdrom/nocloud/host-vars/serveur1/
    initrd  /casper/initrd
}

menuentry "Installer serveur2 (HTTP)" {
    set gfxpayload=keep
    linux   /casper/vmlinuz autoinstall quiet --- ds=nocloud-net;s=http://192.0.2.10/autoinstall/serveur2/
    initrd  /casper/initrd
}
```

Dans le cas ISO autonome, placez `user-data` / `meta-data` de chaque hôte sous `/nocloud/host-vars/<hostname>/` lors de la construction. En mode HTTP, exposez ces fichiers via un serveur statique pour que Subiquity les récupère au démarrage.
