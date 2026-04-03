"""
TechCorp SaaS - Customer Success AI Agent
Stage 1: Core Interaction Loop Prototype
Extended with Conversation Memory
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Import conversation memory
try:
    from conversation_memory import ConversationManager, TopicExtractor
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("Warning: conversation_memory module not found. Running without memory.")


@dataclass
class Ticket:
    """Unified ticket format across all channels"""
    ticket_id: str
    channel: str  # gmail, whatsapp, webform
    timestamp: str
    customer_name: str
    customer_contact: str  # email or phone
    subject: Optional[str]
    message: str
    sentiment: str = "neutral"
    priority: str = "low"

    def to_dict(self) -> Dict:
        return {
            "ticket_id": self.ticket_id,
            "channel": self.channel,
            "timestamp": self.timestamp,
            "customer_name": self.customer_name,
            "customer_contact": self.customer_contact,
            "subject": self.subject,
            "message": self.message,
            "sentiment": self.sentiment,
            "priority": self.priority
        }


class DocumentRetriever:
    """Simple document retrieval from product docs"""

    def __init__(self, docs_path: str):
        self.docs_path = Path(docs_path)
        self.content = self._load_docs()

    def _load_docs(self) -> str:
        """Load product documentation"""
        if self.docs_path.exists():
            return self.docs_path.read_text(encoding='utf-8')
        return ""

    def search(self, query: str, max_results: int = 3) -> List[str]:
        """
        Improved keyword-based search for relevant documentation sections.
        Returns relevant passages from the docs.
        """
        if not self.content:
            return []

        # Split into sections (by headers and Q&A blocks)
        sections = []

        # Split by major headers first
        major_sections = re.split(r'\n#{1,2}\s+', self.content)

        for major_section in major_sections:
            # Further split by Q&A patterns
            qa_blocks = re.split(r'\n\*\*Q:', major_section)
            for block in qa_blocks:
                if len(block.strip()) > 50:
                    sections.append(block.strip())

        # Enhanced keyword extraction
        query_lower = query.lower()
        query_keywords = set(query_lower.split())

        # Add important phrases
        important_phrases = []
        if "add" in query_lower and "member" in query_lower:
            important_phrases.append("add members")
        if "crash" in query_lower or "crashing" in query_lower:
            important_phrases.append("app crashes")
        if "export" in query_lower:
            important_phrases.append("export")
        if "offline" in query_lower:
            important_phrases.append("offline")

        scored_sections = []

        for section in sections:
            section_lower = section.lower()

            # Base score from keyword overlap
            score = sum(1 for keyword in query_keywords if keyword in section_lower)

            # Bonus for important phrases
            for phrase in important_phrases:
                if phrase in section_lower:
                    score += 5

            # Bonus for exact question match
            if "?" in section and any(keyword in section_lower for keyword in query_keywords):
                score += 2

            if score > 0:
                scored_sections.append((score, section[:600]))

        # Sort by score and return top results
        scored_sections.sort(reverse=True, key=lambda x: x[0])
        return [section for _, section in scored_sections[:max_results]]


class EscalationEngine:
    """Determines if a ticket should be escalated to human support"""

    def __init__(self, rules_path: str):
        self.rules_path = Path(rules_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """Load escalation rules from markdown file"""
        if not self.rules_path.exists():
            return {}

        # Define escalation triggers based on escalation-rules.md
        return {
            "legal_keywords": ["lawyer", "legal action", "sue", "attorney", "court", "gdpr", "article 17"],
            "angry_keywords": ["unacceptable", "terrible", "worst", "horrible", "disgusting", "fraudulent"],
            "refund_keywords": ["refund", "money back"],
            "enterprise_keywords": ["enterprise", "sso", "saml", "150 users", "custom quote"],
            "compliance_keywords": ["soc 2", "dpa", "compliance", "audit", "security certification"],
            "billing_dispute_keywords": ["charged twice", "wrong amount", "billing error", "overcharged"],
            "threat_keywords": ["canceling", "switching to competitor", "telling everyone", "social media"],
            "security_keywords": ["unauthorized access", "breach", "locked account", "suspicious activity"]
        }

    def analyze(self, ticket: Ticket) -> Tuple[bool, str, str]:
        """
        Analyze ticket for escalation triggers.
        Returns: (should_escalate, reason, escalation_priority)
        """
        message_lower = ticket.message.lower()
        subject_lower = (ticket.subject or "").lower()
        combined = f"{message_lower} {subject_lower}"

        # Check for critical escalations
        if any(keyword in combined for keyword in self.rules["legal_keywords"]):
            return True, "Legal matter detected", "critical"

        if ticket.sentiment in ["angry", "critical"]:
            return True, "Negative sentiment - angry customer", "critical"

        if any(keyword in combined for keyword in self.rules["security_keywords"]):
            if "urgent" in combined or "client presentation" in combined:
                return True, "Security issue with urgency", "high"

        # Check for high priority escalations
        if any(keyword in combined for keyword in self.rules["billing_dispute_keywords"]):
            return True, "Billing dispute", "high"

        # Billing confusion that needs clarification
        if "charged" in combined and ("confused" in ticket.sentiment or "?" in ticket.message):
            if any(word in combined for word in ["why", "explain", "don't understand", "thought"]):
                return True, "Billing confusion requiring explanation", "high"

        if any(keyword in combined for keyword in self.rules["refund_keywords"]):
            if "annual" in combined or "months" in combined:
                return True, "Refund request for long-term subscription", "high"
            return True, "Refund request", "high"

        if any(keyword in combined for keyword in self.rules["enterprise_keywords"]):
            return True, "Enterprise customer inquiry", "high"

        if any(keyword in combined for keyword in self.rules["compliance_keywords"]):
            return True, "Compliance/security documentation request", "high"

        # Check for medium priority escalations
        if any(keyword in combined for keyword in self.rules["threat_keywords"]):
            return True, "Customer threatening to cancel/complain", "medium"

        # No escalation needed
        return False, "AI can handle", "n/a"


class ResponseGenerator:
    """Generates customer responses using product documentation"""

    def __init__(self, brand_voice_path: str, conversation_manager=None):
        self.brand_voice_path = Path(brand_voice_path)
        self.voice_guidelines = self._load_voice_guidelines()
        self.conversation_manager = conversation_manager

    def _load_voice_guidelines(self) -> Dict[str, str]:
        """Load brand voice guidelines for each channel"""
        # Simplified guidelines extracted from brand-voice.md
        return {
            "gmail": "formal, professional, detailed with step-by-step instructions",
            "whatsapp": "concise, friendly, conversational - 2-4 sentences max",
            "webform": "semi-formal, balanced, helpful with clear next steps"
        }

    def generate(self, ticket: Ticket, relevant_docs: List[str], escalate: bool,
                 escalation_reason: str, conversation_context: str = "") -> str:
        """
        Generate response based on ticket, documentation, escalation decision, and conversation context.
        For prototype, using template-based generation.
        In production, this would call Claude API.
        """
        if escalate:
            return self._generate_escalation_response(ticket, escalation_reason, conversation_context)

        return self._generate_ai_response(ticket, relevant_docs, conversation_context)

    def _generate_escalation_response(self, ticket: Ticket, reason: str, conversation_context: str = "") -> str:
        """Generate escalation notification response"""
        channel = ticket.channel
        name = ticket.customer_name.split()[0]  # First name

        # Check if this is a follow-up
        is_followup = "Previous conversation:" in conversation_context

        if channel == "gmail":
            return f"""Hi {name},

