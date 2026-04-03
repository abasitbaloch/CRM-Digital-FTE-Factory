"""Gmail channel handler.

This module handles email communication via Gmail API with Pub/Sub notifications.
"""

import os
import base64
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import asyncpg
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailHandler:
    """Handler for Gmail API integration with Pub/Sub notifications.

    This class manages:
    - Gmail API authentication
    - Processing Pub/Sub notifications for new emails
    - Fetching and parsing email messages
    - Sending email replies
    - Storing messages in the database
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        service_account_file: Optional[str] = None,
        delegated_email: Optional[str] = None
    ):
        """Initialize Gmail handler.

        Args:
            db_pool: Database connection pool
            service_account_file: Path to service account JSON file
            delegated_email: Email address to impersonate (for domain-wide delegation)
        """
        self.db_pool = db_pool
        self.service_account_file = service_account_file or os.getenv("GMAIL_SERVICE_ACCOUNT_FILE")
        self.delegated_email = delegated_email or os.getenv("GMAIL_DELEGATED_EMAIL")
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Gmail API service with authentication."""
        try:
            if self.service_account_file:
                # Service account authentication (for workspace)
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file,
                    scopes=['https://www.googleapis.com/auth/gmail.modify']
                )

                if self.delegated_email:
                    credentials = credentials.with_subject(self.delegated_email)

                self.service = build('gmail', 'v1', credentials=credentials)
            else:
                # OAuth2 credentials (for personal Gmail)
                # In production, load from secure storage
                raise ValueError("Gmail authentication not configured")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gmail service: {str(e)}")

    async def process_pubsub_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Pub/Sub notification for new Gmail messages.

        Args:
            notification_data: Pub/Sub message data containing historyId

        Returns:
            Processing result with message count and status
        """
        try:
            # Decode Pub/Sub message
            if 'message' in notification_data:
                message_data = notification_data['message']
                data = base64.b64decode(message_data.get('data', '')).decode('utf-8')
                payload = json.loads(data)
            else:
                payload = notification_data

            email_address = payload.get('emailAddress')
            history_id = payload.get('historyId')

            if not history_id:
                return {"status": "error", "message": "No historyId in notification"}

            # Fetch history changes
            messages = await self._fetch_new_messages(history_id)

            # Process each new message
            processed_count = 0
            for message_id in messages:
                await self._process_message(message_id)
                processed_count += 1

            return {
                "status": "success",
                "messages_processed": processed_count,
                "history_id": history_id
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def _fetch_new_messages(self, history_id: str) -> List[str]:
        """Fetch new message IDs from Gmail history.

        Args:
            history_id: Gmail history ID to start from

        Returns:
            List of message IDs
        """
        try:
            # Run Gmail API call in thread pool (it's synchronous)
            loop = asyncio.get_event_loop()
            history = await loop.run_in_executor(
                None,
                lambda: self.service.users().history().list(
                    userId='me',
                    startHistoryId=history_id,
                    historyTypes=['messageAdded']
                ).execute()
            )

            message_ids = []
            if 'history' in history:
                for record in history['history']:
                    if 'messagesAdded' in record:
                        for msg in record['messagesAdded']:
                            message_ids.append(msg['message']['id'])

            return message_ids

        except HttpError as e:
            raise RuntimeError(f"Failed to fetch Gmail history: {str(e)}")

    async def _process_message(self, message_id: str) -> None:
        """Fetch and process a single Gmail message.

        Args:
            message_id: Gmail message ID
        """
        try:
            # Fetch full message
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
            )

            # Parse message
            parsed = self._parse_message(message)

            # Check if this is a reply to existing conversation
            thread_id = message.get('threadId')
            conversation_id = await self._get_or_create_conversation(
                parsed['from_email'],
                thread_id,
                parsed['subject']
            )

            # Store message in database
            await self._store_message(
                conversation_id=conversation_id,
                customer_email=parsed['from_email'],
                content=parsed['body'],
                message_id=message_id,
                thread_id=thread_id,
                metadata={
                    'gmail_message_id': message_id,
                    'gmail_thread_id': thread_id,
                    'subject': parsed['subject'],
                    'from': parsed['from'],
                    'to': parsed['to'],
                    'date': parsed['date']
                }
            )

            # Mark as processed (remove UNREAD label)
            await loop.run_in_executor(
                None,
                lambda: self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            )

        except Exception as e:
            raise RuntimeError(f"Failed to process message {message_id}: {str(e)}")

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into structured format.

        Args:
            message: Raw Gmail message object

        Returns:
            Parsed message data
        """
        headers = {h['name']: h['value'] for h in message['payload']['headers']}

        # Extract body
        body = ""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')

        return {
            'from': headers.get('From', ''),
            'from_email': self._extract_email(headers.get('From', '')),
            'to': headers.get('To', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'body': body.strip()
        }

    def _extract_email(self, from_header: str) -> str:
        """Extract email address from From header.

        Args:
            from_header: Email From header (e.g., "John Doe <john@example.com>")

        Returns:
            Email address
        """
        import re
        match = re.search(r'<(.+?)>', from_header)
        if match:
            return match.group(1)
        return from_header.strip()

    async def _get_or_create_conversation(
        self,
        customer_email: str,
        thread_id: str,
        subject: str
    ) -> str:
        """Get existing conversation or create new one.

        Args:
            customer_email: Customer's email address
            thread_id: Gmail thread ID
            subject: Email subject

        Returns:
            Conversation ID
        """
        async with self.db_pool.acquire() as conn:
            # Check if conversation exists for this thread
            existing = await conn.fetchrow("""
                SELECT id FROM conversations
                WHERE metadata->>'gmail_thread_id' = $1
                AND is_active = true
            """, thread_id)

            if existing:
                return existing['id']

            # Get or create customer
            customer = await conn.fetchrow("""
                SELECT id FROM customers WHERE email = $1
            """, customer_email)

            if not customer:
                customer = await conn.fetchrow("""
                    INSERT INTO customers (email, name, tier)
                    VALUES ($1, $2, 'free')
                    RETURNING id
                """, customer_email, customer_email.split('@')[0])

            customer_id = customer['id']

            # Create new conversation
            conversation = await conn.fetchrow("""
                INSERT INTO conversations (
                    customer_id,
                    channel,
                    subject,
                    metadata
                )
                VALUES ($1, 'email', $2, $3)
                RETURNING id
            """, customer_id, subject, json.dumps({'gmail_thread_id': thread_id}))

            return conversation['id']

    async def _store_message(
        self,
        conversation_id: str,
        customer_email: str,
        content: str,
        message_id: str,
        thread_id: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Store message in database.

        Args:
            conversation_id: Conversation ID
            customer_email: Customer's email
            content: Message content
            message_id: Gmail message ID
            thread_id: Gmail thread ID
            metadata: Additional metadata

        Returns:
            Message ID
        """
        async with self.db_pool.acquire() as conn:
            # Get customer ID
            customer = await conn.fetchrow("""
                SELECT id FROM customers WHERE email = $1
            """, customer_email)

            if not customer:
                raise ValueError(f"Customer not found: {customer_email}")

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
                VALUES ($1, $2, 'inbound', 'email', $3, $4)
                RETURNING id
            """, conversation_id, customer['id'], content, json.dumps(metadata))

            # Update conversation last_message_at
            await conn.execute("""
                UPDATE conversations
                SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)

            return msg['id']

    async def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email reply via Gmail API.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            thread_id: Gmail thread ID (for replies)
            conversation_id: Database conversation ID

        Returns:
            Send result with message ID
        """
        try:
            # Create email message
            message = MIMEMultipart('alternative')
            message['To'] = to_email
            message['Subject'] = subject if not subject.startswith('Re:') else subject
            message['From'] = self.delegated_email or 'support@example.com'

            # Add plain text and HTML parts
            text_part = MIMEText(body, 'plain')
            message.attach(text_part)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Prepare send request
            send_body = {'raw': raw_message}
            if thread_id:
                send_body['threadId'] = thread_id

            # Send via Gmail API
            loop = asyncio.get_event_loop()
            sent_message = await loop.run_in_executor(
                None,
                lambda: self.service.users().messages().send(
                    userId='me',
                    body=send_body
                ).execute()
            )

            # Store outbound message in database
            if conversation_id:
                await self._store_outbound_message(
                    conversation_id=conversation_id,
                    to_email=to_email,
                    content=body,
                    gmail_message_id=sent_message['id'],
                    thread_id=sent_message.get('threadId')
                )

            return {
                "status": "success",
                "message_id": sent_message['id'],
                "thread_id": sent_message.get('threadId')
            }

        except HttpError as e:
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}"
            }

    async def _store_outbound_message(
        self,
        conversation_id: str,
        to_email: str,
        content: str,
        gmail_message_id: str,
        thread_id: Optional[str]
    ) -> None:
        """Store outbound message in database.

        Args:
            conversation_id: Conversation ID
            to_email: Recipient email
            content: Message content
            gmail_message_id: Gmail message ID
            thread_id: Gmail thread ID
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
                VALUES ($1, $2, 'outbound', 'email', $3, $4, NOW())
            """,
                conversation_id,
                customer['customer_id'],
                content,
                json.dumps({
                    'gmail_message_id': gmail_message_id,
                    'gmail_thread_id': thread_id,
                    'to': to_email
                })
            )

            # Update conversation
            await conn.execute("""
                UPDATE conversations
                SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)
