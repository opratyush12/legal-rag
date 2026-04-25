# ── infra/terraform/outputs.tf ────────────────────────────────────────────────

output "alb_dns_name" {
  description = "Public DNS of the ALB — use this to access the app"
  value       = aws_lb.main.dns_name
}

output "ecr_backend_url" {
  description = "ECR repository URL for backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for frontend image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "efs_file_system_id" {
  description = "EFS filesystem ID for data volume"
  value       = aws_efs_file_system.data.id
}

output "s3_bucket_name" {
  description = "S3 bucket for PDF archive"
  value       = aws_s3_bucket.pdfs.id
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC — set as AWS_ROLE_ARN secret"
  value       = aws_iam_role.github_actions.arn
}

output "ecs_execution_role_arn" {
  description = "ECS execution role ARN"
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}
