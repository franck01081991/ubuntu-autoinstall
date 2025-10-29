# Kubernetes GitOps Stack

Ce périmètre décrit la pile Kubernetes multi-sites exploitée via GitOps.
Il couvre l'approvisionnement des clusters k3s sur Ubuntu Server 24.04 LTS
et la couche applicative Flux qui gère Cilium, MetalLB et les workloads.

## Structure

```text
kubernetes/
├── ansible/               # Bootstrap des nœuds et de Flux
│   ├── inventories/       # Inventaires et variables (SOPS pour les secrets)
│   ├── playbooks/         # Playbooks d'orchestration multi-site
│   └── roles/             # Rôles dédiés (bootstrap, k3s, flux, etc.)
├── flux/                  # Déclarations GitOps appliquées par Flux
│   ├── base/              # Manifeste Flux System commun
│   ├── apps/              # Composants applicatifs (Cilium, MetalLB, ...)
│   └── clusters/          # Overlays spécifiques par site
└── terraform/             # Provisioning réseau et machines (idempotent)
    ├── modules/           # Modules réutilisables
    └── envs/              # Environnements / sites (site-a, site-b, ...)
```

## Flux GitOps

- Bootstrap minimal appliqué par Ansible (Flux controllers + sync).
- Flux synchronise `kubernetes/flux/clusters/<site>` sur chaque cluster.
- Les applications (Cilium, MetalLB, etc.) sont déployées via des `HelmRelease`.

## Sécurité & Réseau

- Cilium en mode routage natif eBPF, remplacement kube-proxy strict.
- ClusterMesh et WireGuard pour l'interconnexion site-à-site.
- MetalLB en mode L2 pour annoncer l'ensemble des IPs publiques locales.

## Secrets

- Gestion exclusive via SOPS + age. Aucun secret en clair.
- Les fichiers `*.sops.yaml` doivent être chiffrés avant commit.

## Commandes clés

```bash
make kubernetes/bootstrap   # Bootstrap initial (k3s + Flux)
make kubernetes/plan        # Terraform plan réseau/machines
make kubernetes/apply       # Terraform apply (via backend S3 + lock)
make kubernetes/lint        # Lint Ansible/Terraform/YAML/Kustomize
make kubernetes/security    # Scans sécurité (tfsec, kube-linter, Trivy)
```

## Hypothèses

- Deux sites (`site-a`, `site-b`) disposant chacun de 1 nœud control-plane et
  2 nœuds worker (extensibles via inventaire Ansible).
- Backend Terraform stocké sur un bucket S3 compatible avec verrou DynamoDB.
- Les plages IP MetalLB sont réservées et routées sur chaque site (exemples
  RFC 5737 fournis pour illustration, à remplacer en production).
