# Remote unlock LUKS (optionnel)

Objectif: déverrouiller LUKS sans clavier/écran (serveur distant) via SSH en initramfs.

## Variante simple: dropbear-initramfs
```bash
apt install -y dropbear-initramfs
echo 'DROPBEAR_OPTIONS="-p 2222 -s -j -k -I 300"' > /etc/dropbear/initramfs/dropbear.conf
mkdir -p /etc/dropbear/initramfs
cat >> /etc/dropbear/initramfs/authorized_keys <<'EOF'
ssh-ed25519 AAAA... votre_clef
EOF
update-initramfs -u
