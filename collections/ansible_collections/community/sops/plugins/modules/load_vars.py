#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: load_vars
short_description: Load variables from a SOPS-encrypted file
version_added: 1.0.0
author: GitOps Automation Bot
description:
  - Decrypts a SOPS-managed file using the local C(sops) binary and injects the resulting key/value pairs as Ansible facts.
options:
  file:
    description:
      - Path to the SOPS-encrypted file to decrypt.
    type: path
    required: true
  binary_path:
    description:
      - Path to the C(sops) executable.
    type: path
    default: sops
  output_type:
    description:
      - Output format requested from C(sops).
    type: str
    choices:
      - json
      - yaml
    default: json
extends_documentation_fragment:
  - action_common_attributes
  - action_common_attributes.ansible.builtin
notes:
  - This lightweight implementation is intended for offline environments where downloading the upstream community.sops collection
    is not possible. It relies on the SOPS CLI being available on the controller.
"""


EXAMPLES = r"""
- name: Load secrets from encrypted file
  community.sops.load_vars:
    file: vps/inventory/group_vars/vps/secrets.sops.yaml
"""


RETURN = r"""
ansible_facts:
  description: Variables loaded from the decrypted SOPS file.
  returned: always
  type: dict
"""


def decrypt_file(binary_path: str, file_path: str, output_type: str) -> Dict[str, Any]:
    if output_type == "json":
        cmd = [binary_path, "--decrypt", "--output-type", "json", file_path]
    else:
        cmd = [binary_path, "--decrypt", file_path]
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"SOPS binary not found at {binary_path}") from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover - pass through diagnostics
        raise RuntimeError(
            "Failed to decrypt SOPS file",
        ) from exc

    payload = completed.stdout
    if output_type == "json":
        try:
            return json.loads(payload or "{}")
        except json.JSONDecodeError as exc:  # pragma: no cover - protect against malformed output
            raise RuntimeError("Unable to parse JSON output from sops") from exc

    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - fallback for minimal environments
        raise RuntimeError("PyYAML is required to parse YAML output") from exc

    data = yaml.safe_load(payload)  # type: ignore[no-untyped-call]
    return data or {}


def run_module() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            file=dict(type="path", required=True),
            binary_path=dict(type="path", required=False, default="sops"),
            output_type=dict(type="str", required=False, choices=["json", "yaml"], default="json"),
        ),
        supports_check_mode=True,
    )

    file_path = module.params["file"]
    binary_path = module.params["binary_path"]
    output_type = module.params["output_type"]

    if not os.path.exists(file_path):
        module.fail_json(msg=f"SOPS file {file_path} does not exist")

    if module.check_mode:
        module.exit_json(changed=False)

    try:
        data = decrypt_file(binary_path=binary_path, file_path=file_path, output_type=output_type)
    except RuntimeError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=False, ansible_facts=data)


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
