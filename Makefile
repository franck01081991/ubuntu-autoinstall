ANSIBLE ?= ansible-playbook
HOST ?= thinkcentre1
UBUNTU_ISO ?= ubuntu-24.04-live-server-amd64.iso

BAREMETAL_DIR ?= baremetal
FORMAT ?= table

.PHONY: new-host gen iso clean-generated baremetal/gen baremetal/seed baremetal/fulliso baremetal/clean baremetal/list baremetal/list-hosts baremetal/list-profiles baremetal/discover baremetal/host-init baremetal/validate lint doctor secrets-scan age/keygen age/show-recipient

REQUIRED_CMDS := python3 ansible-playbook xorriso mkpasswd sops age
OPTIONAL_CMDS := yamllint ansible-lint shellcheck markdownlint gitleaks cloud-init

AGE_KEY_DEFAULT ?= $(HOME)/.config/sops/age/keys.txt

new-host:
	@if [ -z "$(HOST)" ]; then echo "Usage: make new-host HOST=<hostname> [DISK=/dev/sdX] [SSH_KEY='ssh-ed25519 ...']" >&2; exit 1; fi
	@python3 scripts/new_host.py --host "$(HOST)" $(if $(DISK),--disk "$(DISK)") $(if $(SSH_KEY),--ssh-key "$(SSH_KEY)")

gen:
	@if [ -z "$(HOST)" ]; then echo "Usage: make gen HOST=<hostname>" >&2; exit 1; fi
	./scripts/check_inventory.sh "$(HOST)"
	cd $(BAREMETAL_DIR)/ansible/playbooks && HOST="$(HOST)" $(ANSIBLE) generate_autoinstall.yml

iso: gen
	@if [ ! -f "$(UBUNTU_ISO)" ]; then echo "Missing Ubuntu ISO: $(UBUNTU_ISO)" >&2; exit 1; fi
	bash $(BAREMETAL_DIR)/scripts/make_full_iso.sh "$(HOST)" "$(UBUNTU_ISO)"

clean-generated:
	rm -rf $(BAREMETAL_DIR)/autoinstall/generated/*

baremetal/gen: gen

baremetal/seed: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_seed_iso.sh "$(HOST)"

baremetal/fulliso: iso

baremetal/validate:
	bash $(BAREMETAL_DIR)/scripts/validate_cloud_init.sh "$(HOST)"

baremetal/host-init:
	bash scripts/bootstrap-host.sh --host $(HOST)

baremetal/clean:
	rm -rf $(BAREMETAL_DIR)/autoinstall/generated/*

baremetal/list:
	python3 scripts/list_inventory.py summary

baremetal/list-hosts:
	python3 scripts/list_inventory.py hosts

baremetal/list-profiles:
	python3 scripts/list_inventory.py summary

baremetal/discover:
	python3 scripts/discover_hardware.py --inventory $(BAREMETAL_DIR)/inventory/hosts.yml --limit $(HOST)

age/keygen:
	@output_path="$(if $(strip $(OUTPUT)),$(OUTPUT),$(AGE_KEY_DEFAULT))"; if [ -z "$$output_path" ]; then echo "Set OUTPUT=<path> or ensure AGE_KEY_DEFAULT is defined" >&2; exit 1; fi; mkdir -p "$$(dirname "$$output_path")"; if [ -f "$$output_path" ] && [ "$(OVERWRITE)" != "1" ]; then echo "age identity already exists at $$output_path. Pass OVERWRITE=1 to replace it." >&2; exit 1; fi; age-keygen -o "$$output_path"; chmod 600 "$$output_path"; echo "Public key (share in .sops.yaml):"; age-keygen -y "$$output_path"

age/show-recipient:
	@output_path="$(if $(strip $(OUTPUT)),$(OUTPUT),$(AGE_KEY_DEFAULT))"; if [ -z "$$output_path" ]; then echo "Set OUTPUT=<path> or ensure AGE_KEY_DEFAULT is defined" >&2; exit 1; fi; if [ ! -f "$$output_path" ]; then echo "No age identity found at $$output_path" >&2; exit 1; fi; age-keygen -y "$$output_path"

lint:
	yamllint ansible baremetal
ansible-lint   ansible/playbooks/common/generate_autoinstall.yml   baremetal/ansible/playbooks/generate_autoinstall.yml
	find scripts baremetal/scripts -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
	find README*.md docs -type f -name '*.md' -print0 | xargs -0 -r markdownlint

secrets-scan:
	@gitleaks detect --config gitleaks.toml --report-format sarif --report-path gitleaks.sarif --redact
	@echo 'gitleaks report generated at gitleaks.sarif'

doctor:
	@missing=0; for cmd in $(REQUIRED_CMDS); do if ! command -v $$cmd >/dev/null 2>&1; then printf 'Missing required dependency: %s
' "$$cmd" >&2; missing=1; fi; done; if [ $$missing -ne 0 ]; then echo 'Install the required tools above, then rerun `make doctor`.' >&2; exit 1; fi; optional_missing=0; for cmd in $(OPTIONAL_CMDS); do if ! command -v $$cmd >/dev/null 2>&1; then printf 'Optional tool not found (recommended for CI parity): %s
' "$$cmd" >&2; optional_missing=1; fi; done; if [ $$optional_missing -eq 0 ]; then echo 'All optional linting tools detected.'; else echo 'Installez les outils optionnels pour rester aligné avec les contrôles internes.'; fi; echo 'Environment looks good.'
