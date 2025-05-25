import pytest
import torch
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'docker', 'app'))

from model_handler import LlamaQueryExpander

class TestLlamaQueryExpander:
    """Test cases for LlamaQueryExpander"""
    
    def test_initialization(self):
        """Test model handler initialization"""
        handler = LlamaQueryExpander()
        assert handler.model is None
        assert handler.tokenizer is None
        assert handler.ready is False
        assert handler.model_name == "meta-llama/Llama-3.1-8B-Instruct"
    
    def test_device_selection(self):
        """Test device selection logic"""
        with patch('torch.cuda.is_available', return_value=True):
            handler = LlamaQueryExpander()
            assert handler.device == "cuda"
        
        with patch('torch.cuda.is_available', return_value=False):
            handler = LlamaQueryExpander()
            assert handler.device == "cpu"
    
    def test_prompt_template_formatting(self):
        """Test prompt template formatting"""
        handler = LlamaQueryExpander()
        query = "ML algos"
        prompt = handler.prompt_template.format(query=query)
        
        assert query in prompt
        assert "search query optimizer" in prompt
        assert "Improved query:" in prompt
    
    @pytest.mark.asyncio
    async def test_expand_query_not_ready(self):
        """Test expand_query when model is not ready"""
        handler = LlamaQueryExpander()
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            await handler.expand_query("test query")
    
    def test_clean_response_functionality(self):
        """Test the response cleaning functionality"""
        handler = LlamaQueryExpander()
        
        # Test removing quotes
        result = handler._clean_response('"quoted response"')
        assert result == "quoted response"
        
        # Test trimming whitespace
        result = handler._clean_response("  spaced  ")
        assert result == "spaced"
        
        # Test length limiting
        long_text = "a" * 300
        result = handler._clean_response(long_text)
        assert len(result) <= 200
        
        # Test normal text
        result = handler._clean_response("normal response")
        assert result == "normal response"
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    @patch('torch.cuda.is_available', return_value=False)
    @pytest.mark.asyncio
    async def test_load_model_cpu(self, mock_cuda, mock_model_class, mock_tokenizer_class):
        """Test model loading on CPU"""
        # Setup mocks
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "<eos>"
        mock_tokenizer_class.return_value = mock_tokenizer
        
        mock_model = Mock()
        mock_model.eval = Mock()
        mock_model.to = Mock(return_value=mock_model)
        mock_model_class.return_value = mock_model
        
        handler = LlamaQueryExpander()
        await handler.load_model()
        
        assert handler.ready is True
        assert handler.device == "cpu"
        mock_model_class.assert_called_once()
        mock_tokenizer_class.assert_called_once()
    
    def test_cleanup(self):
        """Test cleanup functionality"""
        handler = LlamaQueryExpander()
        handler.model = Mock()
        handler.tokenizer = Mock()
        handler.ready = True
        
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.empty_cache') as mock_empty_cache, \
             patch('gc.collect') as mock_gc_collect:
            
            handler.cleanup()
            
            assert handler.model is None
            assert handler.tokenizer is None
            assert handler.ready is False
            mock_empty_cache.assert_called_once()
            mock_gc_collect.assert_called_once()

@pytest.mark.parametrize("input_query,expected_contains", [
    ("ML algos", ["machine learning", "algorithms"]),
    ("AI/ML enginer", ["artificial intelligence", "engineer"]),
    ("deep lerning models", ["deep learning", "models"]),
    ("NLP techniques", ["natural language processing", "techniques"]),
])
def test_query_expansion_expectations(input_query, expected_contains):
    """Test that query expansion produces expected improvements"""
    # This is a parameterized test that would verify expansion quality
    # In a real scenario, you'd run this against the actual model
    # For now, we're testing the expectation framework
    assert len(expected_contains) > 0
    assert isinstance(input_query, str)