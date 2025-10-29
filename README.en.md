# ubuntu-autoinstall-git

Provision **Ubuntu Server 24.04 LTS** per host (ThinkCentre M710q, Dell OptiPlex 3020M) using **Autoinstall + cloud-init (NoCloud)**, entirely driven by Git in a GitOps workflow.

## Table of contents
- [Overview](#overview)
- [GitOps architecture](#gitops-architecture)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start (bare metal)](#quick-start-bare-metal)
- [Hardware profiles](#hardware-profiles)
- [Bare metal host variables](#bare-metal-host-variables)
- [Managing shared variables and secrets](#managing-shared-variables-and-secrets)
- [Available Make targets](#available-make-targets)
- [Validation and testing](#validation-and-testing)
- [Continuous integration](#continuous-integration)
- [Security and compliance](#security-and-compliance)
- [VPS provisioning with Ansible (no ISO)](#vps-provisioning-with-ansible-no-iso)
- [Additional resources](#additional-resources)

## Overview
The repository now exposes two distinct GitOps tracks:

- **`baremetal/`** – renders autoinstall payloads and builds (seed/full) ISOs for physical Ubuntu Server 24.04 LTS hosts.
- **`vps/`** – drives post-install application deployment on VPS instances exclusively through Ansible (no ISO workflow).

Each bare metal host stores its variables in version control, delivering reproducible and idempotent deployments. Generated seed and full ISOs are published as pipeline artifacts for auditing purposes. A library of **hardware profiles** under `baremetal/inventory/profiles/hardware/` keeps the CI focused on validating autoinstall generation per model.

## GitOps architecture
- **Declarative definition**:
  - host-specific parameters live in `baremetal/inventory/host_vars/<host>.yml`;
  - reusable hardware profiles are tracked in `baremetal/inventory/profiles/hardware/<profile>.yml` and can be shared across sites.
- **Automated rendering**: Ansible + Jinja2 generate `user-data`/`meta-data` files in `baremetal/autoinstall/generated/<host>/`.
  - The playbook `baremetal/ansible/playbooks/generate_autoinstall.yml` resolves the `autoinstall/` and `inventory/host_vars/` paths through `{{ playbook_dir }}` so it works regardless of the execution directory (e.g. `make baremetal/gen`).
- **Controlled distribution**: CI builds the installation ISOs, stores them as artifacts, and operators retrieve them as needed.
- **Zero manual drift**: every change flows through Git, CI/CD, and the documented commands.

## Repository layout
```
baremetal/
├── ansible/           # Autoinstall rendering playbook (NoCloud)
├── autoinstall/       # Jinja2 templates + generated artefacts
├── inventory/         # Bare metal host vars & hardware profiles
└── scripts/           # ISO (seed/full) build helpers
vps/
├── ansible/           # Application provisioning playbook
└── inventory/         # VPS inventory and SOPS-encrypted secrets
ansible/               # Shared dependencies (collections, requirements)
scripts/install-sops.sh# SOPS installer (shared)
```

## Prerequisites
- Official Ubuntu 24.04 Live Server ISO (required for `make baremetal/fulliso`).
- Python 3.10+ and Ansible available in the build environment.
- System tools: `mkpasswd`, `cloud-localds`, `xorriso`, `genisoimage` (or distro equivalents).
- [SOPS](https://github.com/getsops/sops) and an [age](https://age-encryption.org/) key pair to keep sensitive variables encrypted. Use `scripts/install-sops.sh` to install the recommended (Linux amd64) release with SHA-256 verification.
- Valid SSH keys and hashed passwords (YESCRYPT recommended) for each host.

## Quick start (bare metal)
1. **Select a hardware profile (optional)**
   ```bash
   ls baremetal/inventory/profiles/hardware
   make baremetal/gen PROFILE=lenovo-m710q
   ```
   Artefacts are produced under `baremetal/autoinstall/generated/lenovo-m710q/`.
2. **Define host variables**
   ```bash
   cp baremetal/inventory/host_vars/example.yml baremetal/inventory/host_vars/site-a-m710q1.yml
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
   The ISO is exported to `baremetal/autoinstall/generated/site-a-m710q1/seed-site-a-m710q1.iso`.
5. **Run the installation**
   - Write the official Ubuntu ISO to a USB drive (USB #1).
   - Mount the seed ISO on a second USB drive or similar (USB #2).
   - Boot the installer, press `e` in GRUB, and append `autoinstall` to the Linux line.
   - The installation continues unattended via cloud-init (NoCloud).
6. **(Optional) Build a full ISO with autoinstall baked in**
   ```bash
   make baremetal/fulliso HOST=site-a-m710q1 UBUNTU_ISO=/path/ubuntu-24.04-live-server-amd64.iso
   ```
   The script `baremetal/scripts/make_full_iso.sh` replays the boot configuration from the source ISO via `xorriso` to inject the `nocloud/` payload without relying on `isolinux/` (flag `-boot_image any replay`).

## Hardware profiles
Files under `baremetal/inventory/profiles/hardware/` capture the minimal values per model (disk, NIC, demo SSH keys, etc.) required to validate autoinstall generation. Each profile can be rendered via `make baremetal/gen PROFILE=<profile>` and becomes the baseline that site-specific automation (Ansible) can extend.

- `lenovo-m710q`: ThinkCentre M710q Tiny fitted with an NVMe stick plus a 2.5" SATA bay. The profile merges both drives into the same LVM volume group to expose a single capacity pool.
  - Optimisations: installs Intel microcode, `thermald`, `powertop` (auto-tuning service) and `lm-sensors` to keep the compact chassis efficient and thermally stable.

## Bare metal host variables
Each `baremetal/inventory/host_vars/<host>.yml` file may include:

| Variable | Description |
| --- | --- |
| `hostname` | Hostname configured during installation |
| `disk_device` | Primary system disk (e.g., `/dev/nvme0n1`) |
| `additional_disk_devices` | Optional list of extra disks to fold into the LVM VG (e.g., `['/dev/sda']`) |
| `netmode` | `dhcp` or `static` |
| `nic` | Network interface (e.g., `enp1s0`) for static IP |
| `ip`, `cidr`, `gw`, `dns` | Static network parameters |
| `ssh_authorized_keys` | List of authorized SSH public keys |
| `password_hash` | Password hash (YESCRYPT or SHA512) |
| `extra_packages` | Optional list of additional packages (e.g., hardware optimisations) |
| `enable_powertop_autotune` | Enables the systemd `powertop-autotune` unit |

## Managing shared variables and secrets

- Common VPS variables live under `vps/inventory/group_vars/vps/` so they stay close to the GitOps inventory.
- Secrets are versioned in **encrypted** form with [SOPS](https://github.com/getsops/sops):
  1. Copy the template:
     ```bash
     cp vps/inventory/group_vars/vps/secrets.sops.yaml.example vps/inventory/group_vars/vps/secrets.sops.yaml
     ```
  2. Install SOPS when missing:
     ```bash
     sudo bash scripts/install-sops.sh /usr/local/bin
     ```
  3. Add your age public key to `.sops.yaml` (`age1...`).
  4. Encrypt the file:
     ```bash
     sops --encrypt --in-place vps/inventory/group_vars/vps/secrets.sops.yaml
     ```
  5. Edit the secret securely:
     ```bash
     sops vps/inventory/group_vars/vps/secrets.sops.yaml
     ```

The keys `vps_external_dns_api_token` and `vps_keycloak_admin_password` must be present in this file for the VPS playbook to run successfully. The playbook fails fast if they are missing.

## Available Make targets
- `make baremetal/gen HOST=<name>`: render `user-data` and `meta-data` under `baremetal/autoinstall/generated/<name>/`.
- `make baremetal/gen PROFILE=<profile>`: render artefacts for a hardware profile under `baremetal/autoinstall/generated/<profile>/`.
- `make baremetal/seed HOST=<name>`: build `seed-<name>.iso` (NoCloud `CIDATA`).
- `make baremetal/fulliso HOST=<name> UBUNTU_ISO=<path>`: build a full installer ISO with autoinstall and boot flags.
- `make baremetal/clean`: remove generated artefacts.
- `make vps/provision`: execute the VPS playbook (post-install, no ISO involved).
- `make vps/lint`: run `yamllint` and `ansible-lint` on the VPS track.
- `make lint`: aggregates `yamllint`, `ansible-lint`, `shellcheck`, and `markdownlint` across the repository (mirrors the “Repository Integrity” CI workflow).

## Validation and testing
- `make lint`: runs the full syntax and style suite (`yamllint`, `ansible-lint`, `shellcheck`, `markdownlint`). Requires `shellcheck` and `markdownlint` to be present locally.
- `make vps/lint`: focused linting for the VPS track (`yamllint` + `ansible-lint`).
- `ansible-lint`: re-run deep validation locally when debugging specific playbooks.
- `yamllint baremetal/inventory baremetal/ansible vps/inventory vps/ansible`: run YAML-only checks.
- `trivy fs --security-checks config,secret --severity HIGH,CRITICAL .`: local configuration & secret scanning with the same thresholds as CI.
- `pip install -r ansible/requirements.txt`: installs `ansible-core` 2.16.13 (fixes CVE-2024-8775) before running the playbooks.

## Continuous integration
- The workflow `.github/workflows/repository-integrity.yml` enforces repository hygiene:
  - **Static analysis** job: runs `yamllint`, `ansible-lint`, `shellcheck`, and `markdownlint` (same scope as `make lint`).
  - **Trivy configuration scan** job: `trivy fs` fails the run on **HIGH/CRITICAL** findings or exposed secrets.
- The workflow `.github/workflows/build-iso.yml` renders autoinstall files **per hardware model** (`PROFILE`), builds both seed and full ISOs, and uploads them as artifacts.
- To trigger manually: **Actions → Build Bare Metal ISOs → Run workflow**, optionally overriding `UBUNTU_ISO_URL`.
  - By default the CI pulls the image from `https://old-releases.ubuntu.com/releases/24.04/ubuntu-24.04-live-server-amd64.iso` to ensure long-term availability. The ISO download is cached in `.cache/` to avoid repeated transfers.
- Artefacts are grouped per hardware profile for straightforward traceability and retained for **1 day** (`retention-days: 1`).
- Before uploading, the workflow deletes existing GitHub Actions artifacts for the same profile (`autoinstall-<profile>`) to stay within the storage quota whenever the run originates from the main repository (local branches or manual dispatches).
- When the GitHub Actions quota is exceeded or the token lacks permissions, artifact uploads fail with a warning but the workflow continues (best-effort mode, artifacts must be recovered manually if needed).

## Security and compliance
- Replace example SSH keys with production-grade host/user keys.
- Generate passwords using `mkpasswd -m yescrypt` (from the `whois` package) or `openssl passwd -6` for SHA512.
- Network configuration enables BBR, sets `rp_filter=2`, disables ICMP redirects, and enables `irqbalance`.
- Store ISO artifacts produced by CI in controlled storage (e.g., GitHub Actions artifacts).

## VPS provisioning with Ansible (no ISO)
VPS instances are provisioned **exclusively** via Ansible. No ISO is ever mounted or installed for these hosts.

After installing Ubuntu on the VPS, run:

```bash
ansible-playbook -i vps/inventory/hosts.yml vps/ansible/playbooks/provision.yml -u ubuntu --become
```

Define variables via `vps/inventory/group_vars/vps/` (see previous section) or use `-e` flags for temporary overrides.

Install the required Ansible collections before running the playbook:

```bash
ansible-galaxy collection install -r ansible/collections/requirements.yml
```
The `ansible/collections/requirements.yml` file pins `community.sops` to **1.6.0**, the latest stable release available without the `--pre` flag.

## Additional resources
- [Documentation en français](README.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)
