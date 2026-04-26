# ecs-stop.ps1 — Scale ECS services to 0 to stop billing
# Usage: .\infra\scripts\ecs-stop.ps1

$cluster = "legal-rag"
$region  = "us-east-1"

Write-Host "Scaling backend to 0..."
aws ecs update-service --cluster $cluster --service legal-rag-backend --desired-count 0 --region $region --no-cli-pager

Write-Host "Scaling frontend to 0..."
aws ecs update-service --cluster $cluster --service legal-rag-frontend --desired-count 0 --region $region --no-cli-pager

Write-Host "`nDone! Both services scaled to 0. No Fargate tasks running = no compute charges."
Write-Host "Note: ALB (~`$16/mo) still runs. To fully stop costs, see comments below."

# ── Optional: delete the ALB to save ~$16/mo ──
# Uncomment if you want zero cost (you'll need to re-apply terraform to recreate it)
# aws elbv2 delete-load-balancer --load-balancer-arn (aws elbv2 describe-load-balancers --names legal-rag-prod-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $region) --region $region