Thank you for reaching out. I understand this is an important matter that requires specialized attention.

I've escalated your inquiry to our support team. A specialist will respond within the appropriate timeframe via email with a solution.

We appreciate your patience.

Best regards,
TechCorp Support Team"""

        elif channel == "whatsapp":
            return f"Hi {name}! I'm connecting you with our support team for this. You'll hear back soon with a solution."

        else:  # webform
            return f"""Hi {name},

Thanks for reaching out. I've escalated your inquiry to our support team who can best assist with this matter.

A specialist will respond shortly via email.

Best,
TechCorp Support"""

    def _generate_ai_response(self, ticket: Ticket, relevant_docs: List[str], conversation_context: str = "") -> str:
        """
        Generate AI response using documentation and conversation context.
        This is a simplified template-based approach for the prototype.
        """
        channel = ticket.channel
        name = ticket.customer_name.split()[0]
        message_lower = ticket.message.lower()

        # Check if this is a follow-up question
        is_followup = "Previous conversation:" in conversation_context

        # Detect follow-up patterns
        followup_indicators = ["also", "and", "what about", "can i also", "thanks", "thank you",
                              "got it", "ok", "one more", "another question"]
        is_followup = is_followup or any(indicator in message_lower for indicator in followup_indicators)

        # Simple intent detection for common questions
        response_content = self._match_common_questions(message_lower, relevant_docs)

        if not response_content:
            # Fallback: use document snippets if available
            if relevant_docs:
                response_content = "Based on our documentation, here's what might help:\n\n" + relevant_docs[0][:300] + "..."
            else:
                response_content = "I'd be happy to help with your question. Let me connect you with our support team who can provide detailed assistance."

        # Format according to channel
        return self._format_response(channel, name, response_content, is_followup)

    def _match_common_questions(self, message: str, docs: List[str]) -> Optional[str]:
        """Match common question patterns and generate appropriate responses"""

        # Add team members
        if ("add" in message and "member" in message) or "add" in message and "team" in message:
            return """Here's how to add team members to your project:

