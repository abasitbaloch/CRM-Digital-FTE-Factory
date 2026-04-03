"""FastAPI application entry point.

This module provides the main API service for the Customer Success platform,
including webhooks for all channels and management endpoints.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Request, Header, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from ..channels.web_form_handler import router as web_form_router
from ..channels.gmail_handler import GmailHandler
from ..channels.whatsapp_handler import WhatsAppHandler
from ..kafka_client import FTEKafkaProducer, TOPICS


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Customer Success API")

    # Initialize database pool
    app.state.db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "customer_success"),
        min_size=5,
        max_size=20
    )
    logger.info("Database pool initialized")

    # Initialize Kafka producer
    app.state.kafka_producer = FTEKafkaProducer(client_id="api-service")
    await app.state.kafka_producer.start()
    logger.info("Kafka producer initialized")

    # Initialize channel handlers
    app.state.gmail_handler = GmailHandler(app.state.db_pool)
    app.state.whatsapp_handler = WhatsAppHandler(app.state.db_pool)
    logger.info("Channel handlers initialized")

    yield

    # Shutdown
    logger.info("Shutting down Customer Success API")

    # Close Kafka producer
    await app.state.kafka_producer.stop()

    # Close database pool
    await app.state.db_pool.close()

    logger.info("Shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Customer Success API",
    description="API service for AI-powered customer success platform",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# CORS Configuration
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(web_form_router)


# ============================================================================
# Dependencies
# ============================================================================

async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Get database pool from app state."""
    return request.app.state.db_pool


async def get_kafka_producer(request: Request) -> FTEKafkaProducer:
    """Get Kafka producer from app state."""
    return request.app.state.kafka_producer


# ============================================================================
# Pydantic Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    database: str
    kafka: str


class ConversationMessage(BaseModel):
    """Conversation message model."""
    id: str
    direction: str
    content: str
    channel: str
    sent_at: datetime
    agent_version: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """Conversation history response."""
    conversation_id: str
    customer_id: str
    customer_name: str
    channel: str
    subject: Optional[str]
    is_active: bool
    is_escalated: bool
    started_at: datetime
    last_message_at: datetime
    messages: List[ConversationMessage]


class CustomerLookupResponse(BaseModel):
    """Customer lookup response."""
    customer_id: str
    name: str
    email: Optional[str]
    tier: str
    created_at: datetime
    active_conversations: int
    total_tickets: int
    open_tickets: int


class ChannelMetrics(BaseModel):
    """Channel metrics model."""
    channel: str
    total_messages: int
    avg_response_time_ms: int
    escalation_rate: float
    resolution_rate: float


