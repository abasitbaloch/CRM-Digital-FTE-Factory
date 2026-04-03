"""Web form channel handler.

This module provides FastAPI endpoints for web-based support submissions.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

import asyncpg
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr, validator


# ============================================================================
# Pydantic Models
# ============================================================================

class SupportCategory(str, Enum):
    """Support request categories."""
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT = "account"
    GENERAL = "general"
    OTHER = "other"


class PriorityLevel(str, Enum):
    """Priority levels for support requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportSubmitRequest(BaseModel):
    """Request model for support form submission."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Customer's full name"
    )
    email: EmailStr = Field(
        ...,
        description="Customer's email address"
    )
    subject: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Brief subject line"
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed message or issue description"
    )
    category: SupportCategory = Field(
        default=SupportCategory.GENERAL,
        description="Category of the support request"
    )
    priority: Optional[PriorityLevel] = Field(
        default=None,
        description="Priority level (auto-assigned if not provided)"
    )

    # Optional fields
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Customer's phone number"
    )
    company: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Company name"
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="Existing customer ID if known"
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (browser info, referrer, etc.)"
    )

    @validator('message')
    def validate_message_content(cls, v):
        """Ensure message is not just whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()

    @validator('subject')
    def validate_subject(cls, v):
        """Ensure subject is meaningful."""
        if not v.strip():
            raise ValueError("Subject cannot be empty or whitespace only")
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "name": "Sarah Johnson",
                "email": "sarah@example.com",
                "subject": "Unable to export data",
                "message": "I'm trying to export my data but getting a timeout error. I've tried multiple times with the same result.",
                "category": "technical",
                "priority": "medium",
                "phone": "+1234567890",
                "company": "Acme Corp"
            }
        }


class SupportSubmitResponse(BaseModel):
    """Response model for support form submission."""

    status: str = Field(..., description="Status of the submission")
    ticket_id: str = Field(..., description="Generated ticket ID")
    conversation_id: str = Field(..., description="Conversation ID")
    message: str = Field(..., description="Confirmation message")
    estimated_response_time: str = Field(
        ...,
        description="Estimated response time"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "ticket_id": "TKT_000123",
                "conversation_id": "conv_abc123",
                "message": "Your support request has been received. We'll respond within 4 hours.",
                "estimated_response_time": "4 hours"
            }
        }


