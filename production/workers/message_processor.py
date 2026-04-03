"""Message processing worker.

This module implements the Unified Message Processor that orchestrates
message processing from all channels through Kafka.
"""

import os
import json
import asyncio
import logging
import signal
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from ..agent.customer_success_agent import CustomerSuccessAgentRunner
from ..agent.formatters import format_response_for_channel


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Message Models
# ============================================================================

@dataclass
class IncomingMessage:
    """Schema for incoming messages from Kafka."""
    message_id: str
    customer_identifier: str  # email or phone
    identifier_type: str  # 'email', 'phone', 'whatsapp'
    channel: str  # 'email', 'whatsapp', 'web_form'
    content: str
    subject: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_kafka_message(cls, kafka_msg: Dict[str, Any]) -> 'IncomingMessage':
        """Parse Kafka message into IncomingMessage."""
        return cls(
            message_id=kafka_msg['message_id'],
            customer_identifier=kafka_msg['customer_identifier'],
            identifier_type=kafka_msg['identifier_type'],
            channel=kafka_msg['channel'],
            content=kafka_msg['content'],
            subject=kafka_msg.get('subject'),
            metadata=kafka_msg.get('metadata', {}),
            timestamp=kafka_msg.get('timestamp')
        )


@dataclass
class ProcessingMetrics:
    """Metrics for message processing."""
    message_id: str
    customer_id: str
    conversation_id: str
    channel: str
    processing_time_ms: int
    tools_used: List[str]
    escalated: bool
    success: bool
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class EscalationEvent:
    """Event for escalation to human agents."""
    escalation_id: str
    customer_id: str
    conversation_id: str
    message_id: str
    reason: str
    context: str
    priority: str
    channel: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


# ============================================================================
# Unified Message Processor
# ============================================================================

