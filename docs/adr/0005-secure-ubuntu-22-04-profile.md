# 0005 — Profil Autoinstall Ubuntu 22.04 sécurisé clé-publique

- Date: 2024-08-27
- Status: Accepted
- Deciders: Platform Team
- Tags: baremetal, security, autoinstall

## Contexte

Les templates existants ciblent principalement Ubuntu 24.04 et reposent sur des
variables inventoriées pour personnaliser chaque hôte. Certains environnements
exigent néanmoins un fichier Autoinstall statique pour Ubuntu 22.04 LTS
(`jammy`) intégrant un durcissement complet : chiffrement total du disque,
authentification SSH par clé uniquement, activation immédiate des garde-fous
(`ufw`, `fail2ban`, `unattended-upgrades`).

## Décision

Ajouter un fichier `baremetal/autoinstall/secure-ubuntu-22.04.yaml` versionné
avec les paramètres de sécurité attendus et des commandes tardives pour appliquer
le durcissement. Le fichier reste déclaratif (aucune substitution dynamique) et
expose un espace réservé `SOPS_DECRYPTED_DISK_PASSPHRASE` que la pipeline GitOps
remplace lors du rendu final après déchiffrement via `SOPS`.

## Conséquences

- **Positives**
  - Fournit un profil statique immédiatement exploitable pour des installations
    bare metal 22.04 sécurisées sans dépendre des templates Jinja2 24.04.
  - Normalise le durcissement SSH, UFW et les services de sécurité via un script
    idempotent exécuté dans `late-commands`.
  - Rappelle explicitement l'utilisation de `SOPS` pour la passphrase LUKS, ce
    qui évite tout secret en clair dans Git.
- **Négatives**
  - Le fichier doit être maintenu séparément des templates 24.04 ; un écart de
    configuration devra être répliqué manuellement si pertinent.
- **Neutres/Mitigations**
  - La documentation (`README.md`) précise la marche à suivre pour injecter la
    passphrase chiffrée via la CI afin d'éviter toute manipulation manuelle.
