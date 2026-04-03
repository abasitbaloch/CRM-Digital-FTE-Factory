"""Agent tools and utilities.

This module provides the core tools for the Customer Success Agent,
converted from MCP server tools to OpenAI Agents SDK @function_tool format.
"""

import os
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from openai_agents_sdk import function_tool


# Database connection pool (singleton pattern)
_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create the database connection pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "customer_success"),
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    return _db_pool


# ============================================================================
# Pydantic Input Schemas
# ============================================================================

class SearchKnowledgeBaseInput(BaseModel):
    """Input schema for searching the knowledge base."""
    query: str = Field(
        ...,
        description="The search query to find relevant documentation, FAQs, or help articles"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results to return (1-20)"
    )


class CreateTicketInput(BaseModel):
    """Input schema for creating a support ticket."""
    customer_id: str = Field(
        ...,
        description="Unique identifier for the customer"
    )
    subject: str = Field(
        ...,
        description="Brief subject line for the ticket"
    )
    description: str = Field(
        ...,
        description="Detailed description of the issue or request"
    )
    priority: str = Field(
        default="medium",
        description="Ticket priority: low, medium, high, or urgent"
    )
    category: Optional[str] = Field(
        default=None,
        description="Ticket category (e.g., billing, technical, feature_request)"
    )


class GetCustomerHistoryInput(BaseModel):
    """Input schema for retrieving customer history."""
    customer_id: str = Field(
        ...,
        description="Unique identifier for the customer"
    )
    include_tickets: bool = Field(
        default=True,
        description="Whether to include past support tickets"
    )
    include_interactions: bool = Field(
        default=True,
        description="Whether to include past interactions/conversations"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of historical records to return"
    )


class EscalateToHumanInput(BaseModel):
    """Input schema for escalating to a human agent."""
    customer_id: str = Field(
        ...,
        description="Unique identifier for the customer"
    )
    reason: str = Field(
        ...,
        description="Reason for escalation (e.g., complex issue, customer request, sensitive matter)"
    )
    context: str = Field(
        ...,
        description="Full context of the conversation and issue for the human agent"
    )
    priority: str = Field(
        default="medium",
        description="Escalation priority: low, medium, high, or urgent"
    )


class SendResponseInput(BaseModel):
    """Input schema for sending a response to the customer."""
    customer_id: str = Field(
        ...,
        description="Unique identifier for the customer"
    )
    message: str = Field(
        ...,
        description="The message to send to the customer"
    )
    channel: str = Field(
        ...,
        description="Communication channel: email, whatsapp, or web_form"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for the message (e.g., attachments, formatting)"
    )


# ============================================================================
# Tool Functions
# ============================================================================

@function_tool
async def search_knowledge_base(query: str, limit: int = 5) -> str:
    """Search the knowledge base for relevant documentation, FAQs, and help articles.

    Use this tool when you need to find information to answer customer questions,
    troubleshoot issues, or provide guidance. The knowledge base contains:
    - Product documentation
    - Common troubleshooting guides
    - FAQs
    - Best practices
    - Known issues and workarounds

    Args:
        query: The search query to find relevant content
        limit: Maximum number of results to return (1-20, default 5)

    Returns:
        A formatted string containing the search results with titles, content snippets,
        and relevance scores. Returns an error message if the search fails.
    """
    try:
        # Validate input
        input_data = SearchKnowledgeBaseInput(query=query, limit=limit)

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Use PostgreSQL full-text search with ranking
            results = await conn.fetch("""
                SELECT
                    id,
                    title,
                    content,
                    category,
                    ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
                FROM knowledge_base
                WHERE search_vector @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC, updated_at DESC
                LIMIT $2
            """, input_data.query, input_data.limit)

            if not results:
                return f"No results found for query: '{input_data.query}'. Try rephrasing or using different keywords."

            # Format results
            formatted_results = [f"Found {len(results)} relevant articles:\n"]
            for idx, row in enumerate(results, 1):
                formatted_results.append(
                    f"\n{idx}. {row['title']} (Category: {row['category']})\n"
                    f"   Relevance: {row['rank']:.2f}\n"
                    f"   {row['content'][:300]}{'...' if len(row['content']) > 300 else ''}\n"
                )

            return "".join(formatted_results)

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}. Please try again or escalate to a human agent if the issue persists."


