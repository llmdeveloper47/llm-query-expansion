#!/bin/bash

set -e

echo "Deploying LLM Query Expansion Service updates..."

# Set variables
CLUSTER_NAME=${CLUSTER_NAME:-"llm-query-expansion"}
AWS_REGION=${AWS_REGION:-"us-west-2"}
ECR_REPO_NAME=${ECR_REPO_NAME:-"llm-query-expansion"}
IMAGE_TAG=${IMAGE_TAG:-$(git rev-parse --short HEAD)}

echo "Deploying with image tag: $IMAGE_TAG"

# Update kubeconfig
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Build and push new image
echo "Building and pushing Docker image..."
ECR_REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build image
docker build -t $ECR_REPO_NAME:$IMAGE_TAG docker/

# Tag and push
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPO_NAME:latest
docker push $ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG
docker push $ECR_REGISTRY/$ECR_REPO_NAME:latest

# Update deployment
echo "Updating deployment..."
kubectl set image deployment/llm-query-expansion llm-api=$ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG

# Wait for rollout
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/llm-query-expansion --timeout=600s

# Run smoke test
echo "Running smoke test..."
EXTERNAL_IP=$(kubectl get service llm-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

if [ -n "$EXTERNAL_IP" ]; then
    echo "Testing health endpoint..."
    curl -f http://$EXTERNAL_IP/health || { echo "Health check failed!"; exit 1; }
    
    echo "Testing query expansion..."
    curl -X POST http://$EXTERNAL_IP/expand \
      -H "Content-Type: application/json" \
      -d '{"query": "ML algos", "use_queue": false}' || { echo "Expansion test failed!"; exit 1; }
    
    echo "Deployment successful!"
else
    echo "Warning: Could not get external IP for smoke test"
fi

echo "Deployment complete!"