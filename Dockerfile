FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    make python3 python3-yaml git xorriso squashfs-tools curl ca-certificates \
    sops age && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY . /workspace
# Exemple:
# docker build -t ubuntu-autoinstall:latest .
# docker run --rm -v $(pwd):/workspace -w /workspace ubuntu-autoinstall:latest make gen HOST=thinkcentre1
	
