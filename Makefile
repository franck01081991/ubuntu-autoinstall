ANSIBLE?=ansible-playbook
HOST?=site-a-m710q1
PROFILE?=
UBUNTU_ISO?=ubuntu-24.04-live-server-amd64.iso

TARGET:=$(if $(PROFILE),$(PROFILE),$(HOST))

.PHONY: gen seed fulliso clean

gen:
	cd ansible/playbooks && PROFILE=$(PROFILE) HOST=$(TARGET) $(ANSIBLE) generate_autoinstall.yml

seed: gen
	bash scripts/make_seed_iso.sh $(TARGET)

fulliso: gen
	bash scripts/make_full_iso.sh $(TARGET) $(UBUNTU_ISO)

clean:
	rm -rf autoinstall/generated/*