class ChannelMetricsResponse(BaseModel):
    """Channel metrics response."""
    period: str
    metrics: List[ChannelMetrics]


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    kafka_producer: FTEKafkaProducer = Depends(get_kafka_producer)
) -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status of all services
    """
    # Check database
    db_status = "healthy"
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"

    # Check Kafka
    kafka_status = "healthy" if kafka_producer._is_started else "unhealthy"

    # Overall status
    overall_status = "healthy" if db_status == "healthy" and kafka_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        service="customer_success_api",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        database=db_status,
        kafka=kafka_status
    )


# ============================================================================
# Gmail Webhook Endpoint
# ============================================================================

@app.post("/webhooks/gmail", tags=["webhooks"])
async def gmail_webhook(
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    kafka_producer: FTEKafkaProducer = Depends(get_kafka_producer)
) -> Dict[str, str]:
    """Gmail Pub/Sub webhook endpoint.

    Processes Gmail push notifications and publishes messages to Kafka.

    Args:
        request: FastAPI request
        db_pool: Database pool
        kafka_producer: Kafka producer

    Returns:
        Acknowledgment response
    """
    try:
        # Parse Pub/Sub notification
        body = await request.json()

        logger.info(f"Received Gmail webhook: {body}")

        # Get Gmail handler
        gmail_handler: GmailHandler = request.app.state.gmail_handler

        # Process notification
        result = await gmail_handler.process_pubsub_notification(body)

        if result['status'] == 'success':
            # Publish to Kafka for processing
            # Note: The Gmail handler already stores messages in DB,
            # but we can publish events for other consumers
            await kafka_producer.send(
                TOPICS['EMAIL_EVENTS'],
                {
                    'event_type': 'messages_received',
                    'count': result.get('messages_processed', 0),
                    'history_id': result.get('history_id')
                }
            )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Gmail webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


# ============================================================================
# WhatsApp Webhook Endpoints
# ============================================================================

@app.post("/webhooks/whatsapp", tags=["webhooks"])
async def whatsapp_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    kafka_producer: FTEKafkaProducer = Depends(get_kafka_producer)
) -> Dict[str, str]:
    """WhatsApp incoming message webhook.

    Processes incoming WhatsApp messages from Twilio and publishes to Kafka.

    Args:
        request: FastAPI request
        x_twilio_signature: Twilio signature header
        db_pool: Database pool
        kafka_producer: Kafka producer

    Returns:
        Acknowledgment response
    """
    try:
        # Get form data
        form_data = await request.form()
        webhook_data = dict(form_data)

        logger.info(f"Received WhatsApp message: {webhook_data.get('From')}")

        # Get WhatsApp handler
        whatsapp_handler: WhatsAppHandler = request.app.state.whatsapp_handler

        # Validate webhook signature
        url = str(request.url)
        validated = whatsapp_handler.validate_webhook(
            url=url,
            params=webhook_data,
            signature=x_twilio_signature or ""
        )

        if not validated:
            logger.warning("Invalid Twilio signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )

        # Process incoming message
        result = await whatsapp_handler.process_incoming_message(
            webhook_data=webhook_data,
            validated=True
        )

        if result['status'] == 'success':
            # Publish to Kafka for agent processing
            await kafka_producer.send(
                TOPICS['CUSTOMER_MESSAGES'],
                {
                    'message_id': result['message_id'],
                    'customer_identifier': webhook_data.get('From', '').replace('whatsapp:', ''),
                    'identifier_type': 'whatsapp',
                    'channel': 'whatsapp',
                    'content': webhook_data.get('Body', ''),
                    'metadata': {
                        'conversation_id': result['conversation_id'],
                        'has_media': result.get('has_media', False)
                    }
                }
            )

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@app.post("/webhooks/whatsapp/status", tags=["webhooks"])
async def whatsapp_status_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None)
) -> Dict[str, str]:
    """WhatsApp message status callback webhook.

    Processes delivery status updates from Twilio.

    Args:
        request: FastAPI request
        x_twilio_signature: Twilio signature header

    Returns:
        Acknowledgment response
    """
    try:
        # Get form data
        form_data = await request.form()
        webhook_data = dict(form_data)

        logger.info(f"Received WhatsApp status: {webhook_data.get('MessageStatus')}")

        # Get WhatsApp handler
        whatsapp_handler: WhatsAppHandler = request.app.state.whatsapp_handler

        # Validate webhook signature
        url = str(request.url)
        validated = whatsapp_handler.validate_webhook(
            url=url,
            params=webhook_data,
            signature=x_twilio_signature or ""
        )

        if not validated:
            logger.warning("Invalid Twilio signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )

        # Process status callback
        await whatsapp_handler.process_status_callback(webhook_data)

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing WhatsApp status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process status: {str(e)}"
        )


# ============================================================================
# Conversation History Endpoint
# ============================================================================

@app.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
    tags=["conversations"]
)
async def get_conversation_history(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> ConversationHistoryResponse:
    """Get conversation history with messages.

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to return
        db_pool: Database pool

    Returns:
        Conversation history with messages

    Raises:
        HTTPException: If conversation not found
    """
    try:
        async with db_pool.acquire() as conn:
            # Get conversation details
            conversation = await conn.fetchrow("""
                SELECT
                    c.id,
                    c.customer_id,
                    c.channel,
                    c.subject,
                    c.is_active,
                    c.is_escalated,
                    c.started_at,
                    c.last_message_at,
                    cu.name as customer_name
                FROM conversations c
                JOIN customers cu ON c.customer_id = cu.id
                WHERE c.id = $1
            """, conversation_id)

            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found"
                )

            # Get messages
            messages = await conn.fetch("""
                SELECT
                    id,
                    direction,
                    content,
                    channel,
                    sent_at,
                    agent_version
                FROM messages
                WHERE conversation_id = $1
                ORDER BY sent_at ASC
                LIMIT $2
            """, conversation_id, limit)

            return ConversationHistoryResponse(
                conversation_id=conversation['id'],
                customer_id=conversation['customer_id'],
                customer_name=conversation['customer_name'],
                channel=conversation['channel'],
                subject=conversation['subject'],
                is_active=conversation['is_active'],
                is_escalated=conversation['is_escalated'],
                started_at=conversation['started_at'],
                last_message_at=conversation['last_message_at'],
                messages=[
                    ConversationMessage(
                        id=msg['id'],
                        direction=msg['direction'],
                        content=msg['content'],
                        channel=msg['channel'],
                        sent_at=msg['sent_at'],
                        agent_version=msg['agent_version']
                    )
                    for msg in messages
                ]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation: {str(e)}"
        )


# ============================================================================
# Customer Lookup Endpoint
# ============================================================================

@app.get(
    "/customers/lookup",
    response_model=CustomerLookupResponse,
    tags=["customers"]
)
async def lookup_customer(
    email: Optional[EmailStr] = Query(None),
    customer_id: Optional[str] = Query(None),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> CustomerLookupResponse:
    """Look up customer by email or ID.

    Args:
        email: Customer email
        customer_id: Customer ID
        db_pool: Database pool

    Returns:
        Customer information

    Raises:
        HTTPException: If customer not found or invalid parameters
    """
    if not email and not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or customer_id must be provided"
        )

    try:
        async with db_pool.acquire() as conn:
            # Look up customer
            if customer_id:
                customer = await conn.fetchrow("""
                    SELECT id, name, email, tier, created_at
                    FROM customers
                    WHERE id = $1
                """, customer_id)
            else:
                customer = await conn.fetchrow("""
                    SELECT id, name, email, tier, created_at
                    FROM customers
                    WHERE email = $1
                """, email)

            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            # Get conversation count
            active_conversations = await conn.fetchval("""
                SELECT COUNT(*)
                FROM conversations
                WHERE customer_id = $1 AND is_active = true
            """, customer['id'])

            # Get ticket counts
            total_tickets = await conn.fetchval("""
                SELECT COUNT(*)
                FROM tickets
                WHERE customer_id = $1
            """, customer['id'])

            open_tickets = await conn.fetchval("""
                SELECT COUNT(*)
                FROM tickets
                WHERE customer_id = $1
                AND status IN ('open', 'in_progress', 'waiting_customer')
            """, customer['id'])

            return CustomerLookupResponse(
                customer_id=customer['id'],
                name=customer['name'],
                email=customer['email'],
                tier=customer['tier'],
                created_at=customer['created_at'],
                active_conversations=active_conversations,
                total_tickets=total_tickets,
                open_tickets=open_tickets
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up customer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lookup customer: {str(e)}"
        )


# ============================================================================
# Channel Metrics Endpoint
# ============================================================================

@app.get(
    "/metrics/channels",
    response_model=ChannelMetricsResponse,
    tags=["metrics"]
)
async def get_channel_metrics(
    period: str = Query(default="today", regex="^(today|week|month)$"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> ChannelMetricsResponse:
    """Get metrics by channel.

    Args:
        period: Time period (today, week, month)
        db_pool: Database pool

    Returns:
        Channel metrics

    Raises:
        HTTPException: If query fails
    """
    try:
        # Determine date filter
        date_filters = {
            "today": "metric_date = CURRENT_DATE",
            "week": "metric_date >= CURRENT_DATE - INTERVAL '7 days'",
            "month": "metric_date >= CURRENT_DATE - INTERVAL '30 days'"
        }
        date_filter = date_filters[period]

        async with db_pool.acquire() as conn:
            metrics = await conn.fetch(f"""
                SELECT
                    channel,
                    SUM(total_messages_processed) as total_messages,
                    AVG(avg_response_time_ms)::int as avg_response_time_ms,
                    AVG(escalation_rate) as escalation_rate,
                    AVG(first_contact_resolution_rate) as resolution_rate
                FROM agent_metrics
                WHERE {date_filter}
                AND channel IS NOT NULL
                GROUP BY channel
                ORDER BY total_messages DESC
            """)

            return ChannelMetricsResponse(
                period=period,
                metrics=[
                    ChannelMetrics(
                        channel=m['channel'],
                        total_messages=m['total_messages'] or 0,
                        avg_response_time_ms=m['avg_response_time_ms'] or 0,
                        escalation_rate=float(m['escalation_rate'] or 0),
                        resolution_rate=float(m['resolution_rate'] or 0)
                    )
                    for m in metrics
                ]
            )

    except Exception as e:
        logger.error(f"Error fetching channel metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["system"])
async def root():
    """Root endpoint."""
    return {
        "service": "Customer Success API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "production.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
