# ADR 0001 – Architecture multi-site k3s avec GitOps

- Date : 2024-06-04
- Statut : Accepté
- Contexte : Besoin d'opérer plusieurs sites Kubernetes Ubuntu 24.04 LTS dans
  une approche GitOps-first, auditable et sans opérations manuelles.

## Décision

1. **Clusters k3s par site**
   - 1 control-plane + n workers selon inventaire.
   - k3s configuré sans flannel, kube-proxy désactivé, Traefik retiré.

2. **CNI Cilium (eBPF natif)**
   - Remplacement kube-proxy strict (`kubeProxyReplacement=strict`).
   - Routage natif (`routingMode=native`) avec `autoDirectNodeRoutes`.
   - Chiffrement WireGuard et ClusterMesh pour l'interconnexion inter-sites.

3. **Exposition publique via MetalLB L2**
   - Pools d'IP publics dédiés par site (1 IP critique/service).
   - Annonces L2 pour consommer toutes les IP locales sans overlay.

4. **GitOps Flux**
   - Bootstrap automatisé via Ansible.
   - Flux synchronise `kubernetes/flux/clusters/<site>`.
   - Applications packagées en `HelmRelease` (Cilium, MetalLB, workloads).

5. **Terraform + Ansible**
   - Terraform pour réseaux/machines avec backend S3 + DynamoDB.
   - Ansible pour le bootstrap k3s + Flux, orchestré via `make`.

## Conséquences

- **Idempotence** : toutes les opérations passent par Git + CI/CD + Make.
- **Sécurité** : secrets chiffrés SOPS, scans tfsec/kube-linter/Trivy.
- **Scalabilité** : ajout d'un site = nouveau dossier `kubernetes/terraform/envs/<site>`
  - overlay Flux.
- **Risques** :
  - Dépendance à Flux pour l'état désiré (nécessite surveillance).
  - Complexité ClusterMesh/WireGuard → nécessite supervision réseau.
- **Roll-back** : versionner tout changement, utiliser `git revert` + `terraform
  apply`/`ansible-playbook`/Flux pour revenir à un état sain.
