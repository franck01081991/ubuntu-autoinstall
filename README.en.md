# Ubuntu Autoinstall

GitOps-first pipeline dedicated to building unattended **Ubuntu Server 24.04 LTS**
ISOs with **Autoinstall + cloud-init (NoCloud)**. Every image is rendered from
version-controlled files and produced by CI to guarantee reproducibility and
auditability.

> 👋 New to the project? Start with the
> [beginner guide](docs/getting-started-beginner.md) to craft your first seed ISO
> locally before validating the GitOps pipeline.

## Table of contents

- [Overview](#overview)
- [GitOps approach for ISO builds](#gitops-approach-for-iso-builds)
- [Repository layout](#repository-layout)
- [Inventory and templates](#inventory-and-templates)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Key Make targets](#key-make-targets)
- [Validation and CI/CD](#validation-and-cicd)
- [Security and compliance](#security-and-compliance)
- [Additional resources](#additional-resources)

## Overview

This repository focuses exclusively on two Autoinstall ISO variants:

- **Seed ISO (`CIDATA`)**: ships `user-data` and `meta-data` alongside the
  official installer image.
- **Full ISO**: embeds the NoCloud payload directly inside Ubuntu Live Server.

Other historical scopes (application provisioning, overlay networking, etc.) are
no longer documented even if legacy directories remain in Git history.

## GitOps approach for ISO builds

- **Declarative inputs**: hosts and profiles are described as YAML under
  `baremetal/inventory/` and reviewed through pull requests.
- **Automated rendering**: Ansible + Jinja2 generate `user-data` and `meta-data`
  in `baremetal/autoinstall/generated/<target>/`.
- **Reproducible builds**: idempotent scripts in `baremetal/scripts/` create seed
  and full ISOs from the rendered artefacts.
- **Controlled distribution**: CI publishes the images as artefacts and acts as
  the single source of truth for deployments.

## Repository layout

```text
baremetal/
├── ansible/            # Autoinstall rendering playbooks (NoCloud)
├── autoinstall/        # Jinja2 templates + generated artefacts
├── inventory/          # Host vars and hardware profiles
└── scripts/            # Seed/full ISO build scripts
ansible/                # Shared dependencies and task files
scripts/install-sops.sh # SOPS installer (Linux amd64)
```

Directories not listed above are preserved for compatibility but fall outside
this ISO-focused workflow.

## Inventory and templates

- **Hardware profiles** (`baremetal/inventory/profiles/hardware/`): minimal
  defaults per model (disk layout, NIC, tuned packages). Use them as a starting
  point.
- **Host variables** (`baremetal/inventory/host_vars/<host>.yml`): define
  hostname, devices, and network parameters for each node.
- **Templates** (`baremetal/autoinstall/templates/`): shared `user-data` and
  `meta-data` definitions. Only adjust them when the product evolves.

## Prerequisites

- Official **Ubuntu 24.04 Live Server** ISO for full builds.
- Python 3.10+, `ansible-core`, `xorriso`, `mkpasswd`.
- [SOPS](https://github.com/getsops/sops) and an
  [age](https://age-encryption.org/) key pair whenever sensitive variables must
  be encrypted.
- Git access with code review. Never mutate production systems manually.

## Quick start

1. **Check local dependencies**

   ```bash
   make doctor
   ```

   The target confirms required binaries and highlights the CI linters
   (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`).

2. **Prepare host variables**

   ```bash
   cp baremetal/inventory/host_vars/example.yml \
     baremetal/inventory/host_vars/site-a-m710q1.yml
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1.yml
   ```

   Customize `hostname`, `hardware_profile`, the system disk, and optional
   static networking or extra packages.

3. **Render the Autoinstall payload**

   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```

4. **Build the seed ISO**

   ```bash
   make baremetal/seed HOST=site-a-m710q1
   ```

5. **Produce a full installer ISO (optional)**

   ```bash
   make baremetal/fulliso HOST=site-a-m710q1 \
     UBUNTU_ISO=/path/ubuntu-24.04-live-server-amd64.iso
   ```

Generated ISOs live under `baremetal/autoinstall/generated/<target>/`.

## Key Make targets

- `make doctor`: dependency checks.
- `make baremetal/gen HOST=<name>` or `PROFILE=<profile>`: render Autoinstall
  files.
- `make baremetal/seed HOST=<name>`: create a seed ISO.
- `make baremetal/fulliso HOST=<name> UBUNTU_ISO=<path>`: produce a standalone
  installer ISO.
- `make baremetal/clean`: remove generated artefacts.
- `make lint`: run the CI linter suite locally.

## Validation and CI/CD

- `.github/workflows/build-iso.yml`: renders Autoinstall artefacts per hardware
  profile, builds both ISO flavours, publishes artefacts, and prunes older runs
  to stay within GitHub Actions quotas.
- `.github/workflows/repository-integrity.yml`: runs `yamllint`, `ansible-lint`,
  `shellcheck`, `markdownlint`, and `trivy fs` (config + secrets) to keep the
  repository clean and secure.
- pip/npm/collection caches derive their keys from file hashes to remain
  idempotent.

## Security and compliance

- Replace demo SSH keys with project-specific keys.
- Generate password hashes via `mkpasswd -m yescrypt` or `openssl passwd -6`.
- Templates enable BBR, `irqbalance`, `rp_filter=2`, and disable outgoing ICMP
  redirects.
- Store produced ISOs in controlled locations (CI artefacts, internal registry,
  etc.).

## Additional resources

- [Beginner guide](docs/getting-started-beginner.md)
- [French README](README.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
