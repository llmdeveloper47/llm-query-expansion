import asyncio
import json
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SQSHandler:
    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        self.sqs = boto3.client('sqs')
    
    async def send_message(self, message_body: Dict[str, Any]) -> str:
        """Send a message to the SQS queue"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sqs.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(message_body)
                )
            )
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Error sending message to SQS: {str(e)}")
            raise
    
    async def receive_messages(self, max_messages: int = 10) -> list:
        """Receive messages from the SQS queue"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=max_messages,
                    WaitTimeSeconds=20  # Long polling
                )
            )
            return response.get('Messages', [])
        except ClientError as e:
            logger.error(f"Error receiving messages from SQS: {str(e)}")
            raise
    
    async def delete_message(self, receipt_handle: str):
        """Delete a message from the SQS queue"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=receipt_handle
                )
            )
        except ClientError as e:
            logger.error(f"Error deleting message from SQS: {str(e)}")
            raise
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get queue attributes and status"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sqs.get_queue_attributes(
                    QueueUrl=self.queue_url,
                    AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
                )
            )
            attributes = response['Attributes']
            return {
                'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0))
            }
        except ClientError as e:
            logger.error(f"Error getting queue status: {str(e)}")
            raise