#!/bin/bash

set -e

echo "Setting up LLM Query Expansion Service..."

# Check prerequisites
command -v terraform >/dev/null 2>&1 || { echo "Terraform is required but not installed. Aborting." >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed. Aborting." >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }

# Set variables
CLUSTER_NAME=${CLUSTER_NAME:-"llm-query-expansion"}
AWS_REGION=${AWS_REGION:-"us-west-2"}
ECR_REPO_NAME=${ECR_REPO_NAME:-"llm-query-expansion"}

echo "Using cluster name: $CLUSTER_NAME"
echo "Using AWS region: $AWS_REGION"

# Step 1: Deploy infrastructure with Terraform
echo "Deploying infrastructure with Terraform..."
cd terraform
terraform init
terraform plan -var="cluster_name=$CLUSTER_NAME" -var="region=$AWS_REGION"
terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="region=$AWS_REGION"

# Get outputs
SQS_QUEUE_URL=$(terraform output -raw sqs_queue_url)
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
SERVICE_ROLE_ARN=$(terraform output -raw service_role_arn)

cd ..

# Step 2: Configure kubectl
echo "Configuring kubectl..."
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Step 3: Create ECR repository
echo "Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION || \
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION

# Step 4: Build and push Docker image
echo "Building and pushing Docker image..."
ECR_REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build image
docker build -t $ECR_REPO_NAME:latest docker/

# Tag and push
docker tag $ECR_REPO_NAME:latest $ECR_REGISTRY/$ECR_REPO_NAME:latest
docker push $ECR_REGISTRY/$ECR_REPO_NAME:latest

# Step 5: Create Kubernetes secrets
echo "Creating Kubernetes secrets..."

# Hugging Face token secret
read -s -p "Enter your Hugging Face token: " HF_TOKEN
echo
kubectl create secret generic huggingface-token --from-literal=token=$HF_TOKEN --dry-run=client -o yaml | kubectl apply -f -

# AWS credentials secret for MLflow
kubectl create secret generic aws-credentials \
  --from-literal=access-key-id=$(aws configure get aws_access_key_id) \
  --from-literal=secret-access-key=$(aws configure get aws_secret_access_key) \
  --dry-run=client -o yaml | kubectl apply -f -

# AWS config
kubectl create configmap aws-config \
  --from-literal=SQS_QUEUE_URL=$SQS_QUEUE_URL \
  --from-literal=S3_BUCKET_NAME=$S3_BUCKET_NAME \
  --dry-run=client -o yaml | kubectl apply -f -

# Step 6: Install AWS Load Balancer Controller
echo "Installing AWS Load Balancer Controller..."
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json || echo "Policy already exists"

eksctl create iamserviceaccount \
  --cluster=$CLUSTER_NAME \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AWSLoadBalancerControllerIAMPolicy \
  --approve || echo "Service account already exists"

helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller || echo "Controller already installed"

# Step 7: Deploy MLflow
echo "Deploying MLflow..."
kubectl apply -f mlflow/k8s-deployment.yaml

# Step 8: Update deployment with correct image and service account
echo "Updating Kubernetes deployment files..."
sed -i "s|image: llm-query-expansion:latest|image: $ECR_REGISTRY/$ECR_REPO_NAME:latest|g" k8s/deployment.yaml
sed -i "s|REPLACE_WITH_ROLE_ARN|$SERVICE_ROLE_ARN|g" k8s/deployment.yaml

# Step 9: Deploy the application
echo "Deploying the application..."
kubectl apply -f k8s/

# Step 10: Wait for deployment
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/llm-query-expansion

# Step 11: Get service endpoint
echo "Getting service endpoint..."
kubectl get services

# Step 12: Wait for MLflow to be ready
echo "Waiting for MLflow to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/mlflow-server

echo "Setup complete!"
echo "Service endpoints:"
kubectl get services | grep -E "(llm-service|mlflow-service)"

echo ""
echo "To test the service:"
echo "1. Get the external IP: kubectl get service llm-service"
echo "2. Test health: curl http://<EXTERNAL-IP>/health"
echo "3. Test expansion: curl -X POST http://<EXTERNAL-IP>/expand -H 'Content-Type: application/json' -d '{\"query\": \"ML algos\"}'"
echo ""
echo "MLflow UI will be available at the mlflow-service external IP on port 5000"

rm -f iam_policy.json