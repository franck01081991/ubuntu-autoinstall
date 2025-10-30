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

## Outils requis pour la CI locale

```bash
python -m pip install --upgrade pip ansible-core ansible-lint yamllint
curl -sSLo kubeconform.tar.gz https://github.com/yannh/kubeconform/releases/download/v0.6.7/kubeconform-linux-amd64.tar.gz
tar -xzf kubeconform.tar.gz kubeconform && sudo install -m 0755 kubeconform /usr/local/bin/ && rm kubeconform kubeconform.tar.gz
curl -sSLo flux.tar.gz https://github.com/fluxcd/flux2/releases/download/v2.7.3/flux_2.7.3_linux_amd64.tar.gz
tar -xzf flux.tar.gz flux && sudo install -m 0755 flux /usr/local/bin/ && rm flux flux.tar.gz
curl -sSLo tfsec.tar.gz https://github.com/aquasecurity/tfsec/releases/download/v1.28.11/tfsec_1.28.11_linux_amd64.tar.gz
tar -xzf tfsec.tar.gz tfsec && sudo install -m 0755 tfsec /usr/local/bin/ && rm tfsec tfsec.tar.gz
curl -sSLo kube-linter.tar.gz https://github.com/stackrox/kube-linter/releases/download/v0.6.8/kube-linter-linux.tar.gz
tar -xzf kube-linter.tar.gz kube-linter && sudo install -m 0755 kube-linter /usr/local/bin/ && rm kube-linter kube-linter.tar.gz
curl -sL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin
python -m venv checkov-venv
source checkov-venv/bin/activate
pip install --upgrade pip
pip install "importlib-metadata<8.0.0,>=6.0.0" checkov
deactivate
```

## Hypothèses

- Deux sites (`site-a`, `site-b`) disposant chacun de 1 nœud control-plane et
  2 nœuds worker (extensibles via inventaire Ansible).
- Backend Terraform stocké sur un bucket S3 compatible avec verrou DynamoDB.
- Les plages IP MetalLB sont réservées et routées sur chaque site (exemples
  RFC 5737 fournis pour illustration, à remplacer en production).
