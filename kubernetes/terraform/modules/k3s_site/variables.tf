variable "site_name" {
  description = "Nom canonique du site (ex: site-a)."
  type        = string
}

variable "site_id" {
  description = "Identifiant numérique unique du site (1..255 pour Cilium)."
  type        = number
}

variable "pod_cidr" {
  description = "CIDR du réseau pods pour ce cluster."
  type        = string
}

variable "service_cidr" {
  description = "CIDR du réseau services Kubernetes pour ce cluster."
  type        = string
}

variable "nodes" {
  description = "Définition des nœuds du site."
  type = list(object({
    name       = string
    role       = string   # control-plane ou worker
    ip_address = string
    public_ip  = string
  }))
}

variable "metallb_addresses" {
  description = "Plages IP MetalLB en L2."
  type        = list(string)
}

variable "wireguard_peers" {
  description = "Configuration des pairs WireGuard inter-sites."
  type = list(object({
    peer_name    = string
    endpoint     = string
    public_key   = string
    allowed_ips  = list(string)
  }))
  default = []
}

variable "cluster_mesh_domain" {
  description = "Nom de domaine interne utilisé par Cilium ClusterMesh."
  type        = string
  default     = "mesh.local"
}
