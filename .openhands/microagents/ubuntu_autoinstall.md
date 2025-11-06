
---
name: Ubuntu Autoinstall
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - ubuntu autoinstall
  - autoinstall
  - ubuntu installation
---

# Ubuntu Autoinstall Microagent

This microagent provides guidance and tools for working with Ubuntu autoinstall configurations.

## Security Policy

POLICY — Tool Safety (OBLIGATOIRE)
- Pour TOUT appel d’outil {execute_bash, str_replace_editor, write_file, read_file, list_dir, search_text}, inclure:
  "security_risk" ∈ {"low","medium","high"} ET "security_notes" (1 phrase).
- low = lecture seule (ls, cat, rg/grep, git status/log, diff).
- medium = modifs dans /workspace uniquement (str_replace_editor, write_file, sed -i, git add/commit).
- high = opérations potentiellement destructives (rm -rf, chmod/chown récursif, mv de masse) → NE PAS exécuter sans mon OK explicite.
- Interdits: sudo, FS hors /workspace, réseau externe non demandé.
- Montre un PLAN (3–6 étapes), attends mon “OK”, puis exécute. Max 10 actions, stop si 2 actions sans progrès.
Réponds d’abord “Policy loaded”, puis propose le PLAN.

## Common Tasks

1. Creating autoinstall configuration files
2. Validating autoinstall configurations
3. Troubleshooting autoinstall issues
4. Customizing autoinstall workflows

## Usage Examples

```bash
# Example command to create a new autoinstall configuration
execute_bash --command "touch autoinstall.yaml" --security_risk "medium" --security_notes "Creating new file in workspace"
```

```bash
# Example command to validate an existing configuration
execute_bash --command "sudo autoinstall-validate autoinstall.yaml" --security_risk "high" --security_notes "Validating configuration with sudo"
```

