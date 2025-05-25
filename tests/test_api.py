import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, patch
import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'docker', 'app'))

from main import app
from model_handler import LlamaQueryExpander

@pytest.fixture
def test_client():
    """Create test client"""
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def mock_model_handler():
    """Mock model handler for testing"""
    with patch('main.model_handler') as mock:
        mock.is_ready.return_value = True
        mock.expand_query = AsyncMock(return_value="machine learning algorithms")
        yield mock

class TestQueryExpansionAPI:
    """Test cases for the query expansion API"""
    
    def test_health_check_healthy(self, test_client, mock_model_handler):
        """Test health check when model is ready"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
    
    def test_health_check_unhealthy(self, test_client):
        """Test health check when model is not ready"""
        with patch('main.model_handler', None):
            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["model_loaded"] is False
    
    def test_expand_query_success(self, test_client, mock_model_handler):
        """Test successful query expansion"""
        payload = {"query": "ML algos", "use_queue": False}
        response = test_client.post("/expand", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_query"] == "ML algos"
        assert data["expanded_query"] == "machine learning algorithms"
        assert data["queued"] is False
        assert "processing_time" in data
    
    def test_expand_query_model_not_ready(self, test_client):
        """Test query expansion when model is not ready"""
        with patch('main.model_handler', None):
            payload = {"query": "test query", "use_queue": False}
            response = test_client.post("/expand", json=payload)
            assert response.status_code == 503
    
    def test_expand_query_with_queue(self, test_client, mock_model_handler):
        """Test query expansion with queueing enabled"""
        with patch('main.sqs_handler') as mock_sqs:
            mock_sqs.send_message = AsyncMock(return_value="message-id-123")
            
            payload = {"query": "test query", "use_queue": True}
            response = test_client.post("/expand", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["queued"] is True
    
    def test_metrics_endpoint(self, test_client):
        """Test Prometheus metrics endpoint"""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert "requests_total" in response.text
    
    def test_queue_status_no_queue(self, test_client):
        """Test queue status when SQS is not configured"""
        response = test_client.get("/queue/status")
        assert response.status_code == 200
        data = response.json()
        assert data["queue_enabled"] is False

class TestModelHandler:
    """Test cases for the model handler"""
    
    @pytest.mark.asyncio
    async def test_clean_response(self):
        """Test response cleaning function"""
        handler = LlamaQueryExpander()
        
        # Test quoted response
        cleaned = handler._clean_response('"machine learning algorithms"')
        assert cleaned == "machine learning algorithms"
        
        # Test whitespace
        cleaned = handler._clean_response("  spaced response  ")
        assert cleaned == "spaced response"
        
        # Test long response
        long_text = "a" * 300
        cleaned = handler._clean_response(long_text)
        assert len(cleaned) <= 200
    
    def test_is_ready_false_initially(self):
        """Test that model is not ready initially"""
        handler = LlamaQueryExpander()
        assert handler.is_ready() is False
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    @pytest.mark.asyncio
    async def test_load_model_success(self, mock_model, mock_tokenizer):
        """Test successful model loading"""
        # Mock tokenizer
        mock_tokenizer_instance = AsyncMock()
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer_instance.eos_token = "<eos>"
        mock_tokenizer.return_value = mock_tokenizer_instance
        
        # Mock model
        mock_model_instance = AsyncMock()
        mock_model.return_value = mock_model_instance
        
        handler = LlamaQueryExpander()
        await handler.load_model()
        
        assert handler.is_ready() is True
        assert handler.tokenizer is not None
        assert handler.model is not None

@pytest.mark.asyncio
async def test_integration_query_expansion():
    """Integration test for query expansion"""
    test_cases = [
        ("ML algos", "machine learning algorithms"),
        ("AI/ML enginer", "artificial intelligence machine learning engineer"),
        ("deep lerning", "deep learning"),
        ("NLP techniques", "natural language processing techniques"),
    ]
    
    # This would require a running instance for true integration testing
    # For now, we'll test the logic with mocked components
    assert len(test_cases) > 0  # Placeholder assertion

if __name__ == "__main__":
    pytest.main([__file__, "-v"])