1. Open your project in TaskFlow Pro
2. Click the "Team" icon in the top right corner
3. Click "Add Members"
4. Enter email addresses or select from your workspace members
5. Choose their permission level (Viewer, Editor, or Admin)
6. Click "Send Invitations"

Your team members will receive an email invitation and can access the project immediately."""

        # App crashing
        if "crash" in message or "crashing" in message:
            return """Try these steps to fix app crashes:

1. Update to the latest version from the App Store
2. Restart your device
3. Clear app cache (Settings > Apps > TaskFlow Pro > Clear Cache)
4. Reinstall the app if the issue persists

If crashes continue after these steps, let me know and I'll escalate to our technical team."""

        # Export data
        if "export" in message and "data" in message:
            return """You can export your data by going to Settings > Data Export. Choose your preferred format (CSV, JSON, or PDF) and select the date range. The export will be emailed to you within 24 hours."""

        # Offline mode
        if "offline" in message:
            return """Yes! The mobile app supports offline mode. You can work on tasks without internet, and changes will sync automatically when you reconnect. Note that the browser version requires an internet connection."""

        # Customize workflow
        if "customize" in message and ("workflow" in message or "stages" in message):
            return """Yes, you can customize workflow stages! Go to Project Settings > Workflow and you can add, edit, or reorder stages to match your team's process."""

        # Projects limit
        if "how many project" in message or "project limit" in message:
            return """You can create unlimited projects on all plans, including the Starter plan."""

        # Billing - upgrade
        if "upgrade" in message and ("mid-month" in message or "billing" in message or "how does" in message):
            return """Yes, you can upgrade from Starter to Professional anytime. You'll be charged the prorated difference for the current month, then the full Professional rate starting next month. All charges are automatic."""

        # 2FA
        if "2fa" in message or "two-factor" in message or "two factor" in message:
            return """You can enable 2FA in Settings > Security. We support authenticator apps (Google Authenticator, Authy) and SMS. For workspace-wide settings, admins can make it mandatory or optional for users."""

        # Multiple devices
        if "multiple device" in message:
            return """Yes! You can use TaskFlow on multiple devices with one account. Your data syncs automatically across all devices."""

        # iPad support
        if "ipad" in message:
            return """Yes, the TaskFlow mobile app works on iPad! Download it from the App Store."""

        # Delete project
        if "delete project" in message:
            return """To delete a project, open the project, click the Settings icon (gear), scroll to the bottom, and click "Delete Project". You'll be asked to confirm."""

        # Password reset
        if "password" in message and ("reset" in message or "forgot" in message):
            return """If the password reset link isn't working, try these steps:

1. Check your spam/junk folder for the reset email
2. Make sure you're using the correct email address
3. Try requesting a new reset link
4. Clear your browser cache and try again

If you still can't reset your password, I can escalate this to get your account unlocked immediately."""

        # Slack integration
        if "slack" in message and ("integration" in message or "not working" in message or "notifications" in message):
            return """For Slack integration issues, try these steps:

1. Go to Settings > Integrations > Slack > Reconnect
2. Verify the bot is added to your Slack channels
3. Check that you have proper permissions in Slack
4. Re-authorize the integration if permissions changed

If notifications still aren't coming through after reconnecting, I'll escalate this to our integrations team."""

        return None

    def _format_response(self, channel: str, name: str, content: str, is_followup: bool = False) -> str:
        """Format response according to channel guidelines"""

        if channel == "gmail":
            greeting = "Thanks for following up!" if is_followup else "Thanks for reaching out! I'd be happy to help."
            return f"""Hi {name},

{greeting}

{content}

Is there anything else I can help you with?

Best regards,
TechCorp Support Team"""

        elif channel == "whatsapp":
            # Condense for WhatsApp
            lines = content.split('\n')
            condensed = ' '.join(line.strip() for line in lines if line.strip())
            # Limit to ~200 chars for WhatsApp
            if len(condensed) > 200:
                condensed = condensed[:197] + "..."

            greeting = "Hi" if not is_followup else "Sure"
            return f"{greeting} {name}! {condensed}"

        else:  # webform
            greeting = "Thanks for the follow-up!" if is_followup else "Thanks for reaching out!"
            return f"""Hi {name},

{greeting}

{content}

Let me know if you need any clarification.

Best,
TechCorp Support"""


