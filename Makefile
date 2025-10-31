ANSIBLE ?= ansible-playbook
HOST ?= site-a-m710q1
PROFILE ?=
UBUNTU_ISO ?= ubuntu-24.04-live-server-amd64.iso

BAREMETAL_DIR ?= baremetal
TARGET := $(if $(PROFILE),$(PROFILE),$(HOST))

.PHONY: baremetal/gen baremetal/seed baremetal/fulliso baremetal/clean lint doctor

REQUIRED_CMDS := python3 ansible-playbook xorriso mkpasswd sops age
OPTIONAL_CMDS := yamllint ansible-lint shellcheck markdownlint

baremetal/gen:
	cd $(BAREMETAL_DIR)/ansible/playbooks && PROFILE=$(PROFILE) HOST=$(TARGET) $(ANSIBLE) generate_autoinstall.yml

baremetal/seed: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_seed_iso.sh $(TARGET)

baremetal/fulliso: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_full_iso.sh $(TARGET) $(UBUNTU_ISO)

baremetal/clean:
	rm -rf $(BAREMETAL_DIR)/autoinstall/generated/*

lint:
	yamllint ansible baremetal .github/workflows
	ansible-lint \
	  ansible/playbooks/common/generate_autoinstall.yml \
	  baremetal/ansible/playbooks/generate_autoinstall.yml
	find scripts baremetal/scripts -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
	find README*.md docs -type f -name '*.md' -print0 | xargs -0 -r markdownlint

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
	  echo 'Install optional tools to mirror CI linting locally.'; \
	fi; \
	echo 'Environment looks good.'
