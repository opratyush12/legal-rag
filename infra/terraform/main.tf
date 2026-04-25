# ── infra/terraform/main.tf ───────────────────────────────────────────────────
# Full AWS infrastructure for legal-rag on ECS Fargate (< $25/mo)
# No NAT gateway — tasks run in public subnets with public IPs to save cost.
# ──────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

data "aws_caller_identity" "current" {}

# ══════════════════════════════════════════════════════════════════════════════
# VPC — 2 public subnets, no NAT (cost saver)
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-igw" }
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${local.name_prefix}-public-${count.index}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-public-rt" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ══════════════════════════════════════════════════════════════════════════════
# Security Groups
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_security_group" "alb" {
  name_prefix = "${local.name_prefix}-alb-"
  vpc_id      = aws_vpc.main.id
  description = "ALB - allow inbound HTTP/HTTPS"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "ecs_backend" {
  name_prefix = "${local.name_prefix}-backend-"
  vpc_id      = aws_vpc.main.id
  description = "Backend Fargate task"

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "ALB to backend"
  }

  # Allow frontend task to reach backend on port 8000
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_frontend.id]
    description     = "Frontend to backend"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "ecs_frontend" {
  name_prefix = "${local.name_prefix}-frontend-"
  vpc_id      = aws_vpc.main.id
  description = "Frontend Fargate task"

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "ALB to frontend"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "efs" {
  name_prefix = "${local.name_prefix}-efs-"
  vpc_id      = aws_vpc.main.id
  description = "EFS mount targets"

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_backend.id]
    description     = "NFS from backend"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle { create_before_destroy = true }
}

# ══════════════════════════════════════════════════════════════════════════════
# ECR Repositories
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Lifecycle policy — keep only last 5 images to stay in free tier
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ══════════════════════════════════════════════════════════════════════════════
# EFS — persistent storage for FAISS index + PDFs
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_efs_file_system" "data" {
  creation_token = "${local.name_prefix}-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = { Name = "${local.name_prefix}-efs" }
}

resource "aws_efs_mount_target" "data" {
  count           = length(aws_subnet.public)
  file_system_id  = aws_efs_file_system.data.id
  subnet_id       = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# ══════════════════════════════════════════════════════════════════════════════
# S3 — PDF archive / future bulk import
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_s3_bucket" "pdfs" {
  bucket_prefix = "${var.project}-pdfs-"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "pdfs" {
  bucket = aws_s3_bucket.pdfs.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pdfs" {
  bucket = aws_s3_bucket.pdfs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# Secrets Manager — GROQ API Key
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_secretsmanager_secret" "groq" {
  name                    = "${var.project}/groq-api-key"
  recovery_window_in_days = 0
  tags = { Name = "${local.name_prefix}-groq-key" }
}

resource "aws_secretsmanager_secret_version" "groq" {
  secret_id     = aws_secretsmanager_secret.groq.id
  secret_string = var.groq_api_key
}

resource "aws_s3_bucket_public_access_block" "pdfs" {
  bucket                  = aws_s3_bucket.pdfs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ══════════════════════════════════════════════════════════════════════════════
# ALB
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

# ── Target Groups ─────────────────────────────────────────────────────────────

resource "aws_lb_target_group" "backend" {
  name        = "${local.name_prefix}-be-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
}

resource "aws_lb_target_group" "frontend" {
  name        = "${local.name_prefix}-fe-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
}

# ── Listener — path-based routing ─────────────────────────────────────────────

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  condition {
    path_pattern { values = ["/api/*", "/health"] }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# CloudWatch Log Groups
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project}-backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project}-frontend"
  retention_in_days = 14
}

# ══════════════════════════════════════════════════════════════════════════════
# IAM — ECS Execution Role (pull images, write logs, read secrets)
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.groq.arn]
    }]
  })
}

# ══════════════════════════════════════════════════════════════════════════════
# IAM — ECS Task Role (S3, EFS access at runtime)
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "s3-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket", "s3:HeadObject"]
      Resource = [
        aws_s3_bucket.pdfs.arn,
        "${aws_s3_bucket.pdfs.arn}/*"
      ]
    }]
  })
}

# ══════════════════════════════════════════════════════════════════════════════
# IAM — GitHub Actions OIDC Role (deploy to ECR + ECS)
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "${local.name_prefix}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  name = "ecr-ecs-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
}

# ══════════════════════════════════════════════════════════════════════════════
# ECS Cluster
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_ecs_cluster" "main" {
  name = var.project

  setting {
    name  = "containerInsights"
    value = "disabled" # keep costs down
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# ECS Task Definitions
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "backend"
    image     = "${aws_ecr_repository.backend.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "PDF_LOCAL_DIR",        value = "/data/pdfs" },
      { name = "INDEX_DIR",            value = "/data/index_store" },
      { name = "PDF_STORAGE_BACKEND",  value = "local" },
      { name = "CORS_ORIGINS",         value = "[\"*\"]" },
      { name = "UVICORN_WORKERS",      value = "1" },
      { name = "PORT",                 value = "8000" },
      { name = "INDEX_S3_BUCKET",      value = aws_s3_bucket.pdfs.id },
      { name = "INDEX_S3_PREFIX",      value = "index_store/" },
      { name = "USE_BM25",             value = "false" }
    ]

    secrets = [{
      name      = "GROQ_API_KEY"
      valueFrom = aws_secretsmanager_secret.groq.arn
    }]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 180
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "backend"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 80
      protocol      = "tcp"
    }]

    healthCheck = {
      command     = ["CMD-SHELL", "wget -q --spider http://localhost:80/ || exit 1"]
      interval    = 30
      timeout     = 3
      retries     = 3
      startPeriod = 10
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "frontend"
      }
    }
  }])
}

# ══════════════════════════════════════════════════════════════════════════════
# ECS Services
# ══════════════════════════════════════════════════════════════════════════════

resource "aws_ecs_service" "backend" {
  name            = "${var.project}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_backend.id]
    assign_public_ip = true # required — no NAT gateway
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition] # CI/CD updates this
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_frontend.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition]
  }
}
