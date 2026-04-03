"""Kafka event streaming client.

This module provides Kafka producer and consumer classes for event streaming
across the Customer Success platform.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaConnectionError
from aiokafka.structs import ConsumerRecord


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Topic Definitions
# ============================================================================

TOPICS = {
    # Incoming messages from all channels
    "CUSTOMER_MESSAGES": "customer-messages",

    # Agent performance metrics
    "AGENT_METRICS": "agent-metrics",

    # Escalations to human agents
    "ESCALATIONS": "escalations",

    # Ticket events (created, updated, resolved)
    "TICKET_EVENTS": "ticket-events",

    # Conversation events
    "CONVERSATION_EVENTS": "conversation-events",

    # Channel-specific events
    "EMAIL_EVENTS": "email-events",
    "WHATSAPP_EVENTS": "whatsapp-events",
    "WEB_FORM_EVENTS": "web-form-events",

    # System events
    "SYSTEM_EVENTS": "system-events",

    # Dead letter queue for failed messages
    "DLQ": "dead-letter-queue"
}


# ============================================================================
# Kafka Producer
# ============================================================================

class FTEKafkaProducer:
    """Kafka producer for publishing events.

    This producer handles:
    - Event serialization
    - Automatic retries
    - Error handling
    - Metrics tracking
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        client_id: str = "fte-producer",
        compression_type: str = "gzip",
        max_retries: int = 3
    ):
        """Initialize Kafka producer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            client_id: Client identifier
            compression_type: Compression algorithm (gzip, snappy, lz4)
            max_retries: Maximum retry attempts
        """
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092"
        )
        self.client_id = client_id
        self.compression_type = compression_type
        self.max_retries = max_retries

        self.producer: Optional[AIOKafkaProducer] = None
        self._is_started = False

        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "bytes_sent": 0
        }

    async def start(self):
        """Start the Kafka producer."""
        if self._is_started:
            logger.warning("Producer already started")
            return

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                compression_type=self.compression_type,
                value_serializer=self._serialize_value,
                key_serializer=self._serialize_key,
                max_request_size=1048576,  # 1MB
                request_timeout_ms=30000,
                retry_backoff_ms=100,
                acks='all'  # Wait for all replicas
            )

            await self.producer.start()
            self._is_started = True

            logger.info(
                f"Kafka producer started: {self.bootstrap_servers} "
                f"(client_id={self.client_id})"
            )

        except KafkaConnectionError as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to start producer: {str(e)}")
            raise

    async def stop(self):
        """Stop the Kafka producer."""
        if not self._is_started:
            return

        try:
            if self.producer:
                await self.producer.stop()

            self._is_started = False

            logger.info(
                f"Kafka producer stopped. Stats: "
                f"sent={self.stats['messages_sent']}, "
                f"failed={self.stats['messages_failed']}, "
                f"bytes={self.stats['bytes_sent']}"
            )

        except Exception as e:
            logger.error(f"Error stopping producer: {str(e)}")

    async def send(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send a message to Kafka topic.

        Args:
            topic: Topic name
            value: Message value (will be JSON serialized)
            key: Optional message key
            headers: Optional message headers

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_started:
            raise RuntimeError("Producer not started. Call start() first.")

        try:
            # Add timestamp if not present
            if 'timestamp' not in value:
                value['timestamp'] = datetime.utcnow().isoformat()

            # Convert headers to bytes
            kafka_headers = None
            if headers:
                kafka_headers = [
                    (k, v.encode('utf-8')) for k, v in headers.items()
                ]

            # Send message
            await self.producer.send_and_wait(
                topic,
                value=value,
                key=key,
                headers=kafka_headers
            )

            # Update stats
            self.stats['messages_sent'] += 1
            self.stats['bytes_sent'] += len(json.dumps(value))

            logger.debug(f"Sent message to {topic}: key={key}")
            return True

        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {str(e)}")
            self.stats['messages_failed'] += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {str(e)}")
            self.stats['messages_failed'] += 1
            return False

    async def send_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]]
    ) -> int:
        """Send a batch of messages to Kafka topic.

        Args:
            topic: Topic name
            messages: List of message values

        Returns:
            Number of messages sent successfully
        """
        sent_count = 0

        for message in messages:
            if await self.send(topic, message):
                sent_count += 1

        return sent_count

    def _serialize_value(self, value: Dict[str, Any]) -> bytes:
        """Serialize message value to JSON bytes.

        Args:
            value: Message value

        Returns:
            JSON bytes
        """
        return json.dumps(value).encode('utf-8')

    def _serialize_key(self, key: Optional[str]) -> Optional[bytes]:
        """Serialize message key to bytes.

        Args:
            key: Message key

        Returns:
            Key bytes or None
        """
        if key is None:
            return None
        return key.encode('utf-8')

    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()


