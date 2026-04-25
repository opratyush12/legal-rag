# ── infra/terraform/variables.tf ──────────────────────────────────────────────
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name used for tagging and naming"
  type        = string
  default     = "legal-rag"
}

variable "environment" {
  description = "Environment name (prod, staging)"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (need ≥ 2 for ALB)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "availability_zones" {
  description = "AZs for the subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ── Fargate sizing ────────────────────────────────────────────────────────────
variable "backend_cpu" {
  type    = number
  default = 1024 # 1 vCPU
}

variable "backend_memory" {
  type    = number
  default = 2048 # 2 GB (sufficient for FAISS-only, no BM25)
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "backend_desired_count" {
  type    = number
  default = 1
}

variable "frontend_desired_count" {
  type    = number
  default = 1
}

# ── Secrets ───────────────────────────────────────────────────────────────────
variable "groq_api_key" {
  description = "GROQ API key to store in Secrets Manager"
  type        = string
  sensitive   = true
}

# ── GitHub OIDC ───────────────────────────────────────────────────────────────
variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo name (without org prefix)"
  type        = string
  default     = "legal-rag"
}
