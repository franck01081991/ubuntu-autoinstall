ANSIBLE?=ansible-playbook
HOST?=site-a-m710q1
UBUNTU_ISO?=ubuntu-24.04-live-server-amd64.iso

.PHONY: gen seed fulliso clean

gen:
	cd ansible/playbooks && HOST=$(HOST) $(ANSIBLE) generate_autoinstall.yml

seed: gen
	bash scripts/make_seed_iso.sh $(HOST)

fulliso: gen
	bash scripts/make_full_iso.sh $(HOST) $(UBUNTU_ISO)

clean:
	rm -rf autoinstall/generated/*
