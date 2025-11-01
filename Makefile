ANSIBLE ?= ansible-playbook
HOST ?= site-a-m710q1
PROFILE ?=
UBUNTU_ISO ?= ubuntu-24.04-live-server-amd64.iso

BAREMETAL_DIR ?= baremetal
TARGET := $(if $(PROFILE),$(PROFILE),$(HOST))
FORMAT ?= table

.PHONY: baremetal/gen baremetal/seed baremetal/fulliso baremetal/clean baremetal/list baremetal/list-hosts baremetal/list-profiles baremetal/discover baremetal/host-init baremetal/validate lint doctor secrets-scan

REQUIRED_CMDS := python3 ansible-playbook xorriso mkpasswd sops age
OPTIONAL_CMDS := yamllint ansible-lint shellcheck markdownlint gitleaks cloud-init

baremetal/gen:
	cd $(BAREMETAL_DIR)/ansible/playbooks && PROFILE=$(PROFILE) HOST=$(TARGET) $(ANSIBLE) generate_autoinstall.yml

baremetal/seed: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_seed_iso.sh $(TARGET)

baremetal/fulliso: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_full_iso.sh $(TARGET) $(UBUNTU_ISO)

baremetal/validate:
	bash $(BAREMETAL_DIR)/scripts/validate_cloud_init.sh $(TARGET)

baremetal/host-init:
	bash scripts/bootstrap-host.sh --host $(HOST) --profile $(PROFILE)

baremetal/clean:
	rm -rf $(BAREMETAL_DIR)/autoinstall/generated/*

baremetal/list:
	python3 scripts/list_inventory.py --format $(FORMAT) summary

baremetal/list-hosts:
	python3 scripts/list_inventory.py --format $(FORMAT) hosts

baremetal/list-profiles:
	python3 scripts/list_inventory.py --format $(FORMAT) profiles

baremetal/discover:
	python3 scripts/discover_hardware.py --inventory $(BAREMETAL_DIR)/inventory/hosts.yml --limit $(TARGET)

lint:
	yamllint ansible baremetal
	ansible-lint \
	  ansible/playbooks/common/generate_autoinstall.yml \
	  baremetal/ansible/playbooks/generate_autoinstall.yml
	find scripts baremetal/scripts -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
	find README*.md docs -type f -name '*.md' -print0 | xargs -0 -r markdownlint

secrets-scan:
	@gitleaks detect --config gitleaks.toml --report-format sarif --report-path gitleaks.sarif --redact
	@echo 'gitleaks report generated at gitleaks.sarif'

doctor:
	@missing=0; \
	for cmd in $(REQUIRED_CMDS); do \
	  if ! command -v $$cmd >/dev/null 2>&1; then \
	    printf 'Missing required dependency: %s\n' "$$cmd" >&2; \
	    missing=1; \
	  fi; \
	done; \
	if [ $$missing -ne 0 ]; then \
	  echo 'Install the required tools above, then rerun `make doctor`.' >&2; \
	  exit 1; \
	fi; \
	optional_missing=0; \
	for cmd in $(OPTIONAL_CMDS); do \
	  if ! command -v $$cmd >/dev/null 2>&1; then \
	    printf 'Optional tool not found (recommended for CI parity): %s\n' "$$cmd" >&2; \
	    optional_missing=1; \
	  fi; \
	done; \
	if [ $$optional_missing -eq 0 ]; then \
	  echo 'All optional linting tools detected.'; \
	else \
	  echo 'Installez les outils optionnels pour rester aligné avec les contrôles internes.'; \
	fi; \
	echo 'Environment looks good.'
