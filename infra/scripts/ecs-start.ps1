# ecs-start.ps1 — Scale ECS services back up for a demo
# Usage: .\infra\scripts\ecs-start.ps1
# Registers fresh task definitions to avoid stale image digest issues.

$cluster = "legal-rag"
$region  = "us-east-1"

function Register-FreshTaskDef($family) {
    $td = (aws ecs describe-task-definition --task-definition $family --region $region --no-cli-pager | ConvertFrom-Json).taskDefinition
    $fields = @{family=$td.family; networkMode=$td.networkMode; requiresCompatibilities=$td.requiresCompatibilities; cpu=$td.cpu; memory=$td.memory; executionRoleArn=$td.executionRoleArn; containerDefinitions=$td.containerDefinitions}
    if ($td.taskRoleArn) { $fields.taskRoleArn = $td.taskRoleArn }
    $json = $fields | ConvertTo-Json -Depth 10
    $path = "$env:TEMP\$family-taskdef.json"
    [System.IO.File]::WriteAllText($path, $json, [System.Text.UTF8Encoding]::new($false))
    $rev = aws ecs register-task-definition --cli-input-json file://$path --region $region --query 'taskDefinition.revision' --output text --no-cli-pager
    Write-Host "  Registered $family`:$rev"
    return "${family}:${rev}"
}

Write-Host "Registering fresh task definitions..."
$backendTd  = Register-FreshTaskDef "legal-rag-backend"
$frontendTd = Register-FreshTaskDef "legal-rag-frontend"

Write-Host "`nScaling backend to 1..."
aws ecs update-service --cluster $cluster --service legal-rag-backend --task-definition $backendTd --desired-count 1 --force-new-deployment --region $region --no-cli-pager

Write-Host "Scaling frontend to 1..."
aws ecs update-service --cluster $cluster --service legal-rag-frontend --task-definition $frontendTd --desired-count 1 --force-new-deployment --region $region --no-cli-pager

Write-Host "`nServices starting. Backend takes ~3 min to become healthy (downloads FAISS index from S3)."
$alb_dns = aws elbv2 describe-load-balancers --names legal-rag-prod-alb --query 'LoadBalancers[0].DNSName' --output text --region $region 2>$null
Write-Host "URL: http://$alb_dns"
