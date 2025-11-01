# Ubuntu Autoinstall

GitOps-first pipeline dedicated to building unattended **Ubuntu Server 24.04 LTS**
ISOs with **Autoinstall + cloud-init (NoCloud)**. Every image is rendered from
version-controlled files and then built manually outside CI to guarantee
reproducibility and auditability.

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
- [Disk encryption](#disk-encryption)
- [Additional resources](#additional-resources)

## Overview

This repository focuses exclusively on two Autoinstall ISO variants for
**bare metal servers**:

- **Seed ISO (`CIDATA`)**: ships `user-data` and `meta-data` alongside the
  official installer image.
- **Full ISO**: embeds the NoCloud payload directly inside Ubuntu Live Server.

Legacy scopes (application provisioning, overlay networking, VPS, etc.) have
been removed so that only the bare metal ISO toolchain remains. Deleted
components can still be recovered from Git history if needed.

## GitOps approach for ISO builds

- **Declarative inputs**: hosts and profiles are described as YAML under
  `baremetal/inventory/` and reviewed through pull requests.
- **Automated rendering**: Ansible + Jinja2 generate `user-data` and `meta-data`
  in `baremetal/autoinstall/generated/<target>/`.
- **Reproducible builds**: idempotent scripts in `baremetal/scripts/` create seed
  and full ISOs from the rendered files.
- **GitOps validation**: CI confirms that every hardware profile and declared
  host renders consistent `user-data` and `meta-data`. Teams can then assemble
  their ISO locally or through a dedicated image factory.

## Repository layout

```text
baremetal/
├── ansible/            # Autoinstall rendering playbooks (NoCloud)
├── autoinstall/        # Jinja2 templates + generated artefacts
├── inventory/          # Host vars and hardware profiles
└── scripts/            # Seed/full ISO build scripts
ansible/                # Shared dependencies and task files
docs/                   # Guides and Architecture Decision Records
scripts/install-sops.sh # SOPS installer (Linux amd64)
```

Every directory shown above is required to produce the bare metal ISOs through
the GitOps pipeline.

## Inventory and templates

- **Hardware profiles** (`baremetal/inventory/profiles/hardware/`): minimal
  defaults per model (disk layout, NIC, tuned packages). Use them as a starting
  point.
- **Host variables** (`baremetal/inventory/host_vars/<host>/`): each host owns a
  directory with `main.yml` (non-sensitive values) and `secrets.sops.yaml`
  (password hashes, SSH keys, tokens encrypted with SOPS).
- **Host inventory** (`baremetal/inventory/hosts.yml`): empty by design so the
  repository stays environment-agnostic. Declare only the machines you want to
  render locally or through the GitOps CI.
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
   cp -R baremetal/inventory/host_vars/example \
     baremetal/inventory/host_vars/site-a-m710q1
   $EDITOR baremetal/inventory/host_vars/site-a-m710q1/main.yml
   SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
     sops baremetal/inventory/host_vars/site-a-m710q1/secrets.sops.yaml
   ```

   Customize `main.yml` (hostname, hardware profile, disk, networking) and use
   SOPS to encrypt secrets in `secrets.sops.yaml` (`password_hash`,
   `ssh_authorized_keys`, tokens). Enable LUKS by adding
   `disk_encryption.enabled: true` and referencing the SOPS-managed passphrase
   as documented in the [disk encryption guide](docs/baremetal-disk-encryption.md).
   Finally, declare the host in `baremetal/inventory/hosts.yml`. The file starts
   empty so each contributor tracks only their local targets:

   ```yaml
   all:
     children:
       baremetal:
         hosts:
           site-a-m710q1: {}
   ```

3. **Discover hardware facts automatically**

   ```bash
   make baremetal/discover HOST=site-a-m710q1
   ```

   The `discover_hardware.yml` playbook gathers `ansible_facts`, `lsblk`, and
   `ip -j link` from the remote host and persists a JSON cache under
   `.cache/discovery/`. Use this snapshot to seed or update your hardware
   profiles before committing any change.

4. **Render the Autoinstall payload**

   ```bash
   make baremetal/gen HOST=site-a-m710q1
   ```

5. **Build the seed ISO**

   ```bash
   make baremetal/seed HOST=site-a-m710q1
   ```

6. **Produce a full installer ISO (optional)**

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
- `make baremetal/discover HOST=<name>`: collect hardware facts into
  `.cache/discovery/<name>.json`.
- `make baremetal/clean`: remove generated artefacts.
- `make lint`: run the CI linter suite locally.
- `make baremetal/list`: inspect the Git-tracked hosts and hardware profiles at a glance.
- `make baremetal/list-hosts`: display only `baremetal/inventory/host_vars/` entries.
- `make baremetal/list-profiles`: display only `baremetal/inventory/profiles/hardware/` entries.

Run `make baremetal/list` before launching the ISO wizard to double-check the inventory and combine it with the troubleshooting guide (`docs/troubleshooting.md`, FR) for the most common failure modes.

## Validation and CI/CD

- `.github/workflows/build-iso.yml`: renders Autoinstall artefacts for each
  hardware profile and host, and verifies the presence of both `user-data` and
  `meta-data`. No ISO or artefact is published anymore, which keeps runtimes
  short and avoids storage pressure.
- `.github/workflows/repository-integrity.yml`: runs `yamllint`, `ansible-lint`,
  `shellcheck`, `markdownlint`, `trivy fs` (config + secrets), and validates
  inventory consistency for the automated discovery workflow.
- pip/npm/collection caches derive their keys from file hashes to remain
  idempotent.

## Security and compliance

- Replace demo SSH keys with project-specific keys encrypted through
  `secrets.sops.yaml`.
- Generate password hashes via `mkpasswd -m yescrypt` or `openssl passwd -6`
  and keep the hash encrypted in SOPS only.
- Templates enable BBR, `irqbalance`, `rp_filter=2`, and disable outgoing ICMP
  redirects.
- CI runs `scripts/ci/check-no-plaintext-secrets.py` to ensure inventories
  contain no plaintext secrets and `trivy fs` for accidental secret detection.
- Configure the GitHub secret `SOPS_AGE_KEY` (age private key) so CI can
  decrypt SOPS files. While the secret stays empty, the *Validate Bare Metal
  Configurations* workflow will be skipped automatically and no autoinstall
  render will run in CI.
- Store produced ISOs in controlled locations (CI artefacts, internal registry,
  etc.).

## Disk encryption

- The template now supports LUKS + LVM through the `disk_encryption` structure.
- Store passphrases encrypted with SOPS in
  `baremetal/inventory/group_vars/all/disk_encryption.sops.yaml`.
- Refer to the [system disk encryption guide](docs/baremetal-disk-encryption.md)
  for SOPS provisioning, host activation, validation steps, and rotation best
  practices.

## Build an ISO outside CI

CI only validates that every declared machine renders valid `user-data` and
`meta-data`. To assemble a seed or full ISO on your workstation (or a dedicated
image factory):

1. **Render the Autoinstall files**

   - Run the CI on your branch to validate the change set, then generate the
     files locally with `make baremetal/gen HOST=<host_name>` or
     `PROFILE=<hardware_profile>`.

2. **Download the official Ubuntu ISO** (only for full installer builds)

   - Grab `ubuntu-24.04-live-server-amd64.iso` from an official mirror and
     validate its checksum/signature.

3. **Build the seed ISO**

   ```bash
   make baremetal/seed HOST=<host_name>
   ```

4. **Build the full ISO (optional)**

   ```bash
   make baremetal/fulliso HOST=<host_name> \
     UBUNTU_ISO=/path/to/ubuntu-24.04-live-server-amd64.iso
   ```

5. **Inspect the output**

   - Generated artefacts reside under
     `baremetal/autoinstall/generated/<host_name>/`.
   - Validate signatures/hashes before any distribution.

## Additional resources

- [Beginner guide](docs/getting-started-beginner.md)
- [ADR 0001 — bare metal focus](docs/adr/0001-focus-baremetal.md)
- [French README](README.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
- [Troubleshooting guide (FR)](docs/troubleshooting.md)
- [ADR 0011 — automated hardware inventory](docs/adr/0011-automated-hardware-inventory.md)
