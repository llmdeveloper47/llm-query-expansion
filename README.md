# LLM Query Expansion Service on AWS EKS

A production-ready deployment of Meta's Llama 3.1 8B model for intelligent search query expansion on AWS EKS. The service improves search queries by expanding abbreviations, correcting spelling mistakes, and adding relevant context while maintaining the original search intent.

## Features

- **High-Performance Query Expansion** using Llama 3.1 8B Instruct
- **Scalable AWS EKS Deployment** with auto-scaling based on CPU, memory, and latency
- **Production-Ready Infrastructure** with Terraform IaC and CI/CD pipelines
- **Comprehensive Monitoring** with MLflow experiment tracking and Prometheus metrics
- **Cost-Optimized** with model quantization and efficient resource management
- **Queue Management** using AWS SQS for high-load scenarios
- **Load Testing** and performance optimization tools

## Prerequisites

### System Requirements
- **Operating System**: macOS, Linux, or WSL2 on Windows
- **Memory**: 8GB+ RAM for local development, 32GB+ for model inference
- **Storage**: 50GB+ free space for model weights and dependencies

### Required Tools
```bash
# Package managers
brew install --cask miniconda  # macOS
# OR for Linux:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# AWS and Kubernetes tools
brew install awscli terraform kubectl helm eksctl  # macOS
# OR for Linux (Ubuntu/Debian):
sudo apt-get update && sudo apt-get install -y awscli terraform kubectl

# Docker
brew install --cask docker  # macOS
# OR for Linux:
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
```

### AWS Account Setup
1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Domain/Route53** (optional, for custom domains)

## Hugging Face Token Setup

### 1. Create Hugging Face Account and Token

