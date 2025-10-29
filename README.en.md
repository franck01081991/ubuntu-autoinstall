# ubuntu-autoinstall-git

Provision **Ubuntu Server 24.04 LTS** per host (ThinkCentre M710q, Dell 3020 Tiny) using **Autoinstall + cloud-init (NoCloud)**, all driven from Git in a GitOps workflow.

## Table of contents
- [Overview](#overview)
- [GitOps architecture](#gitops-architecture)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Hardware profiles](#hardware-profiles)
- [Host variables](#host-variables)
- [Available Make targets](#available-make-targets)
- [Validation and testing](#validation-and-testing)
- [Continuous integration](#continuous-integration)
- [Security and compliance](#security-and-compliance)
- [VPS provisioning with Ansible](#vps-provisioning-with-ansible)
- [Additional resources](#additional-resources)

## Overview
This repository contains the templates and automation required to build fully automated Ubuntu installation media. Each host stores its own variables in inventory, enabling reproducible and idempotent deployments. Generated seed and full ISOs are published as pipeline artifacts for auditing purposes. A library of **hardware profiles** under `inventory/profiles/hardware/` keeps the CI focused on validating autoinstall generation per model.

## GitOps architecture
- **Declarative definition**:
  - host-specific parameters live in `inventory/host_vars/<host>.yml`;
  - reusable hardware profiles are tracked in `inventory/profiles/hardware/<profile>.yml` and can be shared across sites.
- **Automated rendering**: Ansible + Jinja2 generate `user-data`/`meta-data` files in `autoinstall/generated/<host>/`.
- **Controlled distribution**: CI builds the installation ISOs, stores them as artifacts, and operators retrieve them as needed.
- **Zero manual drift**: every change flows through Git, CI/CD, and the documented commands.

## Prerequisites
- Official Ubuntu 24.04 Live Server ISO (required for `make fulliso`).
- Python 3.10+ and Ansible available in the build environment.
- System tools: `mkpasswd`, `cloud-localds`, `xorriso`, `genisoimage` (or distro equivalents).
- [SOPS](https://github.com/getsops/sops) and an [age](https://age-encryption.org/) key pair to keep sensitive variables encrypted.
- Valid SSH keys and hashed passwords (YESCRYPT recommended) for each host.

## Quick start
1. **Select a hardware profile (optional)**
   ```bash
   ls inventory/profiles/hardware
   make gen PROFILE=lenovo-m710q
   ```
   Artifacts are produced under `autoinstall/generated/lenovo-m710q/`.
2. **Define host variables**
   ```bash
   cp inventory/host_vars/example.yml inventory/host_vars/site-a-m710q1.yml
   $EDITOR inventory/host_vars/site-a-m710q1.yml
   ```
3. **Render autoinstall files for the host**
   ```bash
   make gen HOST=site-a-m710q1
   ```
4. **Build the seed ISO (`CIDATA`)**
   ```bash
   make seed HOST=site-a-m710q1
   ```
   The ISO is exported to `autoinstall/generated/site-a-m710q1/seed-site-a-m710q1.iso`.
5. **Run the installation**
   - Write the official Ubuntu ISO to a USB drive (USB #1).
   - Mount the seed ISO on a second USB drive or similar (USB #2).
   - Boot the installer, press `e` in GRUB, and append `autoinstall` to the Linux line.
   - The installation continues unattended via cloud-init (NoCloud).
6. **(Optional) Build a full ISO with autoinstall baked in**
   ```bash
   make fulliso HOST=site-a-m710q1 UBUNTU_ISO=/path/ubuntu-24.04-live-server-amd64.iso
   ```

## Hardware profiles
Files under `inventory/profiles/hardware/` capture the minimal values per model (disk, NIC, demo SSH keys, etc.) required to validate autoinstall generation. Each profile can be rendered via `make gen PROFILE=<profile>` and becomes the baseline that site-specific automation (Ansible) can extend.

- `lenovo-m710q`: ThinkCentre M710q Tiny fitted with an NVMe stick plus a 2.5" SATA bay. The profile merges both drives into the same LVM volume group to expose a single capacity pool.
  - Optimisations: installs Intel microcode, `thermald`, `powertop` (auto-tuning service) and `lm-sensors` to keep the compact chassis efficient and thermally stable.

## Host variables
Each `inventory/host_vars/<host>.yml` file may include:

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

- Common VPS variables now live under `inventory/group_vars/vps/` so they stay close to the GitOps inventory.
- Secrets are versioned in **encrypted** form with [SOPS](https://github.com/getsops/sops):
  1. Copy the template:
     ```bash
     cp inventory/group_vars/vps/secrets.sops.yaml.example inventory/group_vars/vps/secrets.sops.yaml
     ```
  2. Add your age public key to `.sops.yaml` (`age1...`).
  3. Encrypt the file:
     ```bash
     sops --encrypt --in-place inventory/group_vars/vps/secrets.sops.yaml
     ```
  4. Edit the secret securely:
     ```bash
     sops inventory/group_vars/vps/secrets.sops.yaml
     ```

The keys `vps_external_dns_api_token` and `vps_keycloak_admin_password` must be present in this file for `vps_provision.yml` to run successfully. The playbook fails fast if they are missing.

## Available Make targets
- `make gen HOST=<name>`: render `user-data` and `meta-data` under `autoinstall/generated/<name>/`.
- `make gen PROFILE=<profile>`: render artifacts for a hardware profile under `autoinstall/generated/<profile>/`.
- `make seed HOST=<name>`: build `seed-<name>.iso` (NoCloud `CIDATA`).
- `make fulliso HOST=<name> UBUNTU_ISO=<path>`: build a full installer ISO with autoinstall and boot flags.
- `make clean`: remove generated artifacts.

## Validation and testing
- `make lint` *(if defined)*: execute the optional lint target.
- `ansible-lint`: validate roles and playbooks.
- `yamllint inventory ansible autoinstall`: check YAML syntax.
- `terraform fmt/validate` *(not applicable unless Terraform modules are added)*.

## Continuous integration
- The GitHub Actions workflow `.github/workflows/build-iso.yml` now renders autoinstall files **per hardware model** (`PROFILE`), builds both seed and full ISOs, and uploads them as artifacts.
- To trigger manually: **Actions → Build Host ISOs → Run workflow**, optionally overriding `UBUNTU_ISO_URL`.
  - By default the CI pulls the image from `https://old-releases.ubuntu.com/releases/24.04/ubuntu-24.04-live-server-amd64.iso` to ensure long-term availability. The ISO download is cached in `.cache/` to avoid repeated transfers.
- Artifacts are grouped per hardware profile for straightforward traceability.

## Security and compliance
- Replace example SSH keys with production-grade host/user keys.
- Generate passwords using `mkpasswd -m yescrypt` (from the `whois` package) or `openssl passwd -6` for SHA512.
- Network configuration enables BBR, sets `rp_filter=2`, disables ICMP redirects, and enables `irqbalance`.
- Store ISO artifacts produced by CI in controlled storage (e.g., GitHub Actions artifacts).

## VPS provisioning with Ansible
After installing Ubuntu on the VPS, run:

```bash
ansible-playbook -i inventory/hosts.yml ansible/playbooks/vps_provision.yml -u ubuntu --become
```

Define variables via `inventory/group_vars/vps/` (see previous section) or use `-e` flags for temporary overrides.

Install the required Ansible collections before running the playbook:

```bash
ansible-galaxy collection install -r ansible/collections/requirements.yml
```

## Additional resources
- [Documentation en français](README.md)
- [Ubuntu Autoinstall Reference](https://ubuntu.com/server/docs/install/autoinstall)
- [Cloud-init NoCloud Datasource](https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html)