class UnifiedMessageProcessor:
    """Unified message processor for all channels.

    This worker:
    1. Consumes messages from Kafka
    2. Resolves/creates customers
    3. Manages conversations
    4. Runs the AI agent
    5. Stores messages
    6. Publishes metrics
    7. Handles errors and escalations
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        kafka_bootstrap_servers: Optional[str] = None,
        incoming_topic: str = "customer-messages",
        metrics_topic: str = "agent-metrics",
        escalations_topic: str = "escalations",
        consumer_group: str = "message-processor"
    ):
        """Initialize the message processor.

        Args:
            db_pool: Database connection pool
            kafka_bootstrap_servers: Kafka bootstrap servers
            incoming_topic: Topic for incoming messages
            metrics_topic: Topic for metrics
            escalations_topic: Topic for escalations
            consumer_group: Kafka consumer group ID
        """
        self.db_pool = db_pool
        self.kafka_bootstrap_servers = kafka_bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092"
        )

        # Kafka topics
        self.incoming_topic = incoming_topic
        self.metrics_topic = metrics_topic
        self.escalations_topic = escalations_topic
        self.consumer_group = consumer_group

        # Kafka clients
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None

        # Agent runner
        self.agent_runner = CustomerSuccessAgentRunner(db_pool)

        # Shutdown flag
        self.shutdown_requested = False

        # Statistics
        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "escalations": 0,
            "start_time": datetime.utcnow()
        }

    async def start(self):
        """Start the message processor."""
        logger.info("Starting Unified Message Processor")

        # Initialize Kafka consumer
        self.consumer = AIOKafkaConsumer(
            self.incoming_topic,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            max_poll_records=10  # Process in small batches
        )

        # Initialize Kafka producer
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        # Start Kafka clients
        await self.consumer.start()
        await self.producer.start()

        logger.info(f"Listening on topic: {self.incoming_topic}")
        logger.info(f"Consumer group: {self.consumer_group}")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start processing loop
        await self._process_messages()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown_requested = True

    async def _process_messages(self):
        """Main message processing loop."""
        try:
            async for msg in self.consumer:
                if self.shutdown_requested:
                    logger.info("Shutdown requested, stopping message processing")
                    break

                try:
                    # Parse incoming message
                    incoming_msg = IncomingMessage.from_kafka_message(msg.value)

                    logger.info(
                        f"Processing message {incoming_msg.message_id} "
                        f"from {incoming_msg.channel} channel"
                    )

                    # Process the message
                    await self._process_single_message(incoming_msg)

                    self.stats["messages_processed"] += 1

                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    self.stats["messages_failed"] += 1

                    # Publish error to escalations topic
                    await self._handle_processing_error(msg.value, str(e))

        except Exception as e:
            logger.error(f"Fatal error in processing loop: {str(e)}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    async def _process_single_message(self, incoming_msg: IncomingMessage):
        """Process a single incoming message.

        Args:
            incoming_msg: Incoming message to process
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Resolve or create customer
            customer_id = await self._resolve_customer(
                identifier=incoming_msg.customer_identifier,
                identifier_type=incoming_msg.identifier_type,
                channel=incoming_msg.channel
            )

            logger.info(f"Resolved customer: {customer_id}")

            # Step 2: Get or create active conversation
            conversation_id = await self._get_or_create_conversation(
                customer_id=customer_id,
                channel=incoming_msg.channel,
                subject=incoming_msg.subject
            )

            logger.info(f"Conversation: {conversation_id}")

            # Step 3: Store inbound message
            inbound_message_id = await self._store_inbound_message(
                conversation_id=conversation_id,
                customer_id=customer_id,
                channel=incoming_msg.channel,
                content=incoming_msg.content,
                metadata=incoming_msg.metadata
            )

            logger.info(f"Stored inbound message: {inbound_message_id}")

            # Step 4: Run the customer success agent
            agent_response = await self.agent_runner.process_message(
                message=incoming_msg.content,
                customer_id=customer_id,
                conversation_id=conversation_id,
                channel=incoming_msg.channel
            )

            logger.info(f"Agent response: {agent_response['status']}")

            # Step 5: Store outbound message
            if agent_response['status'] == 'success':
                outbound_message_id = await self._store_outbound_message(
                    conversation_id=conversation_id,
                    customer_id=customer_id,
                    channel=incoming_msg.channel,
                    content=agent_response['response'],
                    tools_used=agent_response['tools_called'],
                    agent_version=agent_response['agent_version']
                )

                logger.info(f"Stored outbound message: {outbound_message_id}")

                # Step 6: Send response via appropriate channel
                await self._send_channel_response(
                    customer_id=customer_id,
                    channel=incoming_msg.channel,
                    response=agent_response['response'],
                    conversation_id=conversation_id
                )

            # Step 7: Publish metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            metrics = ProcessingMetrics(
                message_id=incoming_msg.message_id,
                customer_id=customer_id,
                conversation_id=conversation_id,
                channel=incoming_msg.channel,
                processing_time_ms=int(processing_time),
                tools_used=agent_response.get('tools_called', []),
                escalated=agent_response.get('escalated', False),
                success=agent_response['status'] == 'success',
                error=agent_response.get('error')
            )

            await self._publish_metrics(metrics)

            # Step 8: Handle escalations if needed
            if agent_response.get('escalated'):
                await self._handle_escalation(
                    customer_id=customer_id,
                    conversation_id=conversation_id,
                    message_id=incoming_msg.message_id,
                    channel=incoming_msg.channel,
                    context=incoming_msg.content
                )
                self.stats["escalations"] += 1

            logger.info(
                f"Successfully processed message {incoming_msg.message_id} "
                f"in {int(processing_time)}ms"
            )

        except Exception as e:
            logger.error(f"Error in message processing pipeline: {str(e)}", exc_info=True)
            raise

    async def _resolve_customer(
        self,
        identifier: str,
        identifier_type: str,
        channel: str
    ) -> str:
        """Resolve or create customer based on identifier.

        Args:
            identifier: Customer identifier (email or phone)
            identifier_type: Type of identifier
            channel: Communication channel

        Returns:
            Customer ID
        """
        async with self.db_pool.acquire() as conn:
            # Try to find existing customer
            if identifier_type == 'email':
                customer = await conn.fetchrow("""
                    SELECT id FROM customers WHERE email = $1
                """, identifier)
            else:
                customer = await conn.fetchrow("""
                    SELECT customer_id as id
                    FROM customer_identifiers
                    WHERE identifier_type = $1 AND identifier_value = $2
                """, identifier_type, identifier)

            if customer:
                return customer['id']

            # Create new customer
            if identifier_type == 'email':
                new_customer = await conn.fetchrow("""
                    INSERT INTO customers (email, name, tier)
                    VALUES ($1, $2, 'free')
                    RETURNING id
                """, identifier, identifier.split('@')[0])
                customer_id = new_customer['id']
            else:
                new_customer = await conn.fetchrow("""
                    INSERT INTO customers (name, tier)
                    VALUES ($1, 'free')
                    RETURNING id
                """, identifier)
                customer_id = new_customer['id']

                # Add identifier
                await conn.execute("""
                    INSERT INTO customer_identifiers (
                        customer_id,
                        identifier_type,
                        identifier_value,
                        is_primary
                    )
                    VALUES ($1, $2, $3, true)
                """, customer_id, identifier_type, identifier)

            logger.info(f"Created new customer: {customer_id}")
            return customer_id

    async def _get_or_create_conversation(
        self,
        customer_id: str,
        channel: str,
        subject: Optional[str]
    ) -> str:
        """Get or create active conversation.

        Args:
            customer_id: Customer ID
            channel: Communication channel
            subject: Optional conversation subject

        Returns:
            Conversation ID
        """
        async with self.db_pool.acquire() as conn:
            # Check for active conversation
            existing = await conn.fetchrow("""
                SELECT id FROM conversations
                WHERE customer_id = $1
                AND channel = $2
                AND is_active = true
                ORDER BY last_message_at DESC
                LIMIT 1
            """, customer_id, channel)

            if existing:
                return existing['id']

            # Create new conversation
            new_conv = await conn.fetchrow("""
                INSERT INTO conversations (
                    customer_id,
                    channel,
                    subject,
                    is_active
                )
                VALUES ($1, $2, $3, true)
                RETURNING id
            """, customer_id, channel, subject or f"{channel.title()} Conversation")

            logger.info(f"Created new conversation: {new_conv['id']}")
            return new_conv['id']

    async def _store_inbound_message(
        self,
        conversation_id: str,
        customer_id: str,
        channel: str,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Store inbound message in database.

        Args:
            conversation_id: Conversation ID
            customer_id: Customer ID
            channel: Communication channel
            content: Message content
            metadata: Additional metadata

        Returns:
            Message ID
        """
        async with self.db_pool.acquire() as conn:
            msg = await conn.fetchrow("""
                INSERT INTO messages (
                    conversation_id,
                    customer_id,
                    direction,
                    channel,
                    content,
                    metadata,
                    is_processed
                )
                VALUES ($1, $2, 'inbound', $3, $4, $5, true)
                RETURNING id
            """,
                conversation_id,
                customer_id,
                channel,
                content,
                json.dumps(metadata or {})
            )

            # Update conversation last_message_at
            await conn.execute("""
                UPDATE conversations
                SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)

            return msg['id']

    async def _store_outbound_message(
        self,
        conversation_id: str,
        customer_id: str,
        channel: str,
        content: str,
        tools_used: List[str],
        agent_version: str
    ) -> str:
        """Store outbound message in database.

        Args:
            conversation_id: Conversation ID
            customer_id: Customer ID
            channel: Communication channel
            content: Message content
            tools_used: List of tools used by agent
            agent_version: Agent version

        Returns:
            Message ID
        """
        async with self.db_pool.acquire() as conn:
            msg = await conn.fetchrow("""
                INSERT INTO messages (
                    conversation_id,
                    customer_id,
                    direction,
                    channel,
                    content,
                    agent_version,
                    tools_used,
                    sent_at
                )
                VALUES ($1, $2, 'outbound', $3, $4, $5, $6, NOW())
                RETURNING id
            """,
                conversation_id,
                customer_id,
                channel,
                content,
                agent_version,
                tools_used
            )

            # Update conversation last_message_at
            await conn.execute("""
                UPDATE conversations
                SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)

            return msg['id']

    async def _send_channel_response(
        self,
        customer_id: str,
        channel: str,
        response: str,
        conversation_id: str
    ):
        """Send response via appropriate channel.

        Args:
            customer_id: Customer ID
            channel: Communication channel
            response: Response message
            conversation_id: Conversation ID
        """
        # Format response for channel
        formatted_response = format_response_for_channel(response, channel)

        # Queue message for delivery
        async with self.db_pool.acquire() as conn:
            # Get the message ID we just created
            msg = await conn.fetchrow("""
                SELECT id FROM messages
                WHERE conversation_id = $1
                AND direction = 'outbound'
                ORDER BY sent_at DESC
                LIMIT 1
            """, conversation_id)

            if msg:
                await conn.execute("""
                    INSERT INTO message_queue (
                        message_id,
                        customer_id,
                        channel,
                        status
                    )
                    VALUES ($1, $2, $3, 'queued')
                """, msg['id'], customer_id, channel)

    async def _publish_metrics(self, metrics: ProcessingMetrics):
        """Publish processing metrics to Kafka.

        Args:
            metrics: Processing metrics
        """
        try:
            await self.producer.send_and_wait(
                self.metrics_topic,
                value=asdict(metrics)
            )
        except KafkaError as e:
            logger.error(f"Failed to publish metrics: {str(e)}")

    async def _handle_escalation(
        self,
        customer_id: str,
        conversation_id: str,
        message_id: str,
        channel: str,
        context: str
    ):
        """Handle escalation to human agents.

        Args:
            customer_id: Customer ID
            conversation_id: Conversation ID
            message_id: Message ID
            channel: Communication channel
            context: Conversation context
        """
        async with self.db_pool.acquire() as conn:
            # Create escalation record
            escalation = await conn.fetchrow("""
                INSERT INTO escalations (
                    customer_id,
                    conversation_id,
                    reason,
                    context,
                    priority,
                    status
                )
                VALUES ($1, $2, 'agent_escalation', $3, 'medium', 'pending')
                RETURNING id
            """, customer_id, conversation_id, context)

            escalation_id = escalation['id']

            # Mark conversation as escalated
            await conn.execute("""
                UPDATE conversations
                SET is_escalated = true
                WHERE id = $1
            """, conversation_id)

        # Publish escalation event to Kafka
        escalation_event = EscalationEvent(
            escalation_id=escalation_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            message_id=message_id,
            reason="agent_escalation",
            context=context,
            priority="medium",
            channel=channel
        )

        try:
            await self.producer.send_and_wait(
                self.escalations_topic,
                value=asdict(escalation_event)
            )
            logger.info(f"Published escalation event: {escalation_id}")
        except KafkaError as e:
            logger.error(f"Failed to publish escalation: {str(e)}")

    async def _handle_processing_error(
        self,
        message_data: Dict[str, Any],
        error: str
    ):
        """Handle processing errors by publishing to escalations topic.

        Args:
            message_data: Original message data
            error: Error message
        """
        error_event = {
            "type": "processing_error",
            "message_data": message_data,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            await self.producer.send_and_wait(
                self.escalations_topic,
                value=error_event
            )
            logger.info("Published processing error to escalations topic")
        except KafkaError as e:
            logger.error(f"Failed to publish error event: {str(e)}")

    async def shutdown(self):
        """Gracefully shutdown the processor."""
        logger.info("Shutting down Unified Message Processor")

        # Log final statistics
        uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        logger.info(f"Statistics:")
        logger.info(f"  Uptime: {uptime:.2f}s")
        logger.info(f"  Messages processed: {self.stats['messages_processed']}")
        logger.info(f"  Messages failed: {self.stats['messages_failed']}")
        logger.info(f"  Escalations: {self.stats['escalations']}")

        # Stop Kafka clients
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        logger.info("Shutdown complete")


# ============================================================================
# Entry Point
# ============================================================================

async def main():
    """Main entry point for the message processor."""
    # Initialize database pool
    db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "customer_success"),
        min_size=5,
        max_size=20
    )

    # Create and start processor
    processor = UnifiedMessageProcessor(db_pool)

    try:
        await processor.start()
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
