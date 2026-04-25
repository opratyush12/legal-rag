#!/usr/bin/env bash
# ── infra/scripts/rebuild-index.sh ────────────────────────────────────────────
# Trigger a one-off ECS task to rebuild the FAISS index on the EFS volume.
# The task uses the same backend image, overriding the command to run the
# index builder script.
#
# Usage:
#   ./rebuild-index.sh                  # uses defaults
#   AWS_REGION=us-west-2 ./rebuild-index.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
PROJECT="legal-rag"
CLUSTER="$PROJECT"
TASK_FAMILY="$PROJECT-backend"

echo "═══ Rebuild FAISS index via ECS RunTask ═══"

# Get latest task definition ARN
TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition "$TASK_FAMILY" \
  --region "$REGION" \
  --query "taskDefinition.taskDefinitionArn" \
  --output text)
echo "  Task definition: $TASK_DEF_ARN"

# Get networking config from the running service
NETWORK_CONFIG=$(aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$PROJECT-backend" \
  --region "$REGION" \
  --query "services[0].networkConfiguration" \
  --output json)

echo "  Starting index rebuild task..."
TASK_ARN=$(aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$TASK_DEF_ARN" \
  --launch-type FARGATE \
  --network-configuration "$NETWORK_CONFIG" \
  --overrides '{
    "containerOverrides": [{
      "name": "backend",
      "command": ["python", "scripts/build_index.py"]
    }]
  }' \
  --region "$REGION" \
  --query "tasks[0].taskArn" \
  --output text)

echo "  Task started: $TASK_ARN"
echo ""
echo "  Monitor with:"
echo "    aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ARN --region $REGION"
echo ""
echo "  Or view logs:"
echo "    aws logs tail /ecs/$PROJECT-backend --follow --region $REGION"