class TicketStatus(str, Enum):
    """Ticket status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketResponse(BaseModel):
    """Response model for ticket retrieval."""

    ticket_id: str
    status: TicketStatus
    subject: str
    description: str
    category: Optional[str]
    priority: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    # Customer info
    customer_name: str
    customer_email: str

    # Resolution info
    resolution: Optional[str] = None

    # Metadata
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None

    class Config:
        schema_extra = {
            "example": {
                "ticket_id": "TKT_000123",
                "status": "in_progress",
                "subject": "Unable to export data",
                "description": "Customer experiencing timeout errors during data export",
                "category": "technical",
                "priority": "medium",
                "created_at": "2024-03-15T10:30:00Z",
                "updated_at": "2024-03-15T11:00:00Z",
                "customer_name": "Sarah Johnson",
                "customer_email": "sarah@example.com",
                "assigned_to": "support_agent_1"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    status: str = "error"
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# FastAPI Router
# ============================================================================

router = APIRouter(
    prefix="/support",
    tags=["support"],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)


# Dependency to get database pool
async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Get database pool from app state."""
    return request.app.state.db_pool


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/submit",
    response_model=SupportSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a support request",
    description="Submit a new support request via web form"
)
async def submit_support_request(
    request: SupportSubmitRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> SupportSubmitResponse:
    """Submit a new support request.

    This endpoint:
    1. Validates the submission
    2. Creates or retrieves the customer record
    3. Creates a new conversation
    4. Creates a support ticket
    5. Stores the initial message
    6. Returns confirmation with ticket ID

    Args:
        request: Support submission data
        db_pool: Database connection pool

    Returns:
        Submission confirmation with ticket and conversation IDs

    Raises:
        HTTPException: If submission fails
    """
    try:
        async with db_pool.acquire() as conn:
            # Start transaction
            async with conn.transaction():
                # 1. Get or create customer
                customer = await conn.fetchrow("""
                    SELECT id, name, email FROM customers WHERE email = $1
                """, request.email)

                if customer:
                    customer_id = customer['id']
                    # Update name if different
                    if customer['name'] != request.name:
                        await conn.execute("""
                            UPDATE customers SET name = $1, updated_at = NOW()
                            WHERE id = $2
                        """, request.name, customer_id)
                else:
                    # Create new customer
                    customer = await conn.fetchrow("""
                        INSERT INTO customers (
                            name,
                            email,
                            company,
                            tier
                        )
                        VALUES ($1, $2, $3, 'free')
                        RETURNING id
                    """, request.name, request.email, request.company)
                    customer_id = customer['id']

                    # Add phone identifier if provided
                    if request.phone:
                        await conn.execute("""
                            INSERT INTO customer_identifiers (
                                customer_id,
                                identifier_type,
                                identifier_value,
                                is_primary
                            )
                            VALUES ($1, 'phone', $2, true)
                        """, customer_id, request.phone)

                # 2. Create conversation
                conversation = await conn.fetchrow("""
                    INSERT INTO conversations (
                        customer_id,
                        channel,
                        subject,
                        metadata
                    )
                    VALUES ($1, 'web_form', $2, $3)
                    RETURNING id
                """,
                    customer_id,
                    request.subject,
                    json.dumps(request.metadata or {})
                )
                conversation_id = conversation['id']

                # 3. Auto-assign priority if not provided
                priority = request.priority.value if request.priority else "medium"

                # Auto-escalate urgent keywords
                urgent_keywords = ['urgent', 'critical', 'emergency', 'asap', 'immediately']
                if any(keyword in request.message.lower() for keyword in urgent_keywords):
                    priority = "high"

                # 4. Create ticket
                ticket = await conn.fetchrow("""
                    INSERT INTO tickets (
                        customer_id,
                        conversation_id,
                        subject,
                        description,
                        category,
                        priority,
                        status
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, 'open')
                    RETURNING id
                """,
                    customer_id,
                    conversation_id,
                    request.subject,
                    request.message,
                    request.category.value,
                    priority
                )
                ticket_id = ticket['id']

                # 5. Store initial message
                await conn.execute("""
                    INSERT INTO messages (
                        conversation_id,
                        customer_id,
                        direction,
                        channel,
                        content,
                        metadata
                    )
                    VALUES ($1, $2, 'inbound', 'web_form', $3, $4)
                """,
                    conversation_id,
                    customer_id,
                    request.message,
                    json.dumps({
                        'subject': request.subject,
                        'category': request.category.value,
                        'priority': priority,
                        'form_metadata': request.metadata
                    })
                )

                # 6. Create interaction record
                await conn.execute("""
                    INSERT INTO interactions (
                        customer_id,
                        conversation_id,
                        channel,
                        summary,
                        interaction_type,
                        outcome
                    )
                    VALUES ($1, $2, 'web_form', $3, 'support', 'pending')
                """,
                    customer_id,
                    conversation_id,
                    f"Support request: {request.subject}"
                )

        # Determine estimated response time based on priority
        response_times = {
            "urgent": "1 hour",
            "high": "2 hours",
            "medium": "4 hours",
            "low": "24 hours"
        }
        estimated_time = response_times.get(priority, "4 hours")

        return SupportSubmitResponse(
            status="success",
            ticket_id=ticket_id,
            conversation_id=conversation_id,
            message=f"Your support request has been received. We'll respond within {estimated_time}.",
            estimated_response_time=estimated_time
        )

    except asyncpg.PostgresError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit support request: {str(e)}"
        )