class CustomerSuccessAgent:
    """Main agent orchestrating the customer interaction loop with conversation memory"""

    def __init__(self, context_dir: str = "context", enable_memory: bool = True):
        self.context_dir = Path(context_dir)
        self.doc_retriever = DocumentRetriever(self.context_dir / "product-docs.md")
        self.escalation_engine = EscalationEngine(self.context_dir / "escalation-rules.md")

        # Initialize conversation memory
        self.memory_enabled = enable_memory and MEMORY_AVAILABLE
        if self.memory_enabled:
            self.conversation_manager = ConversationManager()
        else:
            self.conversation_manager = None

        self.response_generator = ResponseGenerator(
            self.context_dir / "brand-voice.md",
            conversation_manager=self.conversation_manager
        )

    def normalize_ticket(self, raw_ticket: Dict) -> Ticket:
        """Normalize ticket from any channel into unified format"""
        channel = raw_ticket.get("channel")

        # Extract contact info based on channel
        if channel == "whatsapp":
            contact = raw_ticket.get("customer_phone", "")
        else:
            contact = raw_ticket.get("customer_email", "")

        return Ticket(
            ticket_id=raw_ticket.get("ticket_id", ""),
            channel=channel,
            timestamp=raw_ticket.get("timestamp", ""),
            customer_name=raw_ticket.get("customer_name", ""),
            customer_contact=contact,
            subject=raw_ticket.get("subject"),
            message=raw_ticket.get("message", ""),
            sentiment=raw_ticket.get("sentiment", "neutral"),
            priority=raw_ticket.get("priority", "low")
        )

    def process_ticket(self, raw_ticket: Dict) -> Dict:
        """
        Main processing loop for a customer ticket with conversation memory.
        Returns response and metadata.
        """
        # Step 1: Normalize
        ticket = self.normalize_ticket(raw_ticket)

        # Step 2: Get or create customer profile and conversation context
        conversation_context = ""
        customer_profile = None

        if self.memory_enabled:
            customer_profile = self.conversation_manager.get_or_create_customer(raw_ticket)
            conversation_context = self.conversation_manager.get_conversation_summary(customer_profile.customer_id)

            # Add customer message to history
            self.conversation_manager.add_customer_message(customer_profile.customer_id, raw_ticket)

        # Step 3: Search documentation (include conversation context in search)
        search_query = ticket.message
        if conversation_context:
            # Enhance search with conversation topics
            if customer_profile and customer_profile.topics_discussed:
                search_query += " " + " ".join(customer_profile.topics_discussed)

        relevant_docs = self.doc_retriever.search(search_query)

        # Step 4: Check escalation
        should_escalate, escalation_reason, escalation_priority = self.escalation_engine.analyze(ticket)

        # Step 5: Generate response with conversation context
        response = self.response_generator.generate(
            ticket,
            relevant_docs,
            should_escalate,
            escalation_reason,
            conversation_context
        )

        # Step 6: Update conversation memory
        if self.memory_enabled:
            self.conversation_manager.add_agent_response(
                customer_profile.customer_id,
                response,
                ticket.channel,
                should_escalate,
                ticket.timestamp
            )

        # Step 7: Return result with enhanced metadata
        result = {
            "ticket": ticket.to_dict(),
            "response": response,
            "escalated": should_escalate,
            "escalation_reason": escalation_reason,
            "escalation_priority": escalation_priority if should_escalate else None,
            "relevant_docs_count": len(relevant_docs),
            "processed_at": datetime.utcnow().isoformat()
        }

        # Add customer profile data if memory is enabled
        if self.memory_enabled and customer_profile:
            result["customer_profile"] = {
                "customer_id": customer_profile.customer_id,
                "topics_discussed": customer_profile.topics_discussed,
                "resolution_status": customer_profile.resolution_status,
                "current_sentiment": customer_profile.current_sentiment,
                "channels_used": customer_profile.channels_used,
                "channel_switches": customer_profile.channel_switches,
                "total_interactions": customer_profile.total_interactions,
                "conversation_length": len(customer_profile.conversations)
            }

        return result

    def get_customer_stats(self) -> Dict:
        """Get overall customer statistics"""
        if self.memory_enabled:
            return self.conversation_manager.get_customer_stats()
        return {}

    def save_memory(self, filepath: str):
        """Save conversation memory to file"""
        if self.memory_enabled:
            self.conversation_manager.save_to_file(filepath)

    def load_memory(self, filepath: str):
        """Load conversation memory from file"""
        if self.memory_enabled:
            self.conversation_manager.load_from_file(filepath)


