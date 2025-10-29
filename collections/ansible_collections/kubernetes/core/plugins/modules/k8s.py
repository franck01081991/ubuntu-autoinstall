#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: k8s
short_description: Apply Kubernetes manifests using kubectl
version_added: 1.0.0
author: GitOps Automation Bot
description:
  - Provides a lightweight wrapper around the C(kubectl apply) command for offline automation scenarios.
options:
  kubeconfig:
    description:
      - Path to the kubeconfig file.
    type: path
  state:
    description:
      - Desired resource state.
    type: str
    choices:
      - present
    default: present
  definition:
    description:
      - Kubernetes resource definition provided as a dictionary.
    type: dict
  src:
    description:
      - Path to a YAML manifest rendered on the controller.
    type: path
  binary_path:
    description:
      - Path to the kubectl executable.
    type: path
    default: kubectl
extends_documentation_fragment:
  - action_common_attributes
  - action_common_attributes.ansible.builtin
notes:
  - Only C(state=present) with C(definition) or C(src) is supported.
"""


EXAMPLES = r"""
- name: Ensure namespace exists
  kubernetes.core.k8s:
    kubeconfig: ~/.kube/config
    state: present
    definition:
      apiVersion: v1
      kind: Namespace
      metadata:
        name: example
"""


RETURN = r"""
changed:
  description: Whether kubectl reported resource changes.
  type: bool
  returned: always
stdout:
  description: kubectl standard output.
  type: str
  returned: always
stderr:
  description: kubectl standard error.
  type: str
  returned: always
"""


def write_definition(definition: Dict[str, Any]) -> str:
    handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml")
    yaml.safe_dump(definition, handle, sort_keys=False)
    handle.flush()
    handle.close()
    return handle.name


def run_kubectl(module: AnsibleModule, manifest_path: str) -> subprocess.CompletedProcess[str]:
    binary_path = module.params["binary_path"]
    env = os.environ.copy()
    kubeconfig = module.params.get("kubeconfig")
    if kubeconfig:
        env["KUBECONFIG"] = kubeconfig

    cmd = [binary_path, "apply", "-f", manifest_path]
    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        module.fail_json(msg=f"kubectl binary not found at {binary_path}", details=str(exc))
    except subprocess.CalledProcessError as exc:
        module.fail_json(msg="kubectl command failed", stdout=exc.stdout, stderr=exc.stderr, rc=exc.returncode)


def run_module() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            kubeconfig=dict(type="path", required=False, default=None),
            state=dict(type="str", default="present", choices=["present"]),
            definition=dict(type="dict", required=False, default=None),
            src=dict(type="path", required=False, default=None),
            binary_path=dict(type="path", default="kubectl"),
        ),
        supports_check_mode=True,
    )

    definition: Optional[Dict[str, Any]] = module.params.get("definition")
    src: Optional[str] = module.params.get("src")

    if not definition and not src:
        module.fail_json(msg="Either definition or src must be provided")

    manifest_path: Optional[str] = None

    if definition is not None:
        manifest_path = write_definition(definition)
    elif src:
        manifest_path = src
        if not Path(src).exists():
            module.fail_json(msg=f"Manifest file {src} does not exist")

    if module.check_mode:
        module.exit_json(changed=False)

    try:
        completed = run_kubectl(module, manifest_path)  # type: ignore[arg-type]
    finally:
        if definition is not None and manifest_path:
            try:
                os.unlink(manifest_path)
            except OSError:
                pass

    stdout_lower = (completed.stdout or "").lower()
    changed = any(token in stdout_lower for token in ["created", "configured", "patched", "serverside apply", "server-side apply"])

    module.exit_json(changed=changed, stdout=completed.stdout, stderr=completed.stderr)


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
