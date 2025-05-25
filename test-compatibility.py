#!/usr/bin/env python3
"""
Script to test package compatibility
"""

import sys
import importlib
import pkg_resources

def test_imports():
    """Test that all required packages can be imported"""
    required_packages = [
        'torch',
        'transformers',
        'fastapi',
        'uvicorn',
        'boto3',
        'mlflow',
        'prometheus_client',
        'psutil'
    ]
    
    failed_imports = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package}")
        except ImportError as e:
            print(f"✗ {package}: {e}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\nFailed to import: {failed_imports}")
        return False
    
    print("\n✓ All packages imported successfully!")
    return True

def test_versions():
    """Test package versions"""
    version_requirements = {
        'torch': '2.1.2',
        'transformers': '4.36.2',
        'fastapi': '0.104.1',
    }
    
    for package, expected_version in version_requirements.items():
        try:
            installed_version = pkg_resources.get_distribution(package).version
            if installed_version == expected_version:
                print(f"✓ {package}=={installed_version}")
            else:
                print(f"⚠ {package}: expected {expected_version}, got {installed_version}")
        except pkg_resources.DistributionNotFound:
            print(f"✗ {package}: not installed")

def test_cuda_availability():
    """Test CUDA availability (optional)"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("ℹ CUDA not available (CPU-only mode)")
    except ImportError:
        print("✗ PyTorch not available")

def main():
    print("Testing package compatibility...")
    print(f"Python version: {sys.version}")
    print("-" * 50)
    
    success = test_imports()
    print("\nVersion check:")
    test_versions()
    print("\nCUDA check:")
    test_cuda_availability()
    
    if success:
        print("\n All compatibility tests passed!")
        sys.exit(0)
    else:
        print("\n Some compatibility tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()