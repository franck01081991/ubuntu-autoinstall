#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import subprocess
from typing import Any

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: helm_repository
short_description: Manage Helm chart repositories via the Helm CLI
version_added: 1.0.0
author: GitOps Automation Bot
description:
  - Adds or removes Helm repositories using the C(helm) binary.
options:
  name:
    description:
      - Repository name.
    type: str
    required: true
  repo_url:
    description:
      - Repository URL. Required when C(state=present).
    type: str
  state:
    description:
      - Desired state of the repository.
    type: str
    choices:
      - present
      - absent
    default: present
  binary_path:
    description:
      - Path to the Helm executable.
    type: path
    default: helm
  update_cache:
    description:
      - Whether to refresh the repository index after ensuring the repository.
    type: bool
    default: true
extends_documentation_fragment:
  - action_common_attributes
  - action_common_attributes.ansible.builtin
notes:
  - This lightweight implementation is provided for offline scenarios. It assumes Helm is already installed on the target host.
"""


EXAMPLES = r"""
- name: Add Cilium Helm repository
  community.kubernetes.helm_repository:
    name: cilium
    repo_url: https://helm.cilium.io
    state: present
"""


RETURN = r"""
changed:
  description: Whether the repository configuration changed.
  type: bool
  returned: always
"""


def run_helm(module: AnsibleModule, args: list[str]) -> subprocess.CompletedProcess[str]:
    binary_path = module.params["binary_path"]
    cmd = [binary_path] + args
    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        module.fail_json(msg=f"Helm binary not found at {binary_path}", details=str(exc))
    except subprocess.CalledProcessError as exc:
        module.fail_json(msg="Helm command failed", stdout=exc.stdout, stderr=exc.stderr, rc=exc.returncode)


def repository_exists(module: AnsibleModule, name: str) -> bool:
    result = run_helm(module, ["repo", "list", "--output", "json"])
    try:
        repos: list[dict[str, Any]] = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:  # pragma: no cover - guard corrupted output
        module.fail_json(msg="Unable to parse helm repo list output", details=str(exc))
    return any(repo.get("name") == name for repo in repos)


def ensure_present(module: AnsibleModule) -> dict[str, Any]:
    name = module.params["name"]
    repo_url = module.params["repo_url"]
    update_cache = module.params["update_cache"]
    if not repo_url:
        module.fail_json(msg="repo_url is required when state=present")

    existed = repository_exists(module, name)
    if existed:
        # Force update to refresh repo metadata while keeping idempotency
        run_helm(module, ["repo", "add", name, repo_url, "--force-update"])
        changed = False
    else:
        run_helm(module, ["repo", "add", name, repo_url])
        changed = True

    if update_cache:
        run_helm(module, ["repo", "update", name])

    return {"changed": changed}


def ensure_absent(module: AnsibleModule) -> dict[str, Any]:
    name = module.params["name"]
    if not repository_exists(module, name):
        return {"changed": False}
    run_helm(module, ["repo", "remove", name])
    return {"changed": True}


def run_module() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            repo_url=dict(type="str", required=False),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            binary_path=dict(type="path", default="helm"),
            update_cache=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    state = module.params["state"]

    if module.check_mode:
        if state == "present":
            changed = not repository_exists(module, module.params["name"])
        else:
            changed = repository_exists(module, module.params["name"])
        module.exit_json(changed=changed)

    if state == "present":
        result = ensure_present(module)
    else:
        result = ensure_absent(module)

    module.exit_json(**result)


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