def main():
    """Demo: Process sample tickets"""

    # Initialize agent
    agent = CustomerSuccessAgent()

    # Load sample tickets
    with open("context/sample-tickets.json", "r", encoding="utf-8") as f:
        sample_tickets = json.load(f)

    # Process diverse set of tickets to show different scenarios
    # T001: How-to question (Gmail)
    # T002: Technical issue (WhatsApp)
    # T003: Billing confusion (Web form)
    # T005: Refund request (WhatsApp) - should escalate
    # T010: Legal threat (Gmail) - should escalate
    # T011: Positive + simple question (WhatsApp)
    # T024: Angry customer (Web form) - should escalate
    test_indices = [0, 1, 2, 4, 9, 10, 23]

    print("=" * 80)
    print("TechCorp SaaS - Customer Success AI Agent")
    print("Processing Sample Tickets (Diverse Scenarios)...")
    print("=" * 80)

    for idx in test_indices:
        ticket = sample_tickets[idx]
        print(f"\n{'='*80}")
        print(f"TICKET: {ticket['ticket_id']} ({ticket['channel'].upper()})")
        print(f"{'='*80}")
        print(f"From: {ticket['customer_name']}")
        print(f"Subject: {ticket.get('subject', 'N/A')}")
        print(f"Message: {ticket['message']}")
        print(f"Sentiment: {ticket['sentiment']}")
        print(f"\nProcessing...")

        result = agent.process_ticket(ticket)

        print(f"\n--- ANALYSIS ---")
        print(f"Escalated: {'YES [!]' if result['escalated'] else 'NO'}")
        print(f"Reason: {result['escalation_reason']}")
        if result['escalated']:
            print(f"Priority: {result['escalation_priority'].upper()}")
        print(f"Docs Retrieved: {result['relevant_docs_count']} sections")

        print(f"\n--- RESPONSE ({ticket['channel'].upper()}) ---")
        print(result['response'])
        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
