#!/usr/bin/env bash
# ── infra/scripts/bootstrap.sh ────────────────────────────────────────────────
# One-time setup: create AWS resources that Terraform expects to already exist,
# then initialise and apply Terraform.
#
# Prerequisites:
#   - AWS CLI configured (aws configure / SSO)
#   - Terraform >= 1.5 installed
#   - Docker running (for initial image push)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
PROJECT="legal-rag"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TF_DIR="$REPO_ROOT/infra/terraform"

echo "═══ Step 1: Create GitHub OIDC identity provider (idempotent) ═══"
OIDC_EXISTS=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?ends_with(Arn,'token.actions.githubusercontent.com')]" --output text 2>/dev/null || true)
if [ -z "$OIDC_EXISTS" ]; then
  THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "$THUMBPRINT"
  echo "  ✓ OIDC provider created"
else
  echo "  ✓ OIDC provider already exists"
fi

echo ""
echo "═══ Step 2: Create Secrets Manager secret for GROQ_API_KEY ═══"
if ! aws secretsmanager describe-secret --secret-id "$PROJECT/groq-api-key" --region "$REGION" >/dev/null 2>&1; then
  read -rsp "Enter your GROQ_API_KEY: " GROQ_KEY
  echo ""
  aws secretsmanager create-secret \
    --name "$PROJECT/groq-api-key" \
    --secret-string "$GROQ_KEY" \
    --region "$REGION" \
    --tags Key=Project,Value=$PROJECT Key=Environment,Value=prod
  echo "  ✓ Secret created"
else
  echo "  ✓ Secret already exists"
fi

echo ""
echo "═══ Step 3: Terraform init & apply ═══"
cd "$TF_DIR"
if [ ! -f terraform.tfvars ]; then
  echo "  ⚠  No terraform.tfvars found."
  echo "  Copy terraform.tfvars.example → terraform.tfvars and fill in values, then re-run."
  exit 1
fi

terraform init
terraform plan -out=plan.tfplan
echo ""
read -rp "Apply this plan? [y/N] " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
  terraform apply plan.tfplan
else
  echo "Aborted."
  exit 0
fi

echo ""
echo "═══ Step 4: Build & push initial Docker images ═══"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BACKEND="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT-backend"
ECR_FRONTEND="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT-frontend"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

echo "  Building backend..."
docker build -t "$ECR_BACKEND:latest" "$REPO_ROOT/backend"
docker push "$ECR_BACKEND:latest"

echo "  Building frontend..."
docker build -t "$ECR_FRONTEND:latest" "$REPO_ROOT/frontend"
docker push "$ECR_FRONTEND:latest"

echo ""
echo "═══ Step 5: Force new ECS deployment ═══"
aws ecs update-service --cluster "$PROJECT" --service "$PROJECT-backend"  --force-new-deployment --region "$REGION" >/dev/null
aws ecs update-service --cluster "$PROJECT" --service "$PROJECT-frontend" --force-new-deployment --region "$REGION" >/dev/null

echo ""
echo "════════════════════════════════════════════════════════"
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "check terraform output")
echo "  ✅ Deployment complete!"
echo "  🌐 App URL: http://$ALB_DNS"
echo ""
echo "  Next steps:"
echo "  1. Upload FAISS index + PDFs to EFS (see rebuild-index.sh)"
echo "  2. Set AWS_ROLE_ARN in GitHub repo secrets:"
echo "     $(terraform output -raw github_actions_role_arn 2>/dev/null || echo 'run: terraform output github_actions_role_arn')"
echo "════════════════════════════════════════════════════════"
