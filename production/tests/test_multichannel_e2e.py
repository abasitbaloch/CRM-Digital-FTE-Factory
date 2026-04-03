"""Multi-Channel End-to-End Testing

This module provides comprehensive E2E tests for all communication channels
and cross-channel functionality.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
import asyncpg


# ============================================================================
# Test Configuration
# ============================================================================

API_BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def http_client():
    """HTTP client for API requests."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TEST_TIMEOUT) as client:
        yield client


@pytest.fixture
async def db_pool():
    """Database connection pool for test verification."""
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="postgres",
        password="test_password",
        database="customer_success_test",
        min_size=2,
        max_size=5
    )
    yield pool
    await pool.close()


@pytest.fixture
def test_customer_data():
    """Test customer data."""
    return {
        "name": "Test Customer",
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "phone": "+15551234567",
        "company": "Test Corp"
    }


@pytest.fixture
async def cleanup_test_data(db_pool):
    """Cleanup test data after tests."""
    yield
    # Cleanup after test
    async with db_pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM messages WHERE customer_id IN (
                SELECT id FROM customers WHERE email LIKE 'test_%@example.com'
            )
        """)
        await conn.execute("""
            DELETE FROM conversations WHERE customer_id IN (
                SELECT id FROM customers WHERE email LIKE 'test_%@example.com'
            )
        """)
        await conn.execute("""
            DELETE FROM tickets WHERE customer_id IN (
                SELECT id FROM customers WHERE email LIKE 'test_%@example.com'
            )
        """)
        await conn.execute("""
            DELETE FROM customers WHERE email LIKE 'test_%@example.com'
        """)


# ============================================================================
# Web Form Channel Tests
# ============================================================================

@pytest.mark.asyncio
class TestWebFormChannel:
    """End-to-end tests for web form channel."""

    async def test_submit_support_request(
        self,
        http_client: httpx.AsyncClient,
        test_customer_data: Dict[str, Any],
        db_pool: asyncpg.Pool,
        cleanup_test_data
    ):
        """Test submitting a support request via web form."""
        # Submit support request
        response = await http_client.post(
            "/support/submit",
            json={
                "name": test_customer_data["name"],
                "email": test_customer_data["email"],
                "subject": "Test Support Request",
                "message": "This is a test message for E2E testing.",
                "category": "technical",
                "priority": "medium",
                "company": test_customer_data["company"]
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["status"] == "success"
        assert "ticket_id" in data
        assert "conversation_id" in data
        assert "estimated_response_time" in data

        ticket_id = data["ticket_id"]
        conversation_id = data["conversation_id"]

        # Verify ticket was created in database
        async with db_pool.acquire() as conn:
            ticket = await conn.fetchrow("""
                SELECT * FROM tickets WHERE id = $1
            """, ticket_id)

            assert ticket is not None
            assert ticket["subject"] == "Test Support Request"
            assert ticket["status"] == "open"
            assert ticket["priority"] == "medium"

            # Verify conversation was created
            conversation = await conn.fetchrow("""
                SELECT * FROM conversations WHERE id = $1
            """, conversation_id)

            assert conversation is not None
            assert conversation["channel"] == "web_form"
            assert conversation["is_active"] is True

            # Verify message was stored
            messages = await conn.fetch("""
                SELECT * FROM messages WHERE conversation_id = $1
            """, conversation_id)

            assert len(messages) >= 1
            assert messages[0]["direction"] == "inbound"
            assert messages[0]["content"] == "This is a test message for E2E testing."

    async def test_get_ticket_status(
        self,
        http_client: httpx.AsyncClient,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test retrieving ticket status."""
        # First create a ticket
        create_response = await http_client.post(
            "/support/submit",
            json={
                "name": test_customer_data["name"],
                "email": test_customer_data["email"],
                "subject": "Status Check Test",
                "message": "Testing ticket status retrieval.",
                "category": "general"
            }
        )

        assert create_response.status_code == 201
        ticket_id = create_response.json()["ticket_id"]

        # Retrieve ticket status
        status_response = await http_client.get(f"/support/ticket/{ticket_id}")

        assert status_response.status_code == 200
        ticket_data = status_response.json()

        assert ticket_data["ticket_id"] == ticket_id
        assert ticket_data["status"] == "open"
        assert ticket_data["subject"] == "Status Check Test"
        assert ticket_data["customer_email"] == test_customer_data["email"]

    async def test_list_customer_tickets(
        self,
        http_client: httpx.AsyncClient,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test listing all tickets for a customer."""
        # Create multiple tickets
        for i in range(3):
            await http_client.post(
                "/support/submit",
                json={
                    "name": test_customer_data["name"],
                    "email": test_customer_data["email"],
                    "subject": f"Test Ticket {i+1}",
                    "message": f"Test message {i+1}",
                    "category": "general"
                }
            )

        # List tickets
        response = await http_client.get(
            "/support/tickets",
            params={"email": test_customer_data["email"]}
        )

        assert response.status_code == 200
        tickets = response.json()

        assert len(tickets) == 3
        assert all(t["customer_email"] == test_customer_data["email"] for t in tickets)

    async def test_urgent_priority_auto_assignment(
        self,
        http_client: httpx.AsyncClient,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test that urgent keywords trigger high priority."""
        response = await http_client.post(
            "/support/submit",
            json={
                "name": test_customer_data["name"],
                "email": test_customer_data["email"],
                "subject": "URGENT: System Down",
                "message": "This is an emergency! The system is completely down and we need immediate help!",
                "category": "technical"
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Should have shorter response time for urgent issues
        assert "1 hour" in data["estimated_response_time"] or "2 hours" in data["estimated_response_time"]


# ============================================================================
# Email Channel Tests
# ============================================================================

@pytest.mark.asyncio
class TestEmailChannel:
    """End-to-end tests for email channel."""

    async def test_gmail_webhook_processing(
        self,
        http_client: httpx.AsyncClient,
        db_pool: asyncpg.Pool,
        cleanup_test_data
    ):
        """Test Gmail Pub/Sub webhook processing."""
        # Mock Gmail Pub/Sub notification
        pubsub_notification = {
            "message": {
                "data": "eyJlbWFpbEFkZHJlc3MiOiAic3VwcG9ydEBleGFtcGxlLmNvbSIsICJoaXN0b3J5SWQiOiAiMTIzNDU2In0=",  # base64 encoded
                "messageId": "test-message-id",
                "publishTime": datetime.utcnow().isoformat()
            }
        }

        with patch('production.channels.gmail_handler.GmailHandler.process_pubsub_notification') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "messages_processed": 1,
                "history_id": "123456"
            }

            response = await http_client.post(
                "/webhooks/gmail",
                json=pubsub_notification
            )

            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            mock_process.assert_called_once()

    async def test_email_message_storage(
        self,
        db_pool: asyncpg.Pool,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test that email messages are properly stored."""
        async with db_pool.acquire() as conn:
            # Create customer
            customer = await conn.fetchrow("""
                INSERT INTO customers (name, email, tier)
                VALUES ($1, $2, 'free')
                RETURNING id
            """, test_customer_data["name"], test_customer_data["email"])

            customer_id = customer["id"]

            # Create conversation
            conversation = await conn.fetchrow("""
                INSERT INTO conversations (customer_id, channel, subject)
                VALUES ($1, 'email', 'Test Email Thread')
                RETURNING id
            """, customer_id)

            conversation_id = conversation["id"]

            # Store inbound email message
            message = await conn.fetchrow("""
                INSERT INTO messages (
                    conversation_id,
                    customer_id,
                    direction,
                    channel,
                    content,
                    metadata
                )
                VALUES ($1, $2, 'inbound', 'email', $3, $4)
                RETURNING id
            """,
                conversation_id,
                customer_id,
                "Test email content",
                json.dumps({"subject": "Test Email Thread", "from": test_customer_data["email"]})
            )

            assert message is not None

            # Verify message can be retrieved
            retrieved = await conn.fetchrow("""
                SELECT * FROM messages WHERE id = $1
            """, message["id"])

            assert retrieved["content"] == "Test email content"
            assert retrieved["channel"] == "email"
            assert retrieved["direction"] == "inbound"


# ============================================================================
# WhatsApp Channel Tests
# ============================================================================

@pytest.mark.asyncio
class TestWhatsAppChannel:
    """End-to-end tests for WhatsApp channel."""

    async def test_whatsapp_webhook_processing(
        self,
        http_client: httpx.AsyncClient,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test WhatsApp incoming message webhook."""
        # Mock Twilio webhook data
        webhook_data = {
            "MessageSid": "SM1234567890",
            "From": f"whatsapp:{test_customer_data['phone']}",
            "To": "whatsapp:+14155238886",
            "Body": "Hello, I need help with my account",
            "NumMedia": "0"
        }

        with patch('production.channels.whatsapp_handler.WhatsAppHandler.validate_webhook') as mock_validate:
            with patch('production.channels.whatsapp_handler.WhatsAppHandler.process_incoming_message') as mock_process:
                mock_validate.return_value = True
                mock_process.return_value = {
                    "status": "success",
                    "message_id": "msg_test123",
                    "conversation_id": "conv_test123",
                    "has_media": False
                }

                response = await http_client.post(
                    "/webhooks/whatsapp",
                    data=webhook_data,
                    headers={"X-Twilio-Signature": "test-signature"}
                )

                assert response.status_code == 200
                assert response.json()["status"] == "ok"
                mock_validate.assert_called_once()
                mock_process.assert_called_once()

    async def test_whatsapp_status_callback(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test WhatsApp status callback webhook."""
        status_data = {
            "MessageSid": "SM1234567890",
            "MessageStatus": "delivered",
            "To": "whatsapp:+15551234567"
        }

        with patch('production.channels.whatsapp_handler.WhatsAppHandler.validate_webhook') as mock_validate:
            with patch('production.channels.whatsapp_handler.WhatsAppHandler.process_status_callback') as mock_process:
                mock_validate.return_value = True
                mock_process.return_value = {
                    "status": "success",
                    "message_sid": "SM1234567890",
                    "message_status": "delivered"
                }

                response = await http_client.post(
                    "/webhooks/whatsapp/status",
                    data=status_data,
                    headers={"X-Twilio-Signature": "test-signature"}
                )

                assert response.status_code == 200
                assert response.json()["status"] == "ok"

    async def test_whatsapp_message_length_limit(
        self,
        db_pool: asyncpg.Pool,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test that WhatsApp messages respect 1600 character limit."""
        from production.agent.formatters import format_for_whatsapp

        # Create a long message
        long_message = "A" * 2000

        # Format for WhatsApp
        formatted = format_for_whatsapp(long_message)

        # Should be truncated to 1600 chars or less
        assert len(formatted) <= 1600


# ============================================================================
# Cross-Channel Continuity Tests
# ============================================================================

@pytest.mark.asyncio
class TestCrossChannelContinuity:
    """Test conversation continuity across different channels."""

    async def test_customer_switches_channels(
        self,
        http_client: httpx.AsyncClient,
        db_pool: asyncpg.Pool,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test that customer can continue conversation across channels."""
        # Start conversation via web form
        web_response = await http_client.post(
            "/support/submit",
            json={
                "name": test_customer_data["name"],
                "email": test_customer_data["email"],
                "subject": "Multi-channel test",
                "message": "Starting conversation on web form",
                "category": "technical"
            }
        )

        assert web_response.status_code == 201
        web_data = web_response.json()

        # Verify customer was created
        async with db_pool.acquire() as conn:
            customer = await conn.fetchrow("""
                SELECT id FROM customers WHERE email = $1
            """, test_customer_data["email"])

            assert customer is not None
            customer_id = customer["id"]

            # Simulate email message from same customer
            email_conversation = await conn.fetchrow("""
                INSERT INTO conversations (customer_id, channel, subject)
                VALUES ($1, 'email', 'Multi-channel test')
                RETURNING id
            """, customer_id)

            await conn.execute("""
                INSERT INTO messages (
                    conversation_id,
                    customer_id,
                    direction,
                    channel,
                    content
                )
                VALUES ($1, $2, 'inbound', 'email', $3)
            """,
                email_conversation["id"],
                customer_id,
                "Following up via email"
            )

            # Verify both conversations exist for same customer
            conversations = await conn.fetch("""
                SELECT * FROM conversations WHERE customer_id = $1
            """, customer_id)

            assert len(conversations) >= 2
            channels = [c["channel"] for c in conversations]
            assert "web_form" in channels
            assert "email" in channels

    async def test_conversation_history_retrieval(
        self,
        http_client: httpx.AsyncClient,
        db_pool: asyncpg.Pool,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test retrieving conversation history."""
        # Create a conversation with multiple messages
        async with db_pool.acquire() as conn:
            customer = await conn.fetchrow("""
                INSERT INTO customers (name, email, tier)
                VALUES ($1, $2, 'free')
                RETURNING id
            """, test_customer_data["name"], test_customer_data["email"])

            conversation = await conn.fetchrow("""
                INSERT INTO conversations (customer_id, channel, subject)
                VALUES ($1, 'web_form', 'Test Conversation')
                RETURNING id
            """, customer["id"])

            conversation_id = conversation["id"]

            # Add multiple messages
            for i in range(5):
                await conn.execute("""
                    INSERT INTO messages (
                        conversation_id,
                        customer_id,
                        direction,
                        channel,
                        content
                    )
                    VALUES ($1, $2, $3, 'web_form', $4)
                """,
                    conversation_id,
                    customer["id"],
                    "inbound" if i % 2 == 0 else "outbound",
                    f"Message {i+1}"
                )

        # Retrieve conversation history
        response = await http_client.get(f"/conversations/{conversation_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["conversation_id"] == conversation_id
        assert len(data["messages"]) == 5
        assert data["customer_email"] == test_customer_data["email"]


# ============================================================================
# Channel Metrics Tests
# ============================================================================

@pytest.mark.asyncio
class TestChannelMetrics:
    """Test channel performance metrics."""

    async def test_get_channel_metrics(
        self,
        http_client: httpx.AsyncClient,
        db_pool: asyncpg.Pool
    ):
        """Test retrieving channel metrics."""
        # Insert test metrics
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_metrics (
                    metric_date,
                    metric_hour,
                    agent_version,
                    channel,
                    total_messages_processed,
                    avg_response_time_ms,
                    escalation_rate,
                    first_contact_resolution_rate
                )
                VALUES
                    (CURRENT_DATE, 10, '1.0.0', 'email', 100, 2000, 10.5, 85.0),
                    (CURRENT_DATE, 10, '1.0.0', 'whatsapp', 150, 1500, 8.0, 90.0),
                    (CURRENT_DATE, 10, '1.0.0', 'web_form', 80, 1800, 12.0, 82.0)
                ON CONFLICT DO NOTHING
            """)

        # Retrieve metrics
        response = await http_client.get("/metrics/channels?period=today")

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "today"
        assert len(data["metrics"]) >= 3

        # Verify metrics structure
        for metric in data["metrics"]:
            assert "channel" in metric
            assert "total_messages" in metric
            assert "avg_response_time_ms" in metric
            assert "escalation_rate" in metric
            assert "resolution_rate" in metric

    async def test_customer_lookup(
        self,
        http_client: httpx.AsyncClient,
        db_pool: asyncpg.Pool,
        test_customer_data: Dict[str, Any],
        cleanup_test_data
    ):
        """Test customer lookup endpoint."""
        # Create customer with tickets
        async with db_pool.acquire() as conn:
            customer = await conn.fetchrow("""
                INSERT INTO customers (name, email, tier)
                VALUES ($1, $2, 'pro')
                RETURNING id
            """, test_customer_data["name"], test_customer_data["email"])

            customer_id = customer["id"]

            # Create tickets
            for i in range(3):
                await conn.execute("""
                    INSERT INTO tickets (
                        customer_id,
                        subject,
                        description,
                        status,
                        priority
                    )
                    VALUES ($1, $2, $3, $4, 'medium')
                """,
                    customer_id,
                    f"Test Ticket {i+1}",
                    "Test description",
                    "open" if i < 2 else "resolved"
                )

        # Lookup customer
        response = await http_client.get(
            "/customers/lookup",
            params={"email": test_customer_data["email"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["customer_id"] == customer_id
        assert data["email"] == test_customer_data["email"]
        assert data["tier"] == "pro"
        assert data["total_tickets"] == 3
        assert data["open_tickets"] == 2


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.asyncio
class TestHealthCheck:
    """Test system health check."""

    async def test_health_endpoint(self, http_client: httpx.AsyncClient):
        """Test health check endpoint."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "customer_success_api"
        assert "version" in data
        assert "database" in data
        assert "kafka" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
