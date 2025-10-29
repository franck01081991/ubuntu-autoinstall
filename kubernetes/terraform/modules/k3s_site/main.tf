terraform {
  required_version = ">= 1.5.0"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

resource "random_password" "k3s_token" {
  length  = 48
  special = false
}

resource "random_password" "clustermesh_password" {
  length  = 32
  special = false
}

resource "tls_private_key" "wireguard" {
  for_each = { for node in var.nodes : node.name => node }
  algorithm = "ed25519"
}

locals {
  control_plane_nodes = [for node in var.nodes : node if node.role == "control-plane"]
  worker_nodes        = [for node in var.nodes : node if node.role == "worker"]
  mesh_gateway_port   = 7444 + var.site_id
}

output "site_metadata" {
  description = "Informations générales pour le site."
  value = {
    site_name      = var.site_name
    site_id        = var.site_id
    pod_cidr       = var.pod_cidr
    service_cidr   = var.service_cidr
    metallb_ranges = var.metallb_addresses
    mesh_domain    = var.cluster_mesh_domain
    mesh_gateway   = {
      port = local.mesh_gateway_port
    }
  }
}

output "k3s_token" {
  description = "Jeton de bootstrap k3s (à injecter dans SOPS)."
  value       = random_password.k3s_token.result
  sensitive   = true
}

output "clustermesh_password" {
  description = "Mot de passe partagé pour Cilium ClusterMesh."
  value       = random_password.clustermesh_password.result
  sensitive   = true
}

output "wireguard_keys" {
  description = "Clés WireGuard par nœud."
  value = {
    for name, key in tls_private_key.wireguard :
    name => {
      public_key  = key.public_key_openssh
      private_key = key.private_key_pem
    }
  }
  sensitive = true
}

output "control_plane_nodes" {
  description = "Liste des nœuds control-plane."
  value       = local.control_plane_nodes
}

output "worker_nodes" {
  description = "Liste des nœuds worker."
  value       = local.worker_nodes
}
