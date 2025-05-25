#!/bin/bash

set -e

echo "Cleaning up LLM Query Expansion Service..."

# Set variables
CLUSTER_NAME=${CLUSTER_NAME:-"llm-query-expansion"}
AWS_REGION=${AWS_REGION:-"us-west-2"}
ECR_REPO_NAME=${ECR_REPO_NAME:-"llm-query-expansion"}

# Confirm destruction
read -p "This will destroy ALL resources including the EKS cluster. Are you sure? (type 'yes' to confirm): " confirmation
if [ "$confirmation" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Update kubeconfig
echo "Updating kubeconfig..."
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME 2>/dev/null || echo "Could not update kubeconfig"

# Delete Kubernetes resources
echo "Deleting Kubernetes resources..."
kubectl delete -f k8s/ || echo "Some resources may have already been deleted"
kubectl delete -f mlflow/k8s-deployment.yaml || echo "MLflow resources may have already been deleted"

# Delete secrets and configmaps
kubectl delete secret huggingface-token aws-credentials || echo "Secrets may have already been deleted"
kubectl delete configmap aws-config llm-config || echo "ConfigMaps may have already been deleted"

# Delete AWS Load Balancer Controller
echo "Deleting AWS Load Balancer Controller..."
helm uninstall aws-load-balancer-controller -n kube-system || echo "Controller may not be installed"

# Delete service account
eksctl delete iamserviceaccount \
  --cluster=$CLUSTER_NAME \
  --namespace=kube-system \
  --name=aws-load-balancer-controller || echo "Service account may not exist"

# Delete IAM policy
aws iam delete-policy \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AWSLoadBalancerControllerIAMPolicy || echo "Policy may not exist"

# Delete ECR repository
echo "Deleting ECR repository..."
aws ecr delete-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION --force || echo "Repository may not exist"

# Destroy infrastructure with Terraform
echo "Destroying infrastructure with Terraform..."
cd terraform
terraform destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="region=$AWS_REGION"
cd ..

echo "Cleanup complete!"
echo "Note: Check your AWS console to ensure all resources have been deleted."
echo "Some resources like Load Balancers created by Kubernetes services may need manual deletion."