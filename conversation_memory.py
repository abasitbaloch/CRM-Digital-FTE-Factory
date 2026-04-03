"""
Conversation Memory and Customer Tracking System
Extends the Customer Success AI Agent with context awareness
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Message:
    """Single message in a conversation"""
    timestamp: str
    role: str  # 'customer' or 'agent'
    content: str
    channel: str
    sentiment: Optional[str] = None
    escalated: bool = False


@dataclass
class CustomerProfile:
    """Complete customer profile with conversation history"""
    customer_id: str  # Primary key (email address)
    name: str
    email: str
    phone: Optional[str] = None

    # Conversation tracking
    conversations: List[Message] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)

    # Status tracking
    resolution_status: str = "pending"  # pending, solved, escalated
    current_sentiment: str = "neutral"
    sentiment_history: List[Tuple[str, str]] = field(default_factory=list)  # (timestamp, sentiment)

    # Channel tracking
    original_channel: Optional[str] = None
    channels_used: List[str] = field(default_factory=list)
    channel_switches: int = 0

    # Metadata
    first_contact: Optional[str] = None
    last_contact: Optional[str] = None
    total_interactions: int = 0
    escalation_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "conversations": [
                {
                    "timestamp": msg.timestamp,
                    "role": msg.role,
                    "content": msg.content,
                    "channel": msg.channel,
                    "sentiment": msg.sentiment,
                    "escalated": msg.escalated
                }
                for msg in self.conversations
            ],
            "topics_discussed": self.topics_discussed,
            "resolution_status": self.resolution_status,
            "current_sentiment": self.current_sentiment,
            "sentiment_history": self.sentiment_history,
            "original_channel": self.original_channel,
            "channels_used": self.channels_used,
            "channel_switches": self.channel_switches,
            "first_contact": self.first_contact,
            "last_contact": self.last_contact,
            "total_interactions": self.total_interactions,
            "escalation_count": self.escalation_count
        }


class TopicExtractor:
    """Extract topics from customer messages"""

    # Define topic keywords
    TOPICS = {
        "billing": ["bill", "charge", "payment", "invoice", "refund", "price", "cost", "subscription"],
        "technical": ["crash", "bug", "error", "not working", "broken", "issue", "problem", "slow"],
        "account": ["login", "password", "account", "access", "locked", "reset", "2fa", "authentication"],
        "features": ["how to", "how do i", "can i", "feature", "functionality", "customize", "workflow"],
        "integration": ["slack", "github", "zapier", "api", "webhook", "integration", "connect"],
        "data": ["export", "import", "backup", "data", "migration", "transfer"],
        "team": ["member", "user", "invite", "permission", "role", "team", "workspace"],
        "mobile": ["app", "iphone", "android", "ipad", "mobile", "phone"],
        "enterprise": ["enterprise", "sso", "saml", "compliance", "security", "audit"],
        "cancellation": ["cancel", "unsubscribe", "stop", "quit", "leave"]
    }

    @staticmethod
    def extract(message: str) -> List[str]:
        """Extract topics from message"""
        message_lower = message.lower()
        topics = []

        for topic, keywords in TopicExtractor.TOPICS.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)

        return topics if topics else ["general"]


class ConversationManager:
    """Manages conversation history and customer profiles"""

    def __init__(self):
        self.customers: Dict[str, CustomerProfile] = {}
        self.phone_to_email: Dict[str, str] = {}  # Map phone numbers to email addresses

    def get_or_create_customer(self, ticket: Dict) -> CustomerProfile:
        """Get existing customer or create new profile"""

        # Determine customer ID (prefer email)
        customer_id = None
        email = ticket.get("customer_email")
        phone = ticket.get("customer_phone")

        if email:
            customer_id = email
        elif phone:
            # Check if we've seen this phone number before
            if phone in self.phone_to_email:
                customer_id = self.phone_to_email[phone]
            else:
                # Use phone as temporary ID until we get email
                customer_id = phone

        # Get or create customer profile
        if customer_id not in self.customers:
            profile = CustomerProfile(
                customer_id=customer_id,
                name=ticket.get("customer_name", "Unknown"),
                email=email or "",
                phone=phone,
                original_channel=ticket["channel"],
                first_contact=ticket["timestamp"]
            )
            self.customers[customer_id] = profile

            # Map phone to email if both exist
            if phone and email:
                self.phone_to_email[phone] = email
        else:
            profile = self.customers[customer_id]

            # Update profile with new information
            if email and not profile.email:
                profile.email = email
                # Update customer_id if we now have email
                if customer_id != email:
                    self.customers[email] = profile
                    del self.customers[customer_id]
                    if phone:
                        self.phone_to_email[phone] = email
                    customer_id = email

            if phone and not profile.phone:
                profile.phone = phone
                if email:
                    self.phone_to_email[phone] = email

        return self.customers[customer_id]

    def add_customer_message(self, customer_id: str, ticket: Dict):
        """Add customer message to conversation history"""
        profile = self.customers[customer_id]

        message = Message(
            timestamp=ticket["timestamp"],
            role="customer",
            content=ticket["message"],
            channel=ticket["channel"],
            sentiment=ticket.get("sentiment", "neutral")
        )

        profile.conversations.append(message)
        profile.last_contact = ticket["timestamp"]
        profile.total_interactions += 1

        # Track channel usage
        if ticket["channel"] not in profile.channels_used:
            profile.channels_used.append(ticket["channel"])
            if len(profile.channels_used) > 1:
                profile.channel_switches += 1

        # Track sentiment
        new_sentiment = ticket.get("sentiment", "neutral")
        if new_sentiment != profile.current_sentiment:
            profile.sentiment_history.append((ticket["timestamp"], new_sentiment))
            profile.current_sentiment = new_sentiment

        # Extract and track topics
        topics = TopicExtractor.extract(ticket["message"])
        for topic in topics:
            if topic not in profile.topics_discussed:
                profile.topics_discussed.append(topic)

    def add_agent_response(self, customer_id: str, response: str, channel: str,
                          escalated: bool, timestamp: str):
        """Add agent response to conversation history"""
        profile = self.customers[customer_id]

        message = Message(
            timestamp=timestamp,
            role="agent",
            content=response,
            channel=channel,
            escalated=escalated
        )

        profile.conversations.append(message)

        # Update resolution status
        if escalated:
            profile.resolution_status = "escalated"
            profile.escalation_count += 1
        elif not escalated and profile.resolution_status == "pending":
            # If agent provided answer without escalation, mark as solved
            profile.resolution_status = "solved"

    def get_conversation_context(self, customer_id: str, max_messages: int = 5) -> List[Message]:
        """Get recent conversation history for context"""
        if customer_id not in self.customers:
            return []

        return self.customers[customer_id].conversations[-max_messages:]

    def get_conversation_summary(self, customer_id: str) -> str:
        """Generate a summary of the conversation for context"""
        if customer_id not in self.customers:
            return "No previous conversation history."

        profile = self.customers[customer_id]
        context = self.get_conversation_context(customer_id)

        if not context:
            return "No previous conversation history."

        summary_parts = []

        # Add conversation history
        summary_parts.append("Previous conversation:")
        for msg in context:
            role_label = "Customer" if msg.role == "customer" else "Agent"
            summary_parts.append(f"- {role_label}: {msg.content[:100]}...")

        # Add topics discussed
        if profile.topics_discussed:
            summary_parts.append(f"\nTopics discussed: {', '.join(profile.topics_discussed)}")

        # Add status
        summary_parts.append(f"Current status: {profile.resolution_status}")

        # Add channel info
        if len(profile.channels_used) > 1:
            summary_parts.append(f"Channel switches: {profile.channel_switches} (started on {profile.original_channel})")

        return "\n".join(summary_parts)

    def get_customer_stats(self) -> Dict:
        """Get overall statistics"""
        total_customers = len(self.customers)

        stats = {
            "total_customers": total_customers,
            "by_status": defaultdict(int),
            "by_sentiment": defaultdict(int),
            "by_original_channel": defaultdict(int),
            "multi_channel_customers": 0,
            "total_interactions": 0,
            "total_escalations": 0,
            "topics": defaultdict(int)
        }

        for profile in self.customers.values():
            stats["by_status"][profile.resolution_status] += 1
            stats["by_sentiment"][profile.current_sentiment] += 1
            stats["by_original_channel"][profile.original_channel] += 1
            stats["total_interactions"] += profile.total_interactions
            stats["total_escalations"] += profile.escalation_count

            if len(profile.channels_used) > 1:
                stats["multi_channel_customers"] += 1

            for topic in profile.topics_discussed:
                stats["topics"][topic] += 1

        return stats

    def save_to_file(self, filepath: str):
        """Save conversation data to JSON file"""
        data = {
            "customers": {cid: profile.to_dict() for cid, profile in self.customers.items()},
            "phone_to_email": self.phone_to_email
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filepath: str):
        """Load conversation data from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.phone_to_email = data.get("phone_to_email", {})

        for cid, profile_data in data.get("customers", {}).items():
            profile = CustomerProfile(
                customer_id=profile_data["customer_id"],
                name=profile_data["name"],
                email=profile_data["email"],
                phone=profile_data.get("phone"),
                topics_discussed=profile_data.get("topics_discussed", []),
                resolution_status=profile_data.get("resolution_status", "pending"),
                current_sentiment=profile_data.get("current_sentiment", "neutral"),
                sentiment_history=profile_data.get("sentiment_history", []),
                original_channel=profile_data.get("original_channel"),
                channels_used=profile_data.get("channels_used", []),
                channel_switches=profile_data.get("channel_switches", 0),
                first_contact=profile_data.get("first_contact"),
                last_contact=profile_data.get("last_contact"),
                total_interactions=profile_data.get("total_interactions", 0),
                escalation_count=profile_data.get("escalation_count", 0)
            )

            # Reconstruct conversation messages
            for msg_data in profile_data.get("conversations", []):
                message = Message(
                    timestamp=msg_data["timestamp"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    channel=msg_data["channel"],
                    sentiment=msg_data.get("sentiment"),
                    escalated=msg_data.get("escalated", False)
                )
                profile.conversations.append(message)

            self.customers[cid] = profile


if __name__ == "__main__":
    # Demo: Test conversation memory
    manager = ConversationManager()

    # Simulate multi-turn conversation
    ticket1 = {
        "ticket_id": "T001",
        "channel": "gmail",
        "timestamp": "2026-04-03T10:00:00Z",
        "customer_name": "Sarah Johnson",
        "customer_email": "sarah@example.com",
        "message": "How do I add team members?",
        "sentiment": "neutral"
    }

    profile = manager.get_or_create_customer(ticket1)
    manager.add_customer_message(profile.customer_id, ticket1)
    manager.add_agent_response(profile.customer_id, "Here's how to add team members...", "gmail", False, "2026-04-03T10:01:00Z")

    # Follow-up on WhatsApp
    ticket2 = {
        "ticket_id": "T002",
        "channel": "whatsapp",
        "timestamp": "2026-04-03T11:00:00Z",
        "customer_name": "Sarah Johnson",
        "customer_email": "sarah@example.com",
        "customer_phone": "+1-555-0123",
        "message": "Thanks! Can I also customize permissions?",
        "sentiment": "positive"
    }

    profile = manager.get_or_create_customer(ticket2)
    manager.add_customer_message(profile.customer_id, ticket2)

    print("Conversation Summary:")
    print(manager.get_conversation_summary(profile.customer_id))

    print("\n\nCustomer Profile:")
    print(f"Name: {profile.name}")
    print(f"Email: {profile.email}")
    print(f"Phone: {profile.phone}")
    print(f"Topics: {profile.topics_discussed}")
    print(f"Channels: {profile.channels_used}")
    print(f"Channel Switches: {profile.channel_switches}")
    print(f"Status: {profile.resolution_status}")
    print(f"Sentiment: {profile.current_sentiment}")
