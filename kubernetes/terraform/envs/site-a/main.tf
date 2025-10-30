terraform {
  required_version = ">= 1.5.0"
  backend "s3" {
    bucket         = "gitops-terraform-state"
    key            = "kubernetes/site-a/terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "gitops-terraform-locks"
    encrypt        = true
  }
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

module "site" {
  source = "../../modules/k3s_site"

  site_name           = "site-a"
  site_id             = 1
  pod_cidr            = "10.44.0.0/16"
  service_cidr        = "10.96.0.0/16"
  metallb_addresses   = ["203.0.113.10-203.0.113.30"]
  cluster_mesh_domain = "mesh.gitops.lan"
  nodes = [
    {
      name       = "site-a-control-1"
      role       = "control-plane"
      ip_address = "10.10.0.10"
      public_ip  = "198.18.10.10"
    },
    {
      name       = "site-a-worker-1"
      role       = "worker"
      ip_address = "10.10.0.11"
      public_ip  = "198.18.10.11"
    },
    {
      name       = "site-a-worker-2"
      role       = "worker"
      ip_address = "10.10.0.12"
      public_ip  = "198.18.10.12"
    }
  ]
  wireguard_peers = [
    {
      peer_name   = "site-b"
      endpoint    = "public.site-b.example.com:51820"
      public_key  = "REPLACE_ME_WITH_PEER_KEY"
      allowed_ips = ["10.45.0.0/16", "198.51.100.40/29"]
    }
  ]
}

output "site_metadata" {
  value = module.site.site_metadata
}

output "control_plane_nodes" {
  value = module.site.control_plane_nodes
}

output "worker_nodes" {
  value = module.site.worker_nodes
}
