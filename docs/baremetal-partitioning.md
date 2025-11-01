# Partitionnement disque durci (ANSSI)

Ce guide décrit le gabarit de partitionnement `anssi-luks-lvm` destiné aux
installations Ubuntu Server 24.04 automatisées via ce dépôt. Il s’inspire des
recommandations de l’ANSSI pour compartimenter les données, appliquer le chiffrement
intégral du disque et durcir les options de montage.

Toutes les étapes restent pilotées par Git : sélectionnez le layout dans vos
variables, validez la PR, laissez la CI générer les artefacts puis déployez l’ISO.

## Principes clés

- GPT + UEFI (`/boot/efi`) pour les plateformes modernes.
- `/boot` non chiffré afin de permettre le démarrage du chargeur.
- Chiffrement LUKS global (`dm-crypt`) encapsulant un volume LVM unique.
- Volumes logiques dédiés pour isoler les journaux, répertoires temporaires et
  données applicatives (`/srv`).
- Options de montage restrictives (`nodev`, `nosuid`, `noexec`, `noatime`) selon
  les usages.

## Tableau des volumes

Les tailles ci-dessous reflètent les recommandations ANSSI pour un serveur
généraliste. Le script de redimensionnement intégré étend automatiquement les
volumes jusqu’à ces valeurs puis attribue l’espace résiduel à `/srv`.

| Volume LVM / Partition | Montage          | Taille recommandée | Options de montage                               | Usage                                    |
|------------------------|------------------|---------------------|--------------------------------------------------|------------------------------------------|
| `efi` (partition)      | `/boot/efi`      | 550 MiB             | `defaults`                                       | Partition système EFI                    |
| `boot` (partition)     | `/boot`          | 1 GiB               | `defaults,noatime,nodev`                         | Kernel et initramfs                      |
| `lv_root`              | `/`              | 32 GiB              | `defaults,noatime`                               | Système de base                          |
| `lv_var`               | `/var`           | 24 GiB              | `defaults,noatime,nodev`                         | États applicatifs                        |
| `lv_var_log`           | `/var/log`       | 8 GiB               | `defaults,noatime,nodev,nosuid,noexec`           | Journaux système                         |
| `lv_var_log_audit`     | `/var/log/audit` | 2 GiB               | `defaults,noatime,nodev,nosuid,noexec`           | Journaux auditd                          |
| `lv_tmp`               | `/tmp`           | 8 GiB               | `defaults,nodev,nosuid,noexec`                   | Fichiers temporaires utilisateurs        |
| `lv_var_tmp`           | `/var/tmp`       | 8 GiB               | `defaults,nodev,nosuid,noexec`                   | Temporaires longue durée                 |
| `lv_home`              | `/home`          | 40 GiB              | `defaults,noatime,nodev`                         | Profils utilisateurs                     |
| `lv_srv`               | `/srv`           | Reste du disque     | `defaults,noatime,nodev,nosuid`                  | Services applicatifs                     |
| `lv_swap`              | swap             | 8 GiB               | `sw`                                             | Swap chiffré                             |

## Mise en œuvre GitOps

1. **Sélectionner le layout**  
   Dans `host_vars` ou votre profil matériel, définissez :
   ```yaml
   storage_layout: anssi-luks-lvm
   disk_device: /dev/nvme0n1   # adaptez selon votre plateforme
   ```

2. **Définir la passphrase LUKS**  
   - Ajoutez la passphrase chiffrée dans `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.
   - Référencez-la via :
     ```yaml
     disk_encryption:
       enabled: true
       passphrase: "{{ disk_encryption_passphrase }}"
     ```

3. **Générer l’autoinstall**  
   Exécutez `make baremetal/gen HOST=<hote>` (ou `PROFILE=<profil>`) puis
   contrôlez le rendu `user-data` dans la PR.

4. **Construire l’ISO**  
   Utilisez `make baremetal/seed` ou `make baremetal/fulliso` selon vos besoins.

## Validation et tests

- **CI/CD** : `make lint` et `make baremetal/gen` sont exécutés localement ou via
  la CI pour garantir un rendu cohérent.
- **VM de test** : bootez l’ISO, vérifiez la demande de passphrase, puis
  contrôlez `lsblk --fs` et `findmnt` pour confirmer la structure.
- **Durcissement** : assurez-vous que les permissions `/tmp` et `/var/tmp` sont
  correctes (`chmod 1777`), et que `auditd` écrit bien dans `/var/log/audit`.

## Personnalisations

- **Taille du swap** : modifiez `lv_swap.size` pour correspondre à votre
  politique (hibernation, charges mémoire).
- **Volumes supplémentaires** : ajoutez d’autres entrées `lvm_partition` /
  `format` / `mount` dans le template en conservant les options de sécurité.
- **Options de montage** : adaptez les flags en fonction de vos besoins
  applicatifs (par exemple retirer `noexec` pour un dossier spécifique).

## Maintenance

- **Rotation de la passphrase** : mettez à jour la valeur SOPS puis regénérez les
  ISO. Documentez la rotation via une PR.
- **Surveillance** : vérifiez régulièrement la saturation des volumes via vos
  outils de supervision pour réajuster les tailles lors des futures installations.
- **Audit** : conservez un export `lsblk`/`findmnt` après installation comme
  preuve de conformité.

## Références

- Recommandations de l’ANSSI sur le durcissement des systèmes GNU/Linux.
- Documentation Curtin / Autoinstall Ubuntu.
- Guide « Chiffrement du disque système (LUKS) » de ce dépôt.
