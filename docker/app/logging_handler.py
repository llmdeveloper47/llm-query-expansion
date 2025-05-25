import os
import time
import logging
from typing import Dict, Any
import mlflow
import mlflow.sklearn
from datetime import datetime

logger = logging.getLogger(__name__)

class MLflowLogger:
    def __init__(self):
        self.tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        self.experiment_name = "query-expansion-production"
        
        # Set up MLflow
        mlflow.set_tracking_uri(self.tracking_uri)
        
        try:
            # Create experiment if it doesn't exist
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                mlflow.create_experiment(self.experiment_name)
            mlflow.set_experiment(self.experiment_name)
            logger.info(f"MLflow configured with tracking URI: {self.tracking_uri}")
        except Exception as e:
            logger.warning(f"MLflow setup failed: {str(e)}")
    
    async def log_query_expansion(self, original_query: str, expanded_query: str, processing_time: float):
        """Log query expansion results to MLflow"""
        try:
            with mlflow.start_run(run_name=f"query_expansion_{int(time.time())}"):
                # Log parameters
                mlflow.log_param("original_query", original_query)
                mlflow.log_param("expanded_query", expanded_query)
                mlflow.log_param("timestamp", datetime.utcnow().isoformat())
                
                # Log metrics
                mlflow.log_metric("processing_time_seconds", processing_time)
                mlflow.log_metric("query_length_original", len(original_query))
                mlflow.log_metric("query_length_expanded", len(expanded_query))
                mlflow.log_metric("expansion_ratio", len(expanded_query) / len(original_query) if len(original_query) > 0 else 1)
                
                # Log tags
                mlflow.set_tag("model", "llama-3.1-8b")
                mlflow.set_tag("task", "query_expansion")
                mlflow.set_tag("environment", "production")
                
        except Exception as e:
            logger.error(f"Error logging to MLflow: {str(e)}")
    
    async def log_system_metrics(self, metrics: Dict[str, Any]):
        """Log system performance metrics"""
        try:
            with mlflow.start_run(run_name=f"system_metrics_{int(time.time())}"):
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value)
                    else:
                        mlflow.log_param(key, str(value))
                
                mlflow.set_tag("type", "system_metrics")
                mlflow.set_tag("timestamp", datetime.utcnow().isoformat())
                
        except Exception as e:
            logger.error(f"Error logging system metrics to MLflow: {str(e)}")