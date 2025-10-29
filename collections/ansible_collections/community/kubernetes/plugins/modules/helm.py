#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any, Dict

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: helm
short_description: Manage Helm releases via the Helm CLI
version_added: 1.0.0
author: GitOps Automation Bot
description:
  - Installs or upgrades a Helm release using the local Helm binary.
options:
  name:
    description:
      - Release name.
    type: str
    required: true
  chart_ref:
    description:
      - Helm chart reference (e.g. repo/chart).
    type: str
    required: true
  chart_version:
    description:
      - Optional chart version to deploy.
    type: str
  release_namespace:
    description:
      - Kubernetes namespace for the release.
    type: str
    required: true
  values:
    description:
      - Dictionary of values passed to Helm.
    type: dict
  create_namespace:
    description:
      - Whether to instruct Helm to create the namespace automatically.
    type: bool
    default: false
  kubeconfig:
    description:
      - Path to the kubeconfig file to use.
    type: path
  binary_path:
    description:
      - Path to the Helm executable.
    type: path
    default: helm
  extra_args:
    description:
      - Additional arguments passed to the Helm CLI.
    type: list
    elements: str
extends_documentation_fragment:
  - action_common_attributes
  - action_common_attributes.ansible.builtin
notes:
  - This implementation is intended for offline environments and relies on the Helm CLI being installed on the target.
"""


EXAMPLES = r"""
- name: Deploy cert-manager chart
  community.kubernetes.helm:
    name: cert-manager
    chart_ref: jetstack/cert-manager
    release_namespace: cert-manager
    values:
      installCRDs: false
"""


RETURN = r"""
changed:
  description: Whether the release was installed or upgraded.
  returned: always
  type: bool
stdout:
  description: Helm command standard output.
  returned: always
  type: str
stderr:
  description: Helm command standard error.
  returned: always
  type: str
"""


def build_values_file(values: Dict[str, Any]) -> str:
    if not values:
        raise ValueError("Values dictionary must not be empty")
    handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
    json.dump(values, handle)
    handle.flush()
    handle.close()
    return handle.name


def release_exists(module: AnsibleModule, release: str, namespace: str) -> bool:
    binary_path = module.params["binary_path"]
    cmd = [binary_path, "status", release, "-n", namespace]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError as exc:
        module.fail_json(msg=f"Helm binary not found at {binary_path}", details=str(exc))


def run_module() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            chart_ref=dict(type="str", required=True),
            chart_version=dict(type="str", required=False),
            release_namespace=dict(type="str", required=True),
            values=dict(type="dict", required=False, default=None),
            create_namespace=dict(type="bool", default=False),
            kubeconfig=dict(type="path", required=False, default=None),
            binary_path=dict(type="path", default="helm"),
            extra_args=dict(type="list", elements="str", required=False, default=None),
        ),
        supports_check_mode=True,
    )

    params = module.params
    binary_path = params["binary_path"]
    name = params["name"]
    namespace = params["release_namespace"]
    chart_ref = params["chart_ref"]
    chart_version = params.get("chart_version")
    values = params.get("values")
    create_namespace = params["create_namespace"]
    kubeconfig = params.get("kubeconfig")
    extra_args = params.get("extra_args") or []

    if module.check_mode:
        module.exit_json(changed=not release_exists(module, name, namespace))

    cmd = [binary_path, "upgrade", "--install", name, chart_ref, "-n", namespace]

    if chart_version:
        cmd.extend(["--version", chart_version])

    if create_namespace:
        cmd.append("--create-namespace")

    if values:
        values_file = build_values_file(values)
        cmd.extend(["--values", values_file])
    else:
        values_file = None

    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    if kubeconfig:
        env["KUBECONFIG"] = kubeconfig

    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        module.fail_json(msg=f"Helm binary not found at {binary_path}", details=str(exc))
    except subprocess.CalledProcessError as exc:
        module.fail_json(msg="Helm command failed", stdout=exc.stdout, stderr=exc.stderr, rc=exc.returncode)
    finally:
        if values and values_file:
            try:
                os.unlink(values_file)
            except OSError:
                pass

    stdout_lower = (completed.stdout or "").lower()
    changed = any(marker in stdout_lower for marker in ["has been upgraded", "has been installed", "upgrade succeeded", "install succeeded"])

    module.exit_json(changed=changed, stdout=completed.stdout, stderr=completed.stderr)


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