# ============================================================================
# Kafka Consumer
# ============================================================================

class FTEKafkaConsumer:
    """Kafka consumer for consuming events.

    This consumer handles:
    - Event deserialization
    - Message processing
    - Offset management
    - Error handling
    """

    def __init__(
        self,
        topics: List[str],
        group_id: str,
        bootstrap_servers: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        max_poll_records: int = 100
    ):
        """Initialize Kafka consumer.

        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID
            bootstrap_servers: Kafka bootstrap servers
            auto_offset_reset: Where to start reading (earliest, latest)
            enable_auto_commit: Whether to auto-commit offsets
            max_poll_records: Maximum records per poll
        """
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092"
        )
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.max_poll_records = max_poll_records

        self.consumer: Optional[AIOKafkaConsumer] = None
        self._is_started = False
        self._message_handlers: Dict[str, Callable] = {}

        # Statistics
        self.stats = {
            "messages_consumed": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bytes_consumed": 0
        }

    async def start(self):
        """Start the Kafka consumer."""
        if self._is_started:
            logger.warning("Consumer already started")
            return

        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=self.enable_auto_commit,
                max_poll_records=self.max_poll_records,
                value_deserializer=self._deserialize_value,
                key_deserializer=self._deserialize_key
            )

            await self.consumer.start()
            self._is_started = True

            logger.info(
                f"Kafka consumer started: {self.bootstrap_servers} "
                f"(group_id={self.group_id}, topics={self.topics})"
            )

        except KafkaConnectionError as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to start consumer: {str(e)}")
            raise

    async def stop(self):
        """Stop the Kafka consumer."""
        if not self._is_started:
            return

        try:
            if self.consumer:
                await self.consumer.stop()

            self._is_started = False

            logger.info(
                f"Kafka consumer stopped. Stats: "
                f"consumed={self.stats['messages_consumed']}, "
                f"processed={self.stats['messages_processed']}, "
                f"failed={self.stats['messages_failed']}"
            )

        except Exception as e:
            logger.error(f"Error stopping consumer: {str(e)}")

    def register_handler(self, topic: str, handler: Callable):
        """Register a message handler for a specific topic.

        Args:
            topic: Topic name
            handler: Async function to handle messages
        """
        self._message_handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")

    async def consume(self, process_message: Optional[Callable] = None):
        """Start consuming messages.

        Args:
            process_message: Optional message processing function
        """
        if not self._is_started:
            raise RuntimeError("Consumer not started. Call start() first.")

        try:
            async for msg in self.consumer:
                self.stats['messages_consumed'] += 1
                self.stats['bytes_consumed'] += len(msg.value) if msg.value else 0

                try:
                    # Get handler for this topic
                    handler = self._message_handlers.get(msg.topic, process_message)

                    if handler:
                        await handler(msg)
                        self.stats['messages_processed'] += 1
                    else:
                        logger.warning(f"No handler for topic: {msg.topic}")

                except Exception as e:
                    logger.error(
                        f"Error processing message from {msg.topic}: {str(e)}",
                        exc_info=True
                    )
                    self.stats['messages_failed'] += 1

        except Exception as e:
            logger.error(f"Error in consume loop: {str(e)}")
            raise

    async def consume_one(self) -> Optional[ConsumerRecord]:
        """Consume a single message.

        Returns:
            Consumer record or None
        """
        if not self._is_started:
            raise RuntimeError("Consumer not started. Call start() first.")

        try:
            msg = await self.consumer.getone()
            self.stats['messages_consumed'] += 1
            return msg
        except Exception as e:
            logger.error(f"Error consuming message: {str(e)}")
            return None

    def _deserialize_value(self, value: bytes) -> Dict[str, Any]:
        """Deserialize message value from JSON bytes.

        Args:
            value: JSON bytes

        Returns:
            Deserialized value
        """
        if value is None:
            return {}
        return json.loads(value.decode('utf-8'))

    def _deserialize_key(self, key: Optional[bytes]) -> Optional[str]:
        """Deserialize message key from bytes.

        Args:
            key: Key bytes

        Returns:
            Key string or None
        """
        if key is None:
            return None
        return key.decode('utf-8')

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_producer(**kwargs) -> FTEKafkaProducer:
    """Create and start a Kafka producer.

    Args:
        **kwargs: Producer configuration

    Returns:
        Started producer
    """
    producer = FTEKafkaProducer(**kwargs)
    await producer.start()
    return producer


async def create_consumer(topics: List[str], group_id: str, **kwargs) -> FTEKafkaConsumer:
    """Create and start a Kafka consumer.

    Args:
        topics: Topics to subscribe to
        group_id: Consumer group ID
        **kwargs: Consumer configuration

    Returns:
        Started consumer
    """
    consumer = FTEKafkaConsumer(topics, group_id, **kwargs)
    await consumer.start()
    return consumer
