---
name: Ubuntu Autoinstall Verification
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - ubuntu autoinstall verification
  - ubuntu autoinstall check
  - ubuntu autoinstall validate
---

# Ubuntu Autoinstall Verification Microagent

This microagent provides guidance and tools for verifying Ubuntu autoinstall configurations.

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

## Verification Process

1. List available verification commands (make help, scripts)
2. Execute ONLY the first non-destructive verification command
3. Show the output (summary) and stop

## Common Verification Commands

- `make help`: Show available make commands
- `scripts/check-config.sh`: Validate configuration files
- `scripts/test-network.sh`: Test network connectivity

## Usage Examples

```bash
# List available verification commands
execute_bash --command "make help" --security_risk "low" --security_notes "Listing available commands"

# Execute the first non-destructive verification command
execute_bash --command "./scripts/check-config.sh" --security_risk "medium" --security_notes "Running configuration check"
```
