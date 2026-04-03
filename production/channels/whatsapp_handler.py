"""WhatsApp channel handler.

This module handles WhatsApp communication via Twilio API.
"""

import os
import json
import hmac
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode

import asyncpg
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from twilio.base.exceptions import TwilioRestException


class WhatsAppHandler:
    """Handler for WhatsApp integration via Twilio.

    This class manages:
    - Twilio API authentication
    - Webhook signature validation
    - Processing incoming WhatsApp messages
    - Sending WhatsApp replies
    - Storing messages in the database
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        whatsapp_number: Optional[str] = None
    ):
        """Initialize WhatsApp handler.

        Args:
            db_pool: Database connection pool
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            whatsapp_number: WhatsApp business number (format: whatsapp:+1234567890)
        """
        self.db_pool = db_pool
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = whatsapp_number or os.getenv("TWILIO_WHATSAPP_NUMBER")

        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Twilio credentials not configured")

        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)
        self.validator = RequestValidator(self.auth_token)

    def validate_webhook(
        self,
        url: str,
        params: Dict[str, Any],
        signature: str
    ) -> bool:
        """Validate Twilio webhook signature.

        Args:
            url: Full webhook URL
            params: Request parameters
            signature: X-Twilio-Signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        return self.validator.validate(url, params, signature)

    async def process_incoming_message(
        self,
        webhook_data: Dict[str, Any],
        validated: bool = False
    ) -> Dict[str, Any]:
        """Process incoming WhatsApp message from Twilio webhook.

        Args:
            webhook_data: Twilio webhook POST data
            validated: Whether webhook signature has been validated

        Returns:
            Processing result
        """
        try:
            if not validated:
                raise ValueError("Webhook signature not validated")

            # Extract message data
            from_number = webhook_data.get('From', '')  # Format: whatsapp:+1234567890
            to_number = webhook_data.get('To', '')
            body = webhook_data.get('Body', '')
            message_sid = webhook_data.get('MessageSid', '')
            num_media = int(webhook_data.get('NumMedia', 0))

            # Extract phone number
            phone_number = from_number.replace('whatsapp:', '')

            # Handle media attachments
            media_urls = []
            if num_media > 0:
                for i in range(num_media):
                    media_url = webhook_data.get(f'MediaUrl{i}')
                    media_type = webhook_data.get(f'MediaContentType{i}')
                    if media_url:
                        media_urls.append({
                            'url': media_url,
                            'type': media_type
                        })

            # Get or create conversation
            conversation_id = await self._get_or_create_conversation(
                phone_number=phone_number,
                from_number=from_number
            )

            # Store message in database
            message_id = await self._store_message(
                conversation_id=conversation_id,
                phone_number=phone_number,
                content=body,
                message_sid=message_sid,
                media_urls=media_urls,
                metadata={
                    'twilio_message_sid': message_sid,
                    'from': from_number,
                    'to': to_number,
                    'num_media': num_media,
                    'media': media_urls
                }
            )

            return {
                "status": "success",
                "message_id": message_id,
                "conversation_id": conversation_id,
                "has_media": num_media > 0
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def _get_or_create_conversation(
        self,
        phone_number: str,
        from_number: str
    ) -> str:
        """Get existing conversation or create new one.

        Args:
            phone_number: Customer's phone number (without whatsapp: prefix)
            from_number: Full WhatsApp number (with whatsapp: prefix)

        Returns:
            Conversation ID
        """
        async with self.db_pool.acquire() as conn:
            # Check if conversation exists for this phone number
            existing = await conn.fetchrow("""
                SELECT c.id
                FROM conversations c
                JOIN customer_identifiers ci ON c.customer_id = ci.customer_id
                WHERE ci.identifier_type = 'whatsapp'
                AND ci.identifier_value = $1
                AND c.channel = 'whatsapp'
                AND c.is_active = true
                ORDER BY c.last_message_at DESC
                LIMIT 1
            """, phone_number)

            if existing:
                return existing['id']

            # Get or create customer
            customer = await conn.fetchrow("""
                SELECT customer_id
                FROM customer_identifiers
                WHERE identifier_type = 'whatsapp'
                AND identifier_value = $1
            """, phone_number)

            if customer:
                customer_id = customer['customer_id']
            else:
                # Create new customer
                customer = await conn.fetchrow("""
                    INSERT INTO customers (name, tier)
                    VALUES ($1, 'free')
                    RETURNING id
                """, phone_number)
                customer_id = customer['id']

                # Add WhatsApp identifier
                await conn.execute("""
                    INSERT INTO customer_identifiers (
                        customer_id,
                        identifier_type,
                        identifier_value,
                        is_primary
                    )
                    VALUES ($1, 'whatsapp', $2, true)
                """, customer_id, phone_number)

            # Create new conversation
            conversation = await conn.fetchrow("""
                INSERT INTO conversations (
                    customer_id,
                    channel,
                    subject,
                    metadata
                )
                VALUES ($1, 'whatsapp', 'WhatsApp Conversation', $2)
                RETURNING id
            """, customer_id, json.dumps({'whatsapp_number': from_number}))

            return conversation['id']

    async def _store_message(
        self,
        conversation_id: str,
        phone_number: str,
        content: str,
        message_sid: str,
        media_urls: list,
        metadata: Dict[str, Any]
    ) -> str:
        """Store message in database.

        Args:
            conversation_id: Conversation ID
            phone_number: Customer's phone number
            content: Message content
            message_sid: Twilio message SID
            media_urls: List of media URLs
            metadata: Additional metadata

        Returns:
            Message ID
        """
        async with self.db_pool.acquire() as conn:
            # Get customer ID
            customer = await conn.fetchrow("""
                SELECT customer_id
                FROM customer_identifiers
                WHERE identifier_type = 'whatsapp'
                AND identifier_value = $1
            """, phone_number)

            if not customer:
                raise ValueError(f"Customer not found for phone: {phone_number}")

            # Store message
            msg = await conn.fetchrow("""
                INSERT INTO messages (
                    conversation_id,
                    customer_id,
                    direction,
                    channel,
                    content,
                    metadata
                )
                VALUES ($1, $2, 'inbound', 'whatsapp', $3, $4)
                RETURNING id
            """, conversation_id, customer['customer_id'], content, json.dumps(metadata))

            # Update conversation last_message_at
            await conn.execute("""
                UPDATE conversations
                SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)

            return msg['id']

    async def send_message(
        self,
        to_phone: str,
        message: str,
        conversation_id: Optional[str] = None,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send WhatsApp message via Twilio.

        Args:
            to_phone: Recipient phone number (format: +1234567890)
            message: Message text (max 1600 characters)
            conversation_id: Database conversation ID
            media_url: Optional media URL to send

        Returns:
            Send result with message SID
        """
        try:
            # Ensure phone number has whatsapp: prefix
            if not to_phone.startswith('whatsapp:'):
                to_phone = f'whatsapp:{to_phone}'

            # Truncate message if too long (WhatsApp limit is 1600 chars)
            if len(message) > 1600:
                message = message[:1597] + "..."

            # Send via Twilio
            twilio_message = self.client.messages.create(
                from_=self.whatsapp_number,
                to=to_phone,
                body=message,
                media_url=[media_url] if media_url else None
            )

            # Store outbound message in database
            if conversation_id:
                await self._store_outbound_message(
                    conversation_id=conversation_id,
                    to_phone=to_phone.replace('whatsapp:', ''),
                    content=message,
                    message_sid=twilio_message.sid,
                    media_url=media_url
                )

            return {
                "status": "success",
                "message_sid": twilio_message.sid,
                "to": to_phone
            }

        except TwilioRestException as e:
            return {
                "status": "error",
                "message": f"Twilio error: {e.msg}",
                "code": e.code
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def _store_outbound_message(
        self,
        conversation_id: str,
        to_phone: str,
        content: str,
        message_sid: str,
        media_url: Optional[str]
    ) -> None:
        """Store outbound message in database.

        Args:
            conversation_id: Conversation ID
            to_phone: Recipient phone number
            content: Message content
            message_sid: Twilio message SID
            media_url: Media URL if sent
        """
        async with self.db_pool.acquire() as conn:
            # Get customer ID from conversation
            customer = await conn.fetchrow("""
                SELECT customer_id FROM conversations WHERE id = $1
            """, conversation_id)

            if not customer:
                raise ValueError(f"Conversation not found: {conversation_id}")

            # Store message
            await conn.execute("""
                INSERT INTO messages (
                    conversation_id,
                    customer_id,
                    direction,
                    channel,
                    content,
                    metadata,
                    sent_at
                )
                VALUES ($1, $2, 'outbound', 'whatsapp', $3, $4, NOW())
            """,
                conversation_id,
                customer['customer_id'],
                content,
                json.dumps({
                    'twilio_message_sid': message_sid,
                    'to': to_phone,
                    'media_url': media_url
                })
            )

            # Update conversation
            await conn.execute("""
                UPDATE conversations
                SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)

    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get delivery status of a sent message.

        Args:
            message_sid: Twilio message SID

        Returns:
            Message status information
        """
        try:
            message = self.client.messages(message_sid).fetch()

            return {
                "status": message.status,  # queued, sent, delivered, read, failed, undelivered
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "date_updated": message.date_updated.isoformat() if message.date_updated else None
            }

        except TwilioRestException as e:
            return {
                "status": "error",
                "message": f"Failed to fetch status: {e.msg}"
            }

    async def process_status_callback(
        self,
        webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Twilio status callback webhook.

        Args:
            webhook_data: Twilio status callback data

        Returns:
            Processing result
        """
        try:
            message_sid = webhook_data.get('MessageSid')
            message_status = webhook_data.get('MessageStatus')

            if not message_sid:
                return {"status": "error", "message": "No MessageSid"}

            # Update message status in database
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE messages
                    SET metadata = jsonb_set(
                        metadata,
                        '{delivery_status}',
                        $1::jsonb
                    ),
                    delivered_at = CASE
                        WHEN $2 IN ('delivered', 'read') THEN NOW()
                        ELSE delivered_at
                    END,
                    read_at = CASE
                        WHEN $2 = 'read' THEN NOW()
                        ELSE read_at
                    END
                    WHERE metadata->>'twilio_message_sid' = $3
                """,
                    json.dumps(message_status),
                    message_status,
                    message_sid
                )

            return {
                "status": "success",
                "message_sid": message_sid,
                "message_status": message_status
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def format_message_for_whatsapp(
        self,
        message: str,
        use_emojis: bool = True
    ) -> str:
        """Format message for WhatsApp (concise, scannable).

        Args:
            message: Original message
            use_emojis: Whether to include emojis

        Returns:
            Formatted message
        """
        # WhatsApp best practices:
        # - Keep messages under 1600 chars
        # - Use short paragraphs
        # - Emojis for warmth
        # - Clear formatting

        # Truncate if too long
        if len(message) > 1600:
            message = message[:1597] + "..."

        return message
