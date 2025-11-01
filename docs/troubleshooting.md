# Dépannage : chaîne Ubuntu Autoinstall

Ce guide recense les incidents les plus fréquents rencontrés par un·e technicien·ne lors de la génération d'ISO Autoinstall. Chaque résolution doit rester GitOps : corrigez la configuration dans Git, laissez la CI valider, puis rejouez les commandes idempotentes.

## `make doctor` échoue (dépendance manquante)

**Symptôme**  
Sortie type : `Missing required dependency: xorriso` ou absence de linters recommandés.

**Résolution GitOps**  
1. Ajoutez/actualisez le rôle ou le script d’installation de vos dépendances poste (ex. playbook Ansible interne).  
2. Réexécutez `make doctor` pour confirmer que toutes les dépendances sont disponibles.  
3. Soumettez la PR associée et attendez la validation CI avant de générer des ISO.

## `sops` ne trouve pas la clé `age`

**Symptôme**  
`sops` ou l’assistant ISO affiche « Le fichier de clé age est introuvable ».

**Résolution GitOps**  
1. Vérifiez que la variable `SOPS_AGE_KEY` (CI) ou `SOPS_AGE_KEY_FILE` pointe vers la clé partagée par l’équipe.
2. Si besoin, mettez à jour `scripts/install-sops.sh`, `scripts/install-age.sh` ou votre bootstrap interne pour distribuer la clé via un secret versionné.
3. Pour un atelier ou un labo, exécutez `./scripts/bootstrap-demo-age-key.sh` afin d’installer la clé de démonstration fournie par le dépôt.
4. En production, remplacez cette clé par la vôtre (PR `sops updatekeys --add age:<votre_clef>`), puis relancez la commande (`make baremetal/list`, `make baremetal/gen`, wizard…).

## `make baremetal/fulliso` échoue (ISO Ubuntu introuvable)

**Symptôme**  
Le script ISO signale `ISO introuvable à l'emplacement : ...`.

**Résolution GitOps**  
1. Déclarez l’ISO officielle (chemin ou artefact interne) dans votre documentation d’équipe ou vos variables Git.  
2. Passez explicitement `UBUNTU_ISO=/chemin/ubuntu-24.04-live-server-amd64.iso` à la cible Make ou dans votre pipeline.  
3. Relancez `make baremetal/fulliso HOST=<nom> UBUNTU_ISO=<chemin>`.

## L’hôte n’apparaît pas dans `make baremetal/list`

**Symptôme**  
La section « Hôtes déclarés » est vide ou manque votre machine.

**Résolution GitOps**  
1. Rejouez `make baremetal/host-init HOST=<nom> PROFILE=<profil>` pour réhydrater `host_vars/` et `hosts.yml`.  
2. Commitez les ajustements (nouvelle entrée inventaire, profils) et ouvrez une PR.  
3. Vérifiez à nouveau via `make baremetal/list`.

## `git pull --ff-only` échoue dans l’assistant ISO

**Symptôme**  
L’assistant s’arrête sur un conflit ou une divergence de branche.

**Résolution GitOps**  
1. Faites un commit ou un stash de vos changements locaux.  
2. Rejouez `git fetch --all --prune` puis `git pull --ff-only` dans votre branche GitOps.  
3. Relancez l’assistant ISO pour poursuivre le flux.

---

Pour tout incident non listé, ouvrez un ticket d’amélioration en décrivant le symptôme, la commande exécutée et le correctif Git envisagé.