@function_tool
async def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    category: Optional[str] = None
) -> str:
    """Create a support ticket for tracking customer issues or requests.

    Use this tool when:
    - The customer reports a bug or technical issue
    - The customer requests a new feature
    - The issue requires follow-up or investigation
    - You need to track a customer request that can't be resolved immediately

    Args:
        customer_id: Unique identifier for the customer
        subject: Brief subject line for the ticket
        description: Detailed description of the issue or request
        priority: Ticket priority (low, medium, high, urgent)
        category: Optional category (billing, technical, feature_request, etc.)

    Returns:
        Confirmation message with the ticket ID and details, or an error message if creation fails.
    """
    try:
        # Validate input
        input_data = CreateTicketInput(
            customer_id=customer_id,
            subject=subject,
            description=description,
            priority=priority,
            category=category
        )

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Insert ticket and return the generated ID
            ticket = await conn.fetchrow("""
                INSERT INTO tickets (
                    customer_id,
                    subject,
                    description,
                    priority,
                    category,
                    status,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, 'open', NOW(), NOW())
                RETURNING id, created_at
            """,
                input_data.customer_id,
                input_data.subject,
                input_data.description,
                input_data.priority,
                input_data.category
            )

            ticket_id = ticket['id']
            created_at = ticket['created_at'].isoformat()

            return (
                f"✓ Ticket created successfully!\n"
                f"Ticket ID: {ticket_id}\n"
                f"Subject: {input_data.subject}\n"
                f"Priority: {input_data.priority}\n"
                f"Status: Open\n"
                f"Created: {created_at}\n\n"
                f"The ticket has been logged and will be tracked for resolution."
            )

    except Exception as e:
        return f"Error creating ticket: {str(e)}. The issue has been noted but the ticket could not be created. Please escalate to a human agent."


