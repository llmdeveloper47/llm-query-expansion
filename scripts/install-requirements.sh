#!/bin/bash

set -e

echo "Installing LLM Query Expansion Service dependencies (Pip-only approach)..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: Conda is not installed. Please install Miniconda or Anaconda first."
    echo "Download from: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Initialize conda for bash
eval "$(conda shell.bash hook)"

# Environment name
ENV_NAME="llm-query-expansion"

# Check if environment already exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Conda environment '${ENV_NAME}' already exists."
    read -p "Do you want to remove and recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing environment..."
        conda env remove -n ${ENV_NAME} -y
    else
        echo "Using existing environment..."
        conda activate ${ENV_NAME}
        echo "Environment activated. You can install additional packages manually if needed."
        exit 0
    fi
fi

echo "Creating new conda environment '${ENV_NAME}' with Python 3.9 (minimal conda setup)..."
# Create minimal conda environment with just Python and pip
conda create -n ${ENV_NAME} python=3.9 pip -y

# Activate the conda environment
echo "Activating conda environment..."
conda activate ${ENV_NAME}

# Verify Python version
python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python version: ${python_version}"

if [[ "$python_version" < "3.9" ]]; then
    echo "Error: Python 3.9+ required, found $python_version"
    exit 1
fi

# Upgrade pip and install build tools
echo "Upgrading pip and installing build tools..."
pip install --upgrade pip setuptools wheel

# Detect platform and install PyTorch accordingly
echo "Installing PyTorch..."
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS - use CPU version
    echo "Detected macOS - installing CPU-only PyTorch..."
    pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
elif command -v nvidia-smi &> /dev/null; then
    # Linux with NVIDIA GPU
    echo "Detected NVIDIA GPU - installing CUDA PyTorch..."
    pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
else
    # Linux CPU-only
    echo "Detected Linux CPU - installing CPU-only PyTorch..."
    pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
fi

# Install core ML packages
echo "Installing core ML packages..."
pip install \
    transformers==4.36.2 \
    accelerate==0.25.0 \
    bitsandbytes==0.41.3.post2 \
    sentencepiece==0.1.99 \
    tokenizers==0.15.0 \
    huggingface-hub==0.19.4

# Install API framework
echo "Installing API framework..."
pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    python-multipart==0.0.6

# Install AWS and cloud packages
echo "Installing AWS packages..."
pip install \
    boto3==1.34.34 \
    botocore==1.34.34

# Install monitoring and logging
echo "Installing monitoring packages..."
pip install \
    mlflow==2.9.2 \
    prometheus-client==0.19.0

# Install utilities
echo "Installing utility packages..."
pip install \
    httpx==0.25.2 \
    requests==2.31.0 \
    orjson==3.9.10 \
    psutil==5.9.6 \
    pyyaml==6.0.1

# Install scientific computing packages
echo "Installing scientific packages..."
pip install \
    numpy==1.24.4 \
    pandas==2.1.4 \
    scipy

# Install requirements based on environment type
if [ "$1" = "dev" ]; then
    echo "Installing development requirements..."
    
    # Testing framework
    pip install \
        pytest==7.4.4 \
        pytest-asyncio==0.21.1 \
        pytest-cov==4.1.0 \
        pytest-mock==3.12.0
    
    # Code quality tools
    pip install \
        black==23.12.1 \
        flake8==6.1.0 \
        isort==5.13.2 \
        mypy==1.8.0 \
        pre-commit==3.6.0
    
    # Development utilities
    pip install \
        jupyter==1.0.0 \
        ipykernel==6.27.1 \
        ipdb==0.13.13 \
        rich==13.7.0 \
        python-dotenv==1.0.0 \
        watchdog==3.0.0
    
    # HTTP testing
    pip install \
        aiohttp==3.9.1
    
    # Container and k8s tools
    pip install \
        docker==6.1.3 \
        kubernetes==28.1.0
    
    # Load testing
    pip install \
        locust==2.17.0
    
    # Install Jupyter kernel
    echo "Installing Jupyter kernel..."
    python -m ipykernel install --user --name=${ENV_NAME} --display-name="LLM Query Expansion"
        
elif [ "$1" = "infra" ]; then
    echo "Installing infrastructure requirements..."
    
    # AWS CLI (install via pip for consistency)
    pip install \
        awscli==1.32.34 \
        kubernetes==28.1.0 \
        python-terraform==0.10.1 \
        click==8.1.7 \
        rich==13.7.0 \
        typer==0.9.0
        
else
    echo "Installing production requirements only..."
    echo "Use 'dev' or 'infra' argument for additional packages."
fi

# Verify installation
echo "Verifying installation..."
python -c "
try:
    import torch
    import transformers
    import fastapi
    import mlflow
    print('Core packages verification:')
    print(f'  PyTorch: {torch.__version__}')
    print(f'  Transformers: {transformers.__version__}')
    print(f'  FastAPI: {fastapi.__version__}')
    print(f'  MLflow: {mlflow.__version__}')
    print(f'  CUDA available: {torch.cuda.is_available()}')
    print('All core packages imported successfully!')
except ImportError as e:
    print(f'Import error: {e}')
    exit(1)
"

echo ""
echo "Installation complete!"
echo ""
echo "To activate the environment, run:"
echo "  conda activate ${ENV_NAME}"
echo ""
echo "To deactivate, run:"
echo "  conda deactivate"
echo ""
echo "To remove the environment completely, run:"
echo "  conda env remove -n ${ENV_NAME}"
echo ""
echo "Next steps:"
echo "1. Set your Hugging Face token: export HF_TOKEN='your_token'"
echo "2. Test the installation: python test-compatibility.py"
echo "3. Start local development: cd docker/app && uvicorn main:app --reload"