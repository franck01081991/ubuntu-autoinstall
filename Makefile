ANSIBLE ?= ansible-playbook
HOST ?= site-a-m710q1
PROFILE ?=
UBUNTU_ISO ?= ubuntu-24.04-live-server-amd64.iso

BAREMETAL_DIR ?= baremetal
VPS_DIR ?= vps
TARGET := $(if $(PROFILE),$(PROFILE),$(HOST))

.PHONY: baremetal/gen baremetal/seed baremetal/fulliso baremetal/clean vps/provision vps/lint

baremetal/gen:
	cd $(BAREMETAL_DIR)/ansible/playbooks && PROFILE=$(PROFILE) HOST=$(TARGET) $(ANSIBLE) generate_autoinstall.yml

baremetal/seed: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_seed_iso.sh $(TARGET)

baremetal/fulliso: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_full_iso.sh $(TARGET) $(UBUNTU_ISO)

baremetal/clean:
	rm -rf $(BAREMETAL_DIR)/autoinstall/generated/*

vps/provision:
	$(ANSIBLE) -i $(VPS_DIR)/inventory/hosts.yml $(VPS_DIR)/ansible/playbooks/provision.yml

vps/lint:
	yamllint $(VPS_DIR)/inventory $(VPS_DIR)/ansible
	ansible-lint $(VPS_DIR)/ansible/playbooks/provision.yml
