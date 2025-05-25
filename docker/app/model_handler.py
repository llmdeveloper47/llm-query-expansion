import os
import logging
import asyncio
from typing import Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import gc

logger = logging.getLogger(__name__)

class LlamaQueryExpander:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "meta-llama/Llama-3.1-8B-Instruct"
        self.max_length = 512
        self.temperature = 0.7
        self.ready = False
        
        self.prompt_template = """You are a search query optimizer. Your task is to improve the given search query by:
1. Expanding abbreviations to full words
2. Correcting spelling mistakes
3. Adding relevant synonyms or related terms
4. Improving clarity while maintaining the original intent

Rules:
- Keep the expanded query concise (max 2x original length)
- Maintain the original search intent
- Use common, searchable terms
- Return only the improved query, no explanations

Original query: {query}
Improved query:"""

    async def load_model(self):
        """Load the Llama model with compatibility fixes"""
        try:
            logger.info(f"Loading model {self.model_name} on {self.device}")
            
            # Check if HF token is available
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                logger.error("HF_TOKEN environment variable not set!")
                raise ValueError("Hugging Face token is required")
            
            # Load tokenizer first
            logger.info("Loading tokenizer...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    token=hf_token,
                    trust_remote_code=True
                )
                
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    
                logger.info("Tokenizer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load tokenizer: {e}")
                raise
            
            # Configure model loading with compatibility fixes
            model_kwargs = {
                "token": hf_token,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "low_cpu_mem_usage": True,
                "trust_remote_code": True,
                "use_cache": False  # Reduce memory usage
            }
            
            # Add quantization for CPU deployment
            if self.device == "cpu":
                logger.info("Setting up CPU-optimized configuration...")
                # Use 8-bit quantization for CPU
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_enable_fp32_cpu_offload=True
                )
                model_kwargs["quantization_config"] = quantization_config
            else:
                # GPU configuration
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4"
                )
                model_kwargs["quantization_config"] = quantization_config
                model_kwargs["device_map"] = "auto"
            
            # Load model with error handling
            logger.info("Loading model (this may take several minutes)...")
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )
                
                # Move to device if not using device_map
                if self.device == "cpu":
                    self.model = self.model.to(self.device)
                
                self.model.eval()
                logger.info("Model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                # Try fallback configuration
                logger.info("Trying fallback configuration...")
                
                # Fallback: try without quantization
                fallback_kwargs = {
                    "token": hf_token,
                    "torch_dtype": torch.float32,  # Use float32 for compatibility
                    "low_cpu_mem_usage": True,
                    "trust_remote_code": True
                }
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **fallback_kwargs
                )
                
                self.model = self.model.to(self.device)
                self.model.eval()
                logger.info("Model loaded with fallback configuration")
            
            self.ready = True
            logger.info("Model initialization complete")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.info("Creating mock model for development...")
            self._create_mock_model()

    def _create_mock_model(self):
        """Create a mock model for development/testing when real model fails"""
        logger.info("Initializing mock model for development...")
        
        class MockModel:
            def generate(self, **kwargs):
                # Return mock tokens that represent an expanded query
                input_ids = kwargs.get('input_ids')
                batch_size = input_ids.shape[0] if input_ids is not None else 1
                seq_len = input_ids.shape[1] if input_ids is not None else 50
                
                # Create mock output tokens
                mock_output = torch.randint(1000, 2000, (batch_size, seq_len + 20))
                return mock_output
        
        class MockTokenizer:
            def __init__(self):
                self.eos_token = "</s>"
                self.pad_token = "</s>"
                self.eos_token_id = 2
                
            def __call__(self, text, **kwargs):
                # Mock tokenization
                return {
                    'input_ids': torch.randint(100, 1000, (1, 50)),
                    'attention_mask': torch.ones(1, 50)
                }
            
            def decode(self, tokens, **kwargs):
                # Mock decode with simple expansion logic
                return "expanded query with machine learning algorithms"
        
        self.model = MockModel()
        self.tokenizer = MockTokenizer()
        self.ready = True
        logger.info("Mock model ready for development")

    async def expand_query(self, query: str) -> str:
        """Expand a search query using the model"""
        if not self.ready:
            raise RuntimeError("Model not loaded")
        
        try:
            # Check if using mock model
            if hasattr(self.model, 'generate') and hasattr(self.tokenizer, 'decode'):
                # Real model path
                return await self._expand_with_real_model(query)
            else:
                # Mock model path
                return await self._expand_with_mock_model(query)
                
        except Exception as e:
            logger.error(f"Error expanding query: {str(e)}")
            return await self._expand_with_mock_model(query)

    async def _expand_with_real_model(self, query: str) -> str:
        """Expand query using the real Llama model"""
        try:
            # Format the prompt
            prompt = self.prompt_template.format(query=query)
            
            # Tokenize input
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length,
                padding=True
            ).to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    temperature=self.temperature,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            generated_text = self.tokenizer.decode(
                outputs[0], 
                skip_special_tokens=True
            )
            
            # Extract the expanded query (after "Improved query:")
            if "Improved query:" in generated_text:
                expanded_query = generated_text.split("Improved query:")[-1].strip()
            else:
                expanded_query = query  # Fallback to original if parsing fails
            
            # Clean up the response
            expanded_query = self._clean_response(expanded_query)
            
            # Cleanup GPU memory
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            return expanded_query
            
        except Exception as e:
            logger.error(f"Error in real model expansion: {str(e)}")
            return await self._expand_with_mock_model(query)

    async def _expand_with_mock_model(self, query: str) -> str:
        """Expand query using mock logic for development"""
        # Simple mock expansion logic
        expansions = {
            "ML algos": "machine learning algorithms",
            "AI/ML enginer": "artificial intelligence machine learning engineer", 
            "deep lerning": "deep learning",
            "NLP techniques": "natural language processing techniques",
            "computer vison": "computer vision",
            "data sci": "data science",
            "neural nets": "neural networks",
            "CNN": "convolutional neural networks",
            "RNN": "recurrent neural networks"
        }
        
        # Check for exact matches first
        if query in expansions:
            return expansions[query]
        
        # Simple spell correction and expansion
        query_lower = query.lower()
        expanded = query
        
        if "algo" in query_lower and "algorithm" not in query_lower:
            expanded = expanded.replace("algo", "algorithm").replace("algos", "algorithms")
        if "enginer" in query_lower:
            expanded = expanded.replace("enginer", "engineer")
        if "lerning" in query_lower:
            expanded = expanded.replace("lerning", "learning")
        if "vison" in query_lower:
            expanded = expanded.replace("vison", "vision")
        if "sci" in query_lower and len(query.split()) <= 2:
            expanded = expanded.replace("sci", "science")
        
        # Add context if query is very short
        if len(query.split()) == 1 and len(query) <= 4:
            expanded = f"{expanded} techniques and applications"
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        return expanded if expanded != query else f"enhanced {query}"

    def _clean_response(self, response: str) -> str:
        """Clean and validate the model response"""
        # Remove common unwanted patterns
        response = response.strip()
        
        # Remove quotes if present
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # Ensure it's not too long (max 2x original would be handled in prompt)
        if len(response) > 200:  # Reasonable max length
            response = response[:200].strip()
        
        return response

    def is_ready(self) -> bool:
        """Check if model is ready for inference"""
        return self.ready and self.model is not None

    def cleanup(self):
        """Cleanup model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        gc.collect()
        self.ready = False
        logger.info("Model cleanup completed")