@router.get(
    "/ticket/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket status",
    description="Retrieve the current status and details of a support ticket"
)
async def get_ticket_status(
    ticket_id: str,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> TicketResponse:
    """Get ticket status and details.

    Args:
        ticket_id: Ticket ID (e.g., TKT_000123)
        db_pool: Database connection pool

    Returns:
        Ticket details and current status

    Raises:
        HTTPException: If ticket not found or access denied
    """
    try:
        async with db_pool.acquire() as conn:
            ticket = await conn.fetchrow("""
                SELECT
                    t.id,
                    t.subject,
                    t.description,
                    t.category,
                    t.status,
                    t.priority,
                    t.assigned_to,
                    t.resolution,
                    t.tags,
                    t.created_at,
                    t.updated_at,
                    t.resolved_at,
                    c.name as customer_name,
                    c.email as customer_email
                FROM tickets t
                JOIN customers c ON t.customer_id = c.id
                WHERE t.id = $1
            """, ticket_id)

            if not ticket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ticket {ticket_id} not found"
                )

            return TicketResponse(
                ticket_id=ticket['id'],
                status=TicketStatus(ticket['status']),
                subject=ticket['subject'],
                description=ticket['description'],
                category=ticket['category'],
                priority=ticket['priority'],
                created_at=ticket['created_at'],
                updated_at=ticket['updated_at'],
                resolved_at=ticket['resolved_at'],
                customer_name=ticket['customer_name'],
                customer_email=ticket['customer_email'],
                resolution=ticket['resolution'],
                assigned_to=ticket['assigned_to'],
                tags=ticket['tags']
            )

    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ticket: {str(e)}"
        )


@router.get(
    "/tickets",
    response_model=List[TicketResponse],
    summary="List tickets by email",
    description="Retrieve all tickets for a customer by email address"
)
async def list_customer_tickets(
    email: EmailStr,
    status_filter: Optional[TicketStatus] = None,
    limit: int = 10,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> List[TicketResponse]:
    """List all tickets for a customer.

    Args:
        email: Customer email address
        status_filter: Optional status filter
        limit: Maximum number of tickets to return (default 10, max 50)
        db_pool: Database connection pool

    Returns:
        List of tickets

    Raises:
        HTTPException: If query fails
    """
    try:
        # Limit max results
        limit = min(limit, 50)

        async with db_pool.acquire() as conn:
            if status_filter:
                tickets = await conn.fetch("""
                    SELECT
                        t.id,
                        t.subject,
                        t.description,
                        t.category,
                        t.status,
                        t.priority,
                        t.assigned_to,
                        t.resolution,
                        t.tags,
                        t.created_at,
                        t.updated_at,
                        t.resolved_at,
                        c.name as customer_name,
                        c.email as customer_email
                    FROM tickets t
                    JOIN customers c ON t.customer_id = c.id
                    WHERE c.email = $1 AND t.status = $2
                    ORDER BY t.created_at DESC
                    LIMIT $3
                """, email, status_filter.value, limit)
            else:
                tickets = await conn.fetch("""
                    SELECT
                        t.id,
                        t.subject,
                        t.description,
                        t.category,
                        t.status,
                        t.priority,
                        t.assigned_to,
                        t.resolution,
                        t.tags,
                        t.created_at,
                        t.updated_at,
                        t.resolved_at,
                        c.name as customer_name,
                        c.email as customer_email
                    FROM tickets t
                    JOIN customers c ON t.customer_id = c.id
                    WHERE c.email = $1
                    ORDER BY t.created_at DESC
                    LIMIT $2
                """, email, limit)

            return [
                TicketResponse(
                    ticket_id=ticket['id'],
                    status=TicketStatus(ticket['status']),
                    subject=ticket['subject'],
                    description=ticket['description'],
                    category=ticket['category'],
                    priority=ticket['priority'],
                    created_at=ticket['created_at'],
                    updated_at=ticket['updated_at'],
                    resolved_at=ticket['resolved_at'],
                    customer_name=ticket['customer_name'],
                    customer_email=ticket['customer_email'],
                    resolution=ticket['resolution'],
                    assigned_to=ticket['assigned_to'],
                    tags=ticket['tags']
                )
                for ticket in tickets
            ]

    except asyncpg.PostgresError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tickets: {str(e)}"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get(
    "/health",
    summary="Health check",
    description="Check if the support API is operational"
)
async def health_check(db_pool: asyncpg.Pool = Depends(get_db_pool)) -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status
    """
    try:
        # Test database connection
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "service": "support_api",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )
