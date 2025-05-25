import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Fixed imports - changed from relative to absolute imports
from model_handler import LlamaQueryExpander
from queue_handler import SQSHandler
from logging_handler import MLflowLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')
ERROR_COUNT = Counter('errors_total', 'Total errors')

# Global variables
model_handler: Optional[LlamaQueryExpander] = None
sqs_handler: Optional[SQSHandler] = None
mlflow_logger: Optional[MLflowLogger] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global model_handler, sqs_handler, mlflow_logger
    
    logger.info("Starting up application...")
    
    try:
        # Initialize model handler
        model_handler = LlamaQueryExpander()
        await model_handler.load_model()
        
        # Initialize SQS handler
        sqs_queue_url = os.getenv("SQS_QUEUE_URL")
        if sqs_queue_url:
            sqs_handler = SQSHandler(sqs_queue_url)
        
        # Initialize MLflow logger
        mlflow_logger = MLflowLogger()
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        # Continue without some components for local development
        if not model_handler:
            logger.warning("Model handler failed to initialize - creating mock handler")
            # Create a simple mock for local development
            class MockModelHandler:
                def __init__(self):
                    self.ready = True
                def is_ready(self):
                    return self.ready
                async def expand_query(self, query: str) -> str:
                    await asyncio.sleep(0.1)  # Simulate processing
                    return f"expanded: {query}"
            model_handler = MockModelHandler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if model_handler and hasattr(model_handler, 'cleanup'):
        model_handler.cleanup()

app = FastAPI(
    title="LLM Query Expansion API",
    description="API for expanding search queries using Llama 3.1 8B",
    version="1.0.0",
    lifespan=lifespan
)

class QueryRequest(BaseModel):
    query: str
    use_queue: bool = False

class QueryResponse(BaseModel):
    original_query: str
    expanded_query: str
    processing_time: float
    queued: bool = False

@app.get("/")
async def root():
    return {
        "message": "LLM Query Expansion Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model_handler and model_handler.is_ready():
        return {"status": "healthy", "model_loaded": True}
    return {"status": "unhealthy", "model_loaded": False}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/expand", response_model=QueryResponse)
async def expand_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Expand a search query"""
    start_time = time.time()
    REQUEST_COUNT.inc()
    
    try:
        if not model_handler or not model_handler.is_ready():
            ERROR_COUNT.inc()
            raise HTTPException(status_code=503, detail="Model not ready")
        
        # Check if we should queue the request (high load scenario)
        if request.use_queue and sqs_handler:
            # Queue the request for background processing
            message_id = await sqs_handler.send_message({
                "query": request.query,
                "timestamp": time.time()
            })
            
            return QueryResponse(
                original_query=request.query,
                expanded_query="Request queued for processing",
                processing_time=time.time() - start_time,
                queued=True
            )
        
        # Process immediately
        expanded_query = await model_handler.expand_query(request.query)
        processing_time = time.time() - start_time
        
        # Log to MLflow in background
        if mlflow_logger:
            background_tasks.add_task(
                mlflow_logger.log_query_expansion,
                request.query,
                expanded_query,
                processing_time
            )
        
        REQUEST_LATENCY.observe(processing_time)
        
        logger.info(f"Expanded query: '{request.query}' -> '{expanded_query}' ({processing_time:.3f}s)")
        
        return QueryResponse(
            original_query=request.query,
            expanded_query=expanded_query,
            processing_time=processing_time,
            queued=False
        )
        
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status")
async def queue_status():
    """Get queue status"""
    if not sqs_handler:
        return {"queue_enabled": False}
    
    try:
        status = await sqs_handler.get_queue_status()
        return {"queue_enabled": True, **status}
    except Exception as e:
        return {"queue_enabled": True, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)