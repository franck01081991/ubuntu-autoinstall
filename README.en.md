# Ubuntu Autoinstall

Provision individual **Ubuntu Server 24.04 LTS** hosts (ThinkCentre M710q,
Dell OptiPlex 3020M) with **Autoinstall + cloud-init (NoCloud)** using a GitOps
workflow driven by Git, CI/CD, and code review.

## Table of contents

- [Overview](#overview)
- [GitOps architecture](#gitops-architecture)
- [Repository layout](#repository-layout)
- [Bare metal scope](#bare-metal-scope)
- [Prerequisites](#prerequisites)
- [Quick start (bare metal)](#quick-start-bare-metal)
- [Hardware profiles](#hardware-profiles)
- [Bare metal host variables](#bare-metal-host-variables)
- [Shared variables and secrets management](#shared-variables-and-secrets-management)
- [Available Make targets](#available-make-targets)
- [Validation and testing](#validation-and-testing)
- [Continuous integration](#continuous-integration)
- [Security and compliance](#security-and-compliance)
- [VPS provisioning with Ansible (no ISO)](#vps-provisioning-with-ansible-no-iso)
- [Additional resources](#additional-resources)

## Overview

This repository provides two separate GitOps tracks:

- **`baremetal/`**: renders autoinstall assets and builds both seed/full ISOs for
  Ubuntu Server 24.04 bare metal hosts.
- **`vps/`**: runs post-install automation for VPS targets using Ansible only—no
  ISOs are produced.

Each bare metal host has its own inventoried variables, guaranteeing
reproducible, idempotent deployments. Generated ISOs (seed and full) are
published as pipeline artifacts for traceability. A library of **hardware
profiles** under `baremetal/inventory/profiles/hardware/` allows the CI to
validate autoinstall generation per model.

## GitOps architecture

- **Declarative definition**:
  - host-specific parameters live in `baremetal/inventory/host_vars/<host>.yml`;
  - shared hardware profiles reside in
    `baremetal/inventory/profiles/hardware/<profile>.yml` for reuse.
- **Automated rendering**: Ansible + Jinja2 produce `user-data`/`meta-data` in
  `<track>/autoinstall/generated/<host>/` for both bare metal and VPS
  inventories.
  - the playbooks `baremetal/ansible/playbooks/generate_autoinstall.yml` and
    `vps/ansible/playbooks/generate_autoinstall.yml` import the shared task list
    under `ansible/playbooks/common/`, guaranteeing identical behaviour
    regardless of the execution path (for example `make baremetal/gen` or
    `make vps/gen`).
- **Controlled distribution**: CI builds the installer ISOs, stores them as
  artifacts, and feeds them into deployments.
- **No manual steps**: Git, CI/CD, and documented commands drive the entire
  lifecycle.

## Repository layout

```text
baremetal/
├── ansible/            # Autoinstall rendering playbook (NoCloud)
├── autoinstall/        # Jinja2 templates + generated artefacts
├── inventory/          # Host vars and bare-metal hardware profiles
└── scripts/            # Seed/full ISO build scripts
vps/
├── ansible/            # Autoinstall rendering + post-install provisioning
├── autoinstall/        # Generated artefacts (templates shared with baremetal)
└── inventory/          # Inventory, SOPS secrets, and VPS profiles
ansible/                # Shared dependencies (collections, requirements)
ansible/playbooks/common/ # Shared task files between playbooks
scripts/install-sops.sh # SOPS installer (baremetal & vps)
```

## Bare metal scope

- **`baremetal/` track**: focuses on rendering NoCloud autoinstall files and
  building seed/full ISOs for physical Ubuntu Server hosts.
- **No cloud IaC stored here**: Terraform, Kubernetes, and remote secret
  management belong in dedicated repositories. The VPS track below remains pure
  Ansible automation.
- **GitOps traceability**: hosts and hardware profiles are defined via
  Ansible/Jinja and validated by CI for auditability without ad-hoc scripts.

## Prerequisites

- Official Ubuntu 24.04 Live Server ISO (for `make baremetal/fulliso`).
- Python 3.10+ and Ansible available on the build workstation.
- System utilities: `xorriso` (ISO authoring) and `mkpasswd` (password hash
  generation).
- [SOPS](https://github.com/getsops/sops) plus an
  [age](https://age-encryption.org/) key pair to encrypt sensitive vars.
  `scripts/install-sops.sh` installs the recommended release (Linux amd64) and
  verifies SHA-256.
- Valid SSH keys and a hashed password (YESCRYPT recommended) per host.

## Quick start (bare metal)

1. **Select a hardware profile (optional)**

   ```bash
   ls baremetal/inventory/profiles/hardware
   make baremetal/gen PROFILE=lenovo-m710q
   ```

   Artefacts are generated under
   `baremetal/autoinstall/generated/lenovo-m710q/`.

2. **Define the host variables**

   ```bash
   cp baremetal/inventory/host_vars/example.yml \
     baremetal/inventory/host_vars/site-a-m710q1.yml
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1.yml
   ```

3. **Render autoinstall files for the host**

   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```

4. **Build the seed ISO (`CIDATA`)**

   ```bash
   make baremetal/seed HOST=site-a-m710q1
   ```

   The ISO is exported to
   `baremetal/autoinstall/generated/site-a-m710q1/seed-site-a-m710q1.iso`.

5. **Start installation**

   - Flash the official Ubuntu installer onto USB #1.
   - Mount the seed ISO onto USB #2 (or a dedicated USB stick).
   - Boot the installer, press `e` in GRUB, and append `autoinstall` to the
     Linux line.
   - The installation proceeds unattended through cloud-init (NoCloud).

6. **(Optional) Build a fully integrated installer ISO**

 ```bash
  make baremetal/fulliso HOST=site-a-m710q1 \
    UBUNTU_ISO=/path/ubuntu-24.04-live-server-amd64.iso
  ```

  `baremetal/scripts/make_full_iso.sh` replays the source ISO boot
  configuration via `xorriso` to add the `nocloud/` directory without depending
  on `isolinux/` (`-boot_image any replay`).

### VPS autoinstall quickstart

The VPS inventory reuses the exact same rendering logic:

```bash
make vps/gen VPS_HOST=vps-sapinet
```

Artefacts are created under `vps/autoinstall/generated/vps-sapinet/`. The VPS
playbook consumes the same host variables (`hostname`, `disk_device`, network
parameters, SSH keys, passwords) as the bare metal workflow.

## Hardware profiles

Profiles under `baremetal/inventory/profiles/hardware/` capture minimal
per-model settings to validate autoinstall generation (disks, NICs, test SSH
keys, etc.). Reference them with `make baremetal/gen PROFILE=<profile>` and
customize site-specific files via Ansible.

- `lenovo-m710q`: ThinkCentre M710q Tiny with NVMe + 2.5" SATA; both disks join
  a single LVM volume for extra capacity.
  - Optimisations: Intel microcode, `thermald`, `powertop` (auto-tune service),
    and `lm-sensors` ship pre-installed to stabilise thermals and efficiency.
- `lenovo-90dq004yfr`: ThinkCentre M700 Tiny (90DQ004YFR) using SATA only, tuned
  for that platform’s power/microcode characteristics.

## Bare metal host variables

Each `baremetal/inventory/host_vars/<host>.yml` may define:

- `hostname`: hostname applied during installation.
- `disk_device`: main system disk (for example `/dev/nvme0n1`).
- `additional_disk_devices`: extra disks to add to the LVM VG (for example
  `['/dev/sda']`).
- `netmode`: `dhcp` or `static`.
- `nic`: network interface (for example `enp1s0`) for static addressing.
- `ip`, `cidr`, `gw`, `dns`: static network parameters.
- `ssh_authorized_keys`: list of allowed public keys.
- `password_hash`: password hash (YESCRYPT or SHA512).
- `extra_packages`: additional packages to install (for example hardware
  optimisations).
- `enable_powertop_autotune`: enables the `powertop-autotune` systemd service.

## Shared variables and secrets management

- Shared VPS variables are kept in `vps/inventory/group_vars/vps/` close to the
  inventory. Reusable VPS autoinstall profiles can be stored under
  `vps/inventory/profiles/hardware/`.
- Secrets are versioned **encrypted** with [SOPS](https://github.com/getsops/sops):
  1. Copy the template:

     ```bash
     cp vps/inventory/group_vars/vps/secrets.sops.yaml.example \
       vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

  2. Install SOPS if required:

     ```bash
     sudo bash scripts/install-sops.sh /usr/local/bin
     ```

  3. Add your age public key to `.sops.yaml` (`age1...`).
  4. Encrypt the file:

     ```bash
     sops --encrypt --in-place \
       vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

  5. Edit securely:

     ```bash
     sops vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

The keys `vps_external_dns_api_token` and `vps_keycloak_admin_password` must
exist in this file for `vps/ansible/playbooks/provision.yml` to succeed. The
playbook fails loudly when they are missing.

## Available Make targets

- `make doctor`: verify required dependencies and suggest optional linters to
  mirror CI tooling.
- `make baremetal/gen HOST=<name>`: render `user-data`/`meta-data` into
  `baremetal/autoinstall/generated/<name>/`.
- `make baremetal/gen PROFILE=<profile>`: render artefacts for a hardware
  profile into `baremetal/autoinstall/generated/<profile>/`.
- `make vps/gen VPS_HOST=<name>` or `make vps/gen PROFILE=<profile>`: render
  autoinstall artefacts into `vps/autoinstall/generated/<name or profile>/`
  while reusing the same templates as the bare metal track.
- `make baremetal/seed HOST=<name>`: build `seed-<name>.iso` (NoCloud
  `CIDATA`).
- `make baremetal/fulliso HOST=<name> UBUNTU_ISO=<path>`: build a full
  installer ISO with autoinstall and boot flags.
- `make baremetal/clean`: remove generated artefacts.
- `make vps/clean`: remove generated VPS artefacts.
- `make vps/provision`: execute the VPS playbook (post-install, no ISO
  involved).
- `make vps/lint`: run `yamllint` and `ansible-lint` on the VPS track.
- `make lint`: aggregates `yamllint`, `ansible-lint`, `shellcheck`, and
  `markdownlint` across the repository (mirrors the “Repository Integrity” CI
  workflow).

## Validation and testing

- `make lint`: runs the full syntax and style suite (`yamllint`, `ansible-lint`,
  `shellcheck`, `markdownlint`). Requires `shellcheck` and `markdownlint` to be
  present locally.
- `make vps/lint`: focused linting for the VPS track (`yamllint` +
  `ansible-lint`).
- `ansible-lint`: re-run deep validation locally when debugging specific
  playbooks.
- `yamllint baremetal/inventory baremetal/ansible vps/inventory vps/ansible`:
  run YAML-only checks.
- `trivy fs --security-checks config,secret --severity HIGH,CRITICAL .`: local
  configuration & secret scanning with the same thresholds as CI.
- `pip install -r ansible/requirements.txt`: installs `ansible-core` 2.16.13
  (fixes CVE-2024-8775) before running the playbooks.

## Continuous integration

- The workflow `.github/workflows/repository-integrity.yml` enforces repository
  hygiene:
  - **Static analysis** job: runs `yamllint`, `ansible-lint`, `shellcheck`, and
    `markdownlint` (same scope as `make lint`).
  - **Trivy configuration scan** job: `trivy fs` fails the run on
    **HIGH/CRITICAL** findings or exposed secrets.
- The workflow `.github/workflows/build-iso.yml` renders autoinstall files **per
  hardware model** (`PROFILE`), builds both seed and full ISOs, and uploads them
  as artifacts.
- To trigger manually: **Actions → Build Bare Metal ISOs → Run workflow**,
  optionally overriding `UBUNTU_ISO_URL`.
  - by default the CI pulls the image from
    `https://old-releases.ubuntu.com/releases/24.04/ubuntu-24.04-live-server-amd64.iso`
    to ensure long-term availability. The ISO download is cached in `.cache/` to
    avoid repeated transfers.
- Artefacts are grouped per hardware profile for straightforward traceability
  and retained for **1 day** (`retention-days: 1`).
- Before uploading, the workflow deletes existing GitHub Actions artifacts for
  the same profile (`autoinstall-<profile>`) to stay within the storage quota
  whenever the run originates from the main repository (local branches or manual
  dispatches).
- When the GitHub Actions quota is exceeded or the token lacks permissions,
  artifact uploads fail with a warning but the workflow continues (best-effort
  mode, artifacts must be recovered manually if needed).

## Security and compliance

- Replace example SSH keys with production-grade host/user keys.
- Generate passwords using `mkpasswd -m yescrypt` (from the `whois` package) or
  `openssl passwd -6` for SHA512.
- Network configuration enables BBR, sets `rp_filter=2`, disables ICMP redirects,
  and enables `irqbalance`.
- Store ISO artifacts produced by CI in controlled storage (for example GitHub
  Actions artifacts).

## VPS provisioning with Ansible (no ISO)

VPS instances are provisioned **exclusively** via Ansible. No ISO is ever
mounted or installed for these hosts.

After installing Ubuntu on the VPS, run:

```bash
ansible-playbook -i vps/inventory/hosts.yml \
  vps/ansible/playbooks/provision.yml -u ubuntu --become
```

Define variables via `vps/inventory/group_vars/vps/` (see previous section) or
use `-e` flags for temporary overrides.

Install the required Ansible collections before running the playbook:

```bash
ansible-galaxy collection install -r ansible/collections/requirements.yml
```

The `ansible/collections/requirements.yml` file pins `community.sops` (**1.6.0**),
`community.kubernetes` (**2.0.3**), and `kubernetes.core` (**3.0.1**) to supply
Helm/kubectl modules needed for GitOps deployments.

## Additional resources

- [Documentation en français](README.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