@function_tool
async def get_customer_history(
    customer_id: str,
    include_tickets: bool = True,
    include_interactions: bool = True,
    limit: int = 10
) -> str:
    """Retrieve the customer's history including past tickets and interactions.

    Use this tool to:
    - Understand the customer's past issues and resolutions
    - Check for recurring problems
    - Provide personalized support based on history
    - Reference previous conversations or tickets

    Args:
        customer_id: Unique identifier for the customer
        include_tickets: Whether to include past support tickets
        include_interactions: Whether to include past interactions/conversations
        limit: Maximum number of historical records to return (1-50)

    Returns:
        A formatted summary of the customer's history, or an error message if retrieval fails.
    """
    try:
        # Validate input
        input_data = GetCustomerHistoryInput(
            customer_id=customer_id,
            include_tickets=include_tickets,
            include_interactions=include_interactions,
            limit=limit
        )

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            history_parts = [f"Customer History for ID: {input_data.customer_id}\n"]

            # Get customer info
            customer = await conn.fetchrow("""
                SELECT name, email, created_at, tier
                FROM customers
                WHERE id = $1
            """, input_data.customer_id)

            if not customer:
                return f"No customer found with ID: {input_data.customer_id}"

            history_parts.append(
                f"Name: {customer['name']}\n"
                f"Email: {customer['email']}\n"
                f"Tier: {customer['tier']}\n"
                f"Customer since: {customer['created_at'].strftime('%Y-%m-%d')}\n"
            )

            # Get tickets if requested
            if input_data.include_tickets:
                tickets = await conn.fetch("""
                    SELECT id, subject, status, priority, created_at, resolved_at
                    FROM tickets
                    WHERE customer_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, input_data.customer_id, input_data.limit)

                if tickets:
                    history_parts.append(f"\n📋 Recent Tickets ({len(tickets)}):\n")
                    for ticket in tickets:
                        status_emoji = "✓" if ticket['status'] == 'resolved' else "○"
                        history_parts.append(
                            f"  {status_emoji} #{ticket['id']}: {ticket['subject']}\n"
                            f"     Status: {ticket['status']} | Priority: {ticket['priority']}\n"
                            f"     Created: {ticket['created_at'].strftime('%Y-%m-%d')}\n"
                        )

            # Get interactions if requested
            if input_data.include_interactions:
                interactions = await conn.fetch("""
                    SELECT channel, summary, created_at
                    FROM interactions
                    WHERE customer_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, input_data.customer_id, input_data.limit)

                if interactions:
                    history_parts.append(f"\n💬 Recent Interactions ({len(interactions)}):\n")
                    for interaction in interactions:
                        history_parts.append(
                            f"  • {interaction['channel']}: {interaction['summary']}\n"
                            f"    {interaction['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                        )

            return "".join(history_parts)

    except Exception as e:
        return f"Error retrieving customer history: {str(e)}. Proceeding without historical context."


@function_tool
async def escalate_to_human(
    customer_id: str,
    reason: str,
    context: str,
    priority: str = "medium"
) -> str:
    """Escalate the conversation to a human agent.

    Use this tool when:
    - The customer explicitly requests to speak with a human
    - The issue is too complex for automated handling
    - The customer is frustrated or upset
    - Sensitive matters require human judgment (refunds, account issues, etc.)
    - You've attempted to help but couldn't resolve the issue

    Args:
        customer_id: Unique identifier for the customer
        reason: Reason for escalation
        context: Full context of the conversation and issue for the human agent
        priority: Escalation priority (low, medium, high, urgent)

    Returns:
        Confirmation message that the escalation was successful, or an error message.
    """
    try:
        # Validate input
        input_data = EscalateToHumanInput(
            customer_id=customer_id,
            reason=reason,
            context=context,
            priority=priority
        )

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Create escalation record
            escalation = await conn.fetchrow("""
                INSERT INTO escalations (
                    customer_id,
                    reason,
                    context,
                    priority,
                    status,
                    created_at
                )
                VALUES ($1, $2, $3, $4, 'pending', NOW())
                RETURNING id, created_at
            """,
                input_data.customer_id,
                input_data.reason,
                input_data.context,
                input_data.priority
            )

            escalation_id = escalation['id']

            # Notify human agents (this would integrate with your notification system)
            # For now, we'll just log it
            await conn.execute("""
                INSERT INTO notifications (
                    type,
                    target,
                    message,
                    priority,
                    created_at
                )
                VALUES ('escalation', 'human_agents', $1, $2, NOW())
            """,
                f"New escalation #{escalation_id} for customer {input_data.customer_id}: {input_data.reason}",
                input_data.priority
            )

            return (
                f"✓ Successfully escalated to human agent\n"
                f"Escalation ID: {escalation_id}\n"
                f"Priority: {input_data.priority}\n\n"
                f"A human agent will be with you shortly. "
                f"Your conversation history and context have been shared with them."
            )

    except Exception as e:
        return f"Error escalating to human agent: {str(e)}. Please try contacting support directly or try again later."


@function_tool
async def send_response(
    customer_id: str,
    message: str,
    channel: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Send a response message to the customer through the specified channel.

    Use this tool to send your final response to the customer after:
    - Gathering necessary information
    - Searching the knowledge base
    - Formulating a helpful answer

    Args:
        customer_id: Unique identifier for the customer
        message: The message to send to the customer
        channel: Communication channel (email, whatsapp, web_form)
        metadata: Optional metadata (attachments, formatting, etc.)

    Returns:
        Confirmation that the message was sent, or an error message.
    """
    try:
        # Validate input
        input_data = SendResponseInput(
            customer_id=customer_id,
            message=message,
            channel=channel,
            metadata=metadata
        )

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Log the outgoing message
            message_record = await conn.fetchrow("""
                INSERT INTO messages (
                    customer_id,
                    direction,
                    channel,
                    content,
                    metadata,
                    sent_at
                )
                VALUES ($1, 'outbound', $2, $3, $4, NOW())
                RETURNING id, sent_at
            """,
                input_data.customer_id,
                input_data.channel,
                input_data.message,
                input_data.metadata
            )

            message_id = message_record['id']

            # Queue the message for delivery (this would integrate with your channel handlers)
            await conn.execute("""
                INSERT INTO message_queue (
                    message_id,
                    customer_id,
                    channel,
                    status,
                    created_at
                )
                VALUES ($1, $2, $3, 'queued', NOW())
            """,
                message_id,
                input_data.customer_id,
                input_data.channel
            )

            return (
                f"✓ Message sent successfully via {input_data.channel}\n"
                f"Message ID: {message_id}\n"
                f"The customer will receive your response shortly."
            )

    except Exception as e:
        return f"Error sending message: {str(e)}. The message could not be delivered. Please try again or escalate to a human agent."


# ============================================================================
# Utility Functions
# ============================================================================

async def close_db_pool():
    """Close the database connection pool."""
    global _db_pool
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None