1. **Sign up** at [huggingface.co](https://huggingface.co/join)
2. **Navigate** to [Settings > Access Tokens](https://huggingface.co/settings/tokens)
3. **Create** a new token with `Read` permissions
4. **Accept** the Llama model license at [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)

### 2. Configure Token for Local Development

#### Option A: Environment Variable (Recommended)
```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Or set for current session
export HF_TOKEN="your_token_here"
```

#### Option B: Hugging Face CLI
```bash
# Install Hugging Face Hub
pip install huggingface_hub

# Login interactively
huggingface-cli login
# Enter your token when prompted
```

#### Option C: Create .env file
```bash
# Create .env file in project root
echo "HF_TOKEN=your_token_here" > .env
```

### 3. Verify Token Access
```bash
# Test token validity
python -c "
from huggingface_hub import HfApi
api = HfApi()
try:
    model_info = api.model_info('meta-llama/Llama-3.1-8B-Instruct')
    print('Token is valid and model is accessible')
except Exception as e:
    print(f' Error: {e}')
"
```

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd llm-query-expansion
```

### 2. Setup Conda Environment
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Setup development environment
./scripts/install-requirements.sh dev

# Activate environment
conda activate llm-query-expansion
```

### 3. Configure Environment Variables
```bash
# Create local environment file
cp .env.example .env

# Edit with your values
nano .env
```

Example `.env` file:
```bash
# Hugging Face Token (Required)
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Local Development Settings
LOG_LEVEL=INFO
MODEL_CACHE_DIR=/tmp/model_cache
MLFLOW_TRACKING_URI=http://localhost:5000

# AWS Settings (for local testing with AWS services)
AWS_REGION=us-west-2
AWS_PROFILE=default
```

### 4. Start Local MLflow Server
```bash
# Terminal 1: Start MLflow server
conda activate llm-query-expansion
mlflow server --host 0.0.0.0 --port 5000 &

# Verify MLflow is running
curl http://localhost:5000/health
```

### 5. Test Local Development
```bash
# Run unit tests
pytest tests/ -v

# Run compatibility tests
python test-compatibility.py

# Start local API server
cd docker/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test Local API
```bash
# Terminal 2: Test the API
# Health check
curl http://localhost:8000/health

# Test query expansion
curl -X POST http://localhost:8000/expand \
  -H "Content-Type: application/json" \
  -d '{"query": "ML algos", "use_queue": false}'

# Expected response:
# {
#   "original_query": "ML algos",
#   "expanded_query": "machine learning algorithms",
#   "processing_time": 2.5,
#   "queued": false
# }
```

### 7. Local Load Testing
```bash
# Run local load test
python tests/load_test.py --url http://localhost:8000 --users 5 --requests 20
```

## ☁️ AWS Production Deployment

### 1. Configure AWS Credentials

#### Option A: AWS CLI Configuration
```bash
aws configure
# AWS Access Key ID: [Enter your access key]
# AWS Secret Access Key: [Enter your secret key]
# Default region name: us-west-2
# Default output format: json
```

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-west-2"
```

#### Option C: IAM Roles (Recommended for EC2/Cloud9)
- Attach appropriate IAM roles to your EC2 instance
- No credentials needed in code

### 2. Verify AWS Access
```bash
# Test AWS access
aws sts get-caller-identity

# Test EKS permissions
aws eks list-clusters --region us-west-2
```

### 3. Deploy Infrastructure

#### Step 1: Initialize and Deploy with Terraform
```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan deployment (review changes)
terraform plan \
  -var="cluster_name=llm-query-expansion" \
  -var="region=us-west-2" \
  -var="desired_capacity=2"

# Apply infrastructure (create resources)
terraform apply \
  -var="cluster_name=llm-query-expansion" \
  -var="region=us-west-2" \
  -var="desired_capacity=2"

# Note down outputs
terraform output
```

#### Step 2: Run Complete Setup Script
```bash
# Return to project root
cd ..

# Set environment variables
export CLUSTER_NAME="llm-query-expansion"
export AWS_REGION="us-west-2"
export HF_TOKEN="your_huggingface_token"

# Run complete setup (infrastructure + deployment)
./scripts/setup.sh
```

### 4. Manual Deployment Steps (Alternative)

If you prefer step-by-step deployment:

#### Step 1: Configure kubectl
```bash
aws eks update-kubeconfig --region us-west-2 --name llm-query-expansion
kubectl get nodes
```

#### Step 2: Create Secrets
```bash
# Hugging Face token secret
kubectl create secret generic huggingface-token \
  --from-literal=token=$HF_TOKEN

# AWS credentials for MLflow
kubectl create secret generic aws-credentials \
  --from-literal=access-key-id=$(aws configure get aws_access_key_id) \
  --from-literal=secret-access-key=$(aws configure get aws_secret_access_key)
```

#### Step 3: Create ConfigMaps
```bash
# Get Terraform outputs
SQS_QUEUE_URL=$(cd terraform && terraform output -raw sqs_queue_url)
S3_BUCKET_NAME=$(cd terraform && terraform output -raw s3_bucket_name)

# Create AWS config
kubectl create configmap aws-config \
  --from-literal=SQS_QUEUE_URL=$SQS_QUEUE_URL \
  --from-literal=S3_BUCKET_NAME=$S3_BUCKET_NAME
```

#### Step 4: Build and Push Docker Image
```bash
# Get ECR repository URI
ECR_REPO_NAME="llm-query-expansion"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Create ECR repository
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION || true

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push image
docker build -t $ECR_REPO_NAME:latest docker/
docker tag $ECR_REPO_NAME:latest $ECR_REGISTRY/$ECR_REPO_NAME:latest
docker push $ECR_REGISTRY/$ECR_REPO_NAME:latest
```

#### Step 5: Update Kubernetes Manifests
```bash
# Update deployment with correct image
sed -i "s|image: llm-query-expansion:latest|image: $ECR_REGISTRY/$ECR_REPO_NAME:latest|g" k8s/deployment.yaml

# Update service account with role ARN
SERVICE_ROLE_ARN=$(cd terraform && terraform output -raw service_role_arn)
sed -i "s|REPLACE_WITH_ROLE_ARN|$SERVICE_ROLE_ARN|g" k8s/deployment.yaml
```

#### Step 6: Deploy to Kubernetes
```bash
# Deploy MLflow first
kubectl apply -f mlflow/k8s-deployment.yaml

# Wait for MLflow to be ready
kubectl wait --for=condition=available --timeout=300s deployment/mlflow-server

# Deploy main application
kubectl apply -f k8s/

# Wait for deployment
kubectl wait --for=condition=available --timeout=600s deployment/llm-query-expansion
```

### 5. Verify Production Deployment

#### Check Pod Status
```bash
# Check all pods
kubectl get pods

# Check logs
kubectl logs -l app=llm-query-expansion -f

# Check resource usage
kubectl top pods
```

#### Get Service Endpoints
```bash
# Get service external IPs
kubectl get services

# Example output:
# NAME           TYPE           CLUSTER-IP      EXTERNAL-IP                           PORT(S)
# llm-service    LoadBalancer   10.100.12.34    a1b2c3d4e5f6-123456789.us-west-2.elb.amazonaws.com   80:30123/TCP
# mlflow-service LoadBalancer   10.100.56.78    a9b8c7d6e5f4-987654321.us-west-2.elb.amazonaws.com   5000:30456/TCP
```

#### Test Production API
```bash
# Get external IP
EXTERNAL_IP=$(kubectl get service llm-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint
curl http://$EXTERNAL_IP/health

# Test query expansion
curl -X POST http://$EXTERNAL_IP/expand \
  -H "Content-Type: application/json" \
  -d '{"query": "AI/ML enginer jobs", "use_queue": false}'

# Test metrics
curl http://$EXTERNAL_IP/metrics
```

## Production Testing

### 1. Integration Testing
```bash
# Run full integration test suite
python tests/integration_test.py --url http://$EXTERNAL_IP
```

### 2. Load Testing
```bash
# Light load test
python tests/load_test.py --url http://$EXTERNAL_IP --users 10 --requests 50

# Heavy load test
python tests/load_test.py --url http://$EXTERNAL_IP --users 50 --requests 500
```

### 3. Scaling Test
```bash
# Check current HPA status
kubectl get hpa

# Monitor scaling during load test
watch kubectl get pods

# Check auto-scaling triggers
kubectl describe hpa llm-hpa
```

### 4. Queue Testing
```bash
# Test with queue enabled (high load simulation)
curl -X POST http://$EXTERNAL_IP/expand \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "use_queue": true}'

# Check queue status
curl http://$EXTERNAL_IP/queue/status
```

## Monitoring and Logging

### 1. Access MLflow UI
```bash
# Get MLflow external IP
MLFLOW_IP=$(kubectl get service mlflow-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "MLflow UI: http://$MLFLOW_IP:5000"
```

### 2. View Prometheus Metrics
```bash
# Port forward to access Prometheus locally
kubectl port-forward service/prometheus-service 9090:9090 &

echo "Prometheus UI: http://localhost:9090"
```

### 3. Check Application Logs
```bash
# Real-time logs
kubectl logs -l app=llm-query-expansion -f

# Logs from specific pod
kubectl logs <pod-name> -f

# Previous container logs
kubectl logs <pod-name> --previous
```

### 4. Monitor Resource Usage
```bash
# Pod resource usage
kubectl top pods

# Node resource usage
kubectl top nodes

# Detailed pod description
kubectl describe pod <pod-name>
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Pod Stuck in Pending State
```bash
# Check node resources
kubectl describe nodes

# Check pod events
kubectl describe pod <pod-name>

# Common solutions:
# - Scale cluster nodes: eksctl scale nodegroup --cluster=llm-query-expansion --nodes=3
# - Check resource requests in deployment.yaml
```

#### 2. Model Loading Failures
```bash
# Check HuggingFace token
kubectl get secret huggingface-token -o yaml

# Check pod logs for token errors
kubectl logs <pod-name> | grep -i "token\|auth\|forbidden"

# Recreate secret with correct token
kubectl delete secret huggingface-token
kubectl create secret generic huggingface-token --from-literal=token=$HF_TOKEN
kubectl rollout restart deployment/llm-query-expansion
```

#### 3. High Memory Usage (OOMKilled)
```bash
# Check memory limits
kubectl describe pod <pod-name> | grep -A 5 "Limits\|Requests"

# Increase memory limits in k8s/deployment.yaml:
# resources:
#   limits:
#     memory: "40Gi"  # Increase from 32Gi
#   requests:
#     memory: "32Gi"  # Increase from 24Gi

# Apply changes
kubectl apply -f k8s/deployment.yaml
```

#### 4. High Latency Issues
```bash
# Check current latency metrics
curl http://$EXTERNAL_IP/metrics | grep request_duration

# Enable model quantization (edit docker/app/model_handler.py)
# Scale up replicas
kubectl scale deployment llm-query-expansion --replicas=4

# Check HPA scaling
kubectl get hpa
```

#### 5. Network Connectivity Issues
```bash
# Check service endpoints
kubectl get endpoints

# Check security groups (AWS Console)
# Ensure ALB security group allows inbound traffic on port 80

# Check ALB status
kubectl describe ingress llm-ingress
```

### Debug Commands Reference
```bash
# Get cluster info
kubectl cluster-info

# Check all resources
kubectl get all

# Describe problematic resources
kubectl describe deployment llm-query-expansion
kubectl describe service llm-service
kubectl describe hpa llm-hpa

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Access pod shell
kubectl exec -it <pod-name> -- /bin/bash

# Port forward for local debugging
kubectl port-forward service/llm-service 8080:80
```

## Cost Management

### Expected Costs (us-west-2 region)
- **EKS Cluster**: ~$73/month
- **EC2 Instances (2x c5.4xlarge)**: ~$600/month
- **Load Balancer**: ~$20/month
- **S3 Storage**: ~$5/month
- **SQS**: ~$1/month
- **Total**: ~$700/month for production setup

### Cost Optimization Tips
1. **Use Spot Instances** for non-critical workloads
2. **Scale down during off-hours** using scheduled scaling
3. **Monitor unused resources** with AWS Cost Explorer
4. **Use S3 Intelligent Tiering** for model artifacts
5. **Clean up resources** when not needed

## Cleanup and Teardown

### 1. Destroy AWS Resources
```bash
# WARNING: This will delete ALL resources and data
./scripts/cleanup.sh

# Manual cleanup if script fails:
cd terraform
terraform destroy -auto-approve
```

### 2. Local Environment Cleanup
```bash
# Remove conda environment
conda deactivate
conda env remove -n llm-query-expansion

# Remove Docker images
docker rmi $(docker images -q llm-query-expansion)

# Clean up local files
rm -rf ~/.cache/huggingface/
```

### 3. Verify Cleanup
```bash
# Check no EKS clusters remain
aws eks list-clusters

# Check no EC2 instances remain
aws ec2 describe-instances --query 'Reservations[].Instances[?State.Name==`running`]'

# Check no S3 buckets remain (with your prefix)
aws s3 ls | grep llm-query-expansion
```

## CI/CD Deployment

### 1. GitHub Actions Setup
1. **Fork/clone** the repository
2. **Add secrets** in GitHub repository settings:
   ```
   AWS_ACCESS_KEY_ID: your_aws_access_key
   AWS_SECRET_ACCESS_KEY: your_aws_secret_key
   HF_TOKEN: your_huggingface_token
   ```

### 2. Automatic Deployment
```bash
# Push to main branch triggers deployment
git add .
git commit -m "Deploy to production"
git push origin main

# Monitor deployment in GitHub Actions tab
```

### 3. Manual Deployment Updates
```bash
# Deploy specific version
IMAGE_TAG=v1.0.1 ./scripts/deploy.sh

# Quick deployment of current code
./scripts/deploy.sh
```

## Additional Resources

- **Llama 3.1 Model Card**: [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
- **AWS EKS Documentation**: [AWS EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/)
- **Kubernetes Documentation**: [kubernetes.io](https://kubernetes.io/docs/)
- **MLflow Documentation**: [mlflow.org](https://mlflow.org/docs/latest/index.html)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest tests/ -v`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Important Notes

- **Hugging Face Token**: Required for model access - ensure it's kept secure
- **AWS Costs**: Monitor your AWS bill - ML workloads can be expensive
- **Model License**: Ensure compliance with Llama 3.1 license terms
- **Security**: Never commit secrets to version control
- **Resource Limits**: Ensure your AWS account has sufficient service limits

## Support

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review logs using the debug commands
3. Check [GitHub Issues](link-to-issues) for similar problems
4. Create a new issue with:
   - Error messages and logs
   - Steps to reproduce
   - Environment details (OS, AWS region, etc.)

---

