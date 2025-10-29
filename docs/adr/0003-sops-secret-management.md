# ADR 0003: Encrypt group variables with SOPS

## Status
Accepted

## Context
- VPS provisioning requires API tokens and administrator passwords that must be tracked in Git for GitOps but never stored in clear text.
- Existing `ansible/group_vars/vps.yml` mixed defaults and secrets without encryption, making Git history risky.
- CI pipelines and operators need deterministic, idempotent automation without manually exporting secrets.

## Decision
- Move shared VPS variables under `vps/inventory/group_vars/vps/` to keep configuration co-located with the inventory tree.
- Introduce a `secrets.sops.yaml` file encrypted with SOPS and age keys; the unencrypted template `secrets.sops.yaml.example` documents required values.
- Load secrets at runtime with `community.sops.load_vars` and fail fast if required values are missing.
- Install the `community.sops` collection and `sops`/`age` binaries in CI to preserve GitOps workflows end-to-end.

## Consequences
- Contributors must maintain age key material locally and decrypt via `sops` before editing secrets.
- Pipelines gain deterministic access to encrypted variables while keeping audit trails in Git.
- Documentation now covers the bootstrap steps to rotate keys and maintain encrypted inventory data.
