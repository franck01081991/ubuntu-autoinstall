ANSIBLE ?= ansible-playbook
HOST ?= site-a-m710q1
PROFILE ?=
UBUNTU_ISO ?= ubuntu-24.04-live-server-amd64.iso

BAREMETAL_DIR ?= baremetal
VPS_DIR ?= vps
VPS_HOST ?= vps-sapinet
TARGET := $(if $(PROFILE),$(PROFILE),$(HOST))
VPS_TARGET := $(if $(PROFILE),$(PROFILE),$(VPS_HOST))

KUBERNETES_DIR ?= kubernetes
TF_ENVS := site-a site-b

.PHONY: baremetal/gen baremetal/seed baremetal/fulliso baremetal/clean \
        vps/gen vps/clean vps/provision vps/lint lint \
        kubernetes/bootstrap kubernetes/lint kubernetes/plan kubernetes/apply \
        kubernetes/security kubernetes/flux-diff

baremetal/gen:
	cd $(BAREMETAL_DIR)/ansible/playbooks && PROFILE=$(PROFILE) HOST=$(TARGET) $(ANSIBLE) generate_autoinstall.yml

baremetal/seed: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_seed_iso.sh $(TARGET)

baremetal/fulliso: baremetal/gen
	bash $(BAREMETAL_DIR)/scripts/make_full_iso.sh $(TARGET) $(UBUNTU_ISO)

baremetal/clean:
	rm -rf $(BAREMETAL_DIR)/autoinstall/generated/*

vps/gen:
	cd $(VPS_DIR)/ansible/playbooks && PROFILE=$(PROFILE) HOST=$(VPS_TARGET) $(ANSIBLE) generate_autoinstall.yml

vps/clean:
	rm -rf $(VPS_DIR)/autoinstall/generated/*

vps/provision:
	$(ANSIBLE) -i $(VPS_DIR)/inventory/hosts.yml $(VPS_DIR)/ansible/playbooks/provision.yml

vps/lint:
	yamllint $(VPS_DIR)/inventory $(VPS_DIR)/ansible
	ansible-lint $(VPS_DIR)/ansible/playbooks/provision.yml

lint:
	yamllint ansible baremetal vps .github/workflows
	ansible-lint \	
		ansible/playbooks/common/generate_autoinstall.yml \	
		baremetal/ansible/playbooks/generate_autoinstall.yml \	
		vps/ansible/playbooks/generate_autoinstall.yml \	
		vps/ansible/playbooks/provision.yml
	find scripts baremetal/scripts -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
	find README*.md docs -type f -name '*.md' -print0 | xargs -0 -r markdownlint

kubernetes/bootstrap:
	cd $(KUBERNETES_DIR)/ansible && ansible-galaxy collection install -r requirements.yml
	cd $(KUBERNETES_DIR)/ansible && ansible-playbook playbooks/site.yml

kubernetes/lint:
	yamllint $(KUBERNETES_DIR)
	ansible-lint $(KUBERNETES_DIR)/ansible/playbooks/site.yml
	for env in $(TF_ENVS); do terraform -chdir=$(KUBERNETES_DIR)/terraform/envs/$$env fmt -check; terraform -chdir=$(KUBERNETES_DIR)/terraform/envs/$$env validate; done
	find $(KUBERNETES_DIR)/flux \( -name '*.yaml' -o -name '*.yml' \) -print0 | xargs -0 -r kubeconform -summary -strict

kubernetes/plan:
	for env in $(TF_ENVS); do terraform -chdir=$(KUBERNETES_DIR)/terraform/envs/$$env init -upgrade && terraform -chdir=$(KUBERNETES_DIR)/terraform/envs/$$env plan; done

kubernetes/apply:
	for env in $(TF_ENVS); do terraform -chdir=$(KUBERNETES_DIR)/terraform/envs/$$env apply -auto-approve; done

kubernetes/security:
	tfsec $(KUBERNETES_DIR)/terraform
	checkov -d $(KUBERNETES_DIR)
	kube-linter lint $(KUBERNETES_DIR)/flux
	trivy config --severity CRITICAL,HIGH $(KUBERNETES_DIR)

kubernetes/flux-diff:
	flux diff ks flux-system --path=$(KUBERNETES_DIR)/flux/clusters/site-a || true
	flux diff ks flux-system --path=$(KUBERNETES_DIR)/flux/clusters/site-b || true
