"""Main Customer Success Agent implementation.

This module instantiates and manages the production Customer Success Agent
using the OpenAI Agents SDK.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import asyncpg
from openai import AsyncOpenAI
from openai_agents_sdk import Agent

# Import our tools and prompts
from .tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
    get_db_pool,
    close_db_pool
)
from .prompts import (
    CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    format_system_prompt,
    build_message_history,
    get_greeting,
    get_closing,
    validate_channel
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Agent Configuration
# ============================================================================

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4-turbo-preview")
AGENT_VERSION = "1.0.0"

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ============================================================================
# Agent Instantiation
# ============================================================================

# Create the Customer Success Agent with tools and instructions
customer_success_agent = Agent(
    name="CustomerSuccessAgent",
    model=AGENT_MODEL,
    instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response
    ],
    # Agent configuration
    temperature=0.7,  # Balanced creativity and consistency
    max_tokens=2000,  # Reasonable response length
    # Enable parallel tool calls for efficiency
    parallel_tool_calls=True
)


# ============================================================================
# Agent Wrapper Class
# ============================================================================

class CustomerSuccessAgentRunner:
    """Wrapper class for running the Customer Success Agent.

    This class provides a clean interface for:
    - Processing customer messages
    - Managing conversation context
    - Handling agent responses
    - Tracking metrics
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize the agent runner.

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.agent = customer_success_agent

    async def process_message(
        self,
        message: str,
        customer_id: str,
        conversation_id: str,
        channel: str,
        customer_data: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process a customer message through the agent.

        Args:
            message: Customer's message
            customer_id: Customer ID
            conversation_id: Conversation ID
            channel: Communication channel (email, whatsapp, web_form)
            customer_data: Optional customer data (fetched if not provided)
            message_history: Optional message history (fetched if not provided)

        Returns:
            Agent response with metadata
        """
        start_time = datetime.now()

        try:
            # Validate channel
            if not validate_channel(channel):
                raise ValueError(f"Invalid channel: {channel}")

            # Fetch customer data if not provided
            if not customer_data:
                customer_data = await self._fetch_customer_data(customer_id)

            # Fetch message history if not provided
            if message_history is None:
                message_history = await self._fetch_message_history(conversation_id)

            # Build formatted message history
            formatted_history = build_message_history(message_history)

            # Format system prompt with context
            system_prompt = format_system_prompt(
                customer_id=customer_data['id'],
                customer_name=customer_data['name'],
                customer_email=customer_data['email'],
                customer_tier=customer_data['tier'],
                customer_since=customer_data['created_at'],
                customer_timezone=customer_data.get('timezone', 'UTC'),
                channel=channel,
                conversation_id=conversation_id,
                message_history=formatted_history,
                agent_version=AGENT_VERSION
            )

            # Run the agent
            logger.info(f"Processing message for customer {customer_id} on {channel}")

            response = await self.agent.run(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            )

            # Extract response and metadata
            agent_response = response.messages[-1].content if response.messages else ""
            tools_used = [call.function.name for call in response.tool_calls] if response.tool_calls else []

            # Check if escalated
            escalated = "escalate_to_human" in tools_used

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Log metrics
            await self._log_metrics(
                customer_id=customer_id,
                conversation_id=conversation_id,
                channel=channel,
                tools_used=tools_used,
                escalated=escalated,
                processing_time_ms=int(processing_time)
            )

            return {
                "status": "success",
                "response": agent_response,
                "tools_called": tools_used,
                "escalated": escalated,
                "processing_time_ms": int(processing_time),
                "agent_version": AGENT_VERSION
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)

            # Calculate processing time even on error
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": int(processing_time),
                "agent_version": AGENT_VERSION
            }

    async def _fetch_customer_data(self, customer_id: str) -> Dict[str, Any]:
        """Fetch customer data from database.

        Args:
            customer_id: Customer ID

        Returns:
            Customer data dictionary
        """
        async with self.db_pool.acquire() as conn:
            customer = await conn.fetchrow("""
                SELECT
                    id,
                    name,
                    email,
                    tier,
                    timezone,
                    language,
                    company,
                    created_at
                FROM customers
                WHERE id = $1
            """, customer_id)

            if not customer:
                raise ValueError(f"Customer not found: {customer_id}")

            return dict(customer)

    async def _fetch_message_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch message history for conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to fetch

        Returns:
            List of message dictionaries
        """
        async with self.db_pool.acquire() as conn:
            messages = await conn.fetch("""
                SELECT
                    direction,
                    content,
                    sent_at as timestamp
                FROM messages
                WHERE conversation_id = $1
                ORDER BY sent_at ASC
                LIMIT $2
            """, conversation_id, limit)

            return [
                {
                    "role": "assistant" if msg['direction'] == 'outbound' else "user",
                    "content": msg['content'],
                    "timestamp": msg['timestamp']
                }
                for msg in messages
            ]

    async def _log_metrics(
        self,
        customer_id: str,
        conversation_id: str,
        channel: str,
        tools_used: List[str],
        escalated: bool,
        processing_time_ms: int
    ) -> None:
        """Log agent metrics to database.

        Args:
            customer_id: Customer ID
            conversation_id: Conversation ID
            channel: Communication channel
            tools_used: List of tools called
            escalated: Whether conversation was escalated
            processing_time_ms: Processing time in milliseconds
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Update or insert hourly metrics
                await conn.execute("""
                    INSERT INTO agent_metrics (
                        metric_date,
                        metric_hour,
                        agent_version,
                        channel,
                        total_conversations,
                        total_messages_processed,
                        escalated_count,
                        avg_response_time_ms,
                        tool_usage_counts
                    )
                    VALUES (
                        CURRENT_DATE,
                        EXTRACT(HOUR FROM NOW()),
                        $1,
                        $2,
                        1,
                        1,
                        $3::int,
                        $4,
                        $5::jsonb
                    )
                    ON CONFLICT (metric_date, metric_hour, agent_version, channel)
                    DO UPDATE SET
                        total_conversations = agent_metrics.total_conversations + 1,
                        total_messages_processed = agent_metrics.total_messages_processed + 1,
                        escalated_count = agent_metrics.escalated_count + EXCLUDED.escalated_count,
                        avg_response_time_ms = (
                            agent_metrics.avg_response_time_ms * agent_metrics.total_messages_processed +
                            EXCLUDED.avg_response_time_ms
                        ) / (agent_metrics.total_messages_processed + 1),
                        tool_usage_counts = agent_metrics.tool_usage_counts || EXCLUDED.tool_usage_counts
                """,
                    AGENT_VERSION,
                    channel,
                    1 if escalated else 0,
                    processing_time_ms,
                    self._build_tool_usage_json(tools_used)
                )

        except Exception as e:
            logger.error(f"Failed to log metrics: {str(e)}")

    def _build_tool_usage_json(self, tools_used: List[str]) -> str:
        """Build JSON object for tool usage counts.

        Args:
            tools_used: List of tool names

        Returns:
            JSON string with tool counts
        """
        import json
        counts = {}
        for tool in tools_used:
            counts[tool] = counts.get(tool, 0) + 1
        return json.dumps(counts)


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_agent_runner(db_pool: asyncpg.Pool) -> CustomerSuccessAgentRunner:
    """Create an agent runner instance.

    Args:
        db_pool: Database connection pool

    Returns:
        Configured agent runner
    """
    return CustomerSuccessAgentRunner(db_pool)


async def process_customer_message(
    message: str,
    customer_id: str,
    conversation_id: str,
    channel: str,
    db_pool: asyncpg.Pool,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to process a customer message.

    Args:
        message: Customer's message
        customer_id: Customer ID
        conversation_id: Conversation ID
        channel: Communication channel
        db_pool: Database connection pool
        **kwargs: Additional arguments passed to agent runner

    Returns:
        Agent response
    """
    runner = await create_agent_runner(db_pool)
    return await runner.process_message(
        message=message,
        customer_id=customer_id,
        conversation_id=conversation_id,
        channel=channel,
        **kwargs
    )


# ============================================================================
# Agent Information
# ============================================================================

def get_agent_info() -> Dict[str, Any]:
    """Get information about the agent configuration.

    Returns:
        Agent configuration details
    """
    return {
        "name": customer_success_agent.name,
        "model": customer_success_agent.model,
        "version": AGENT_VERSION,
        "tools": [tool.__name__ for tool in customer_success_agent.tools],
        "capabilities": [
            "Knowledge base search",
            "Ticket creation",
            "Customer history retrieval",
            "Human escalation",
            "Multi-channel communication"
        ]
    }


# ============================================================================
# Lifecycle Management
# ============================================================================

async def initialize_agent(db_pool: asyncpg.Pool) -> None:
    """Initialize agent and dependencies.

    Args:
        db_pool: Database connection pool
    """
    logger.info(f"Initializing Customer Success Agent v{AGENT_VERSION}")
    logger.info(f"Model: {AGENT_MODEL}")
    logger.info(f"Tools: {[tool.__name__ for tool in customer_success_agent.tools]}")


async def shutdown_agent() -> None:
    """Shutdown agent and cleanup resources."""
    logger.info("Shutting down Customer Success Agent")
    await close_db_pool()
