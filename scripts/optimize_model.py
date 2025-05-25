#!/usr/bin/env python3
"""
Script to optimize the Llama model for better performance
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from optimum.onnxruntime import ORTModelForCausalLM
from optimum.onnxruntime.configuration import OptimizationConfig
import argparse
import os

def optimize_model_with_onnx(model_name: str, output_dir: str):
    """Convert model to ONNX for better CPU performance"""
    print(f"Converting {model_name} to ONNX...")
    
    # Load the model
    model = ORTModelForCausalLM.from_pretrained(
        model_name,
        export=True,
        use_cache=False
    )
    
    # Configure optimization
    optimization_config = OptimizationConfig(
        optimization_level="all",
        optimize_for_gpu=False,
        fp16=False,
        use_gpu=False
    )
    
    # Optimize the model
    model.optimize(optimization_config)
    
    # Save optimized model
    model.save_pretrained(output_dir)
    
    print(f"Optimized model saved to {output_dir}")

def quantize_model_int8(model_name: str, output_dir: str):
    """Quantize model to INT8 for reduced memory usage"""
    from transformers import BitsAndBytesConfig
    
    print(f"Quantizing {model_name} to INT8...")
    
    quantization_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_enable_fp32_cpu_offload=True
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Save quantized model
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"Quantized model saved to {output_dir}")

def benchmark_model(model_path: str, test_queries: list):
    """Benchmark model performance"""
    import time
    
    print(f"Benchmarking model at {model_path}...")
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    times = []
    
    for query in test_queries:
        start_time = time.time()
        
        inputs = tokenizer(
            f"Expand this query: {query}",
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    print(f"Average inference time: {avg_time:.3f} seconds")
    print(f"Throughput: {1/avg_time:.2f} queries/second")
    
    return avg_time

def main():
    parser = argparse.ArgumentParser(description="Optimize Llama model for deployment")
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct", help="Model name")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--method", choices=["onnx", "quantize", "benchmark"], required=True)
    
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    test_queries = [
        "ML algos",
        "AI/ML enginer",
        "deep lerning models",
        "NLP techniques",
        "computer vison"
    ]
    
    if args.method == "onnx":
        optimize_model_with_onnx(args.model, args.output)
    elif args.method == "quantize":
        quantize_model_int8(args.model, args.output)
    elif args.method == "benchmark":
        benchmark_model(args.model, test_queries)

if __name__ == "__main__":
    main()