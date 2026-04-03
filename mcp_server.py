"""
Customer Success AI Agent - MCP Server
Exposes agent functionality as MCP tools for integration with other systems
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

# MCP imports
from mcp.server import Server
from mcp.types import Tool, TextContent

# Import our agent
from agent import CustomerSuccessAgent
from conversation_memory import ConversationManager


class Channel(str, Enum):
    """Supported communication channels"""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


class Priority(str, Enum):
    """Ticket priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    """Ticket status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class Ticket:
    """Ticket data structure"""
    def __init__(self, ticket_id: str, customer_id: str, issue: str,
                 priority: str, channel: str):
        self.ticket_id = ticket_id
        self.customer_id = customer_id
        self.issue = issue
        self.priority = priority
        self.channel = channel
        self.status = TicketStatus.OPEN
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        self.responses: List[Dict] = []
        self.escalation_id: Optional[str] = None
        self.escalation_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "ticket_id": self.ticket_id,
            "customer_id": self.customer_id,
            "issue": self.issue,
            "priority": self.priority,
            "channel": self.channel,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "responses": self.responses,
            "escalation_id": self.escalation_id,
            "escalation_reason": self.escalation_reason
        }


# Initialize server
server = Server("customer-success-agent")

# Global state
agent = CustomerSuccessAgent(enable_memory=True)
tickets: Dict[str, Ticket] = {}
ticket_counter = 0
escalation_counter = 0

# Try to load existing conversation history
history_path = Path("conversation_history.json")
if history_path.exists():
    try:
        agent.load_memory(str(history_path))
        print(f"Loaded conversation history from {history_path}")
    except Exception as e:
        print(f"Warning: Could not load conversation history: {e}")


def convert_to_agent_ticket(ticket: Ticket) -> Dict:
    """Convert MCP ticket to agent ticket format"""

    # Map channel names
    channel_map = {
        "email": "gmail",
        "whatsapp": "whatsapp",
        "web_form": "webform"
    }

    agent_ticket = {
        "ticket_id": ticket.ticket_id,
        "channel": channel_map.get(ticket.channel, ticket.channel),
        "timestamp": ticket.created_at,
        "customer_name": ticket.customer_id.split("@")[0] if "@" in ticket.customer_id else "Customer",
        "message": ticket.issue,
        "sentiment": "neutral",
        "priority": ticket.priority
    }

    # Add email or phone based on customer_id format
    if "@" in ticket.customer_id:
        agent_ticket["customer_email"] = ticket.customer_id
    else:
        agent_ticket["customer_phone"] = ticket.customer_id

    # Add subject for email/webform
    if ticket.channel in ["email", "web_form"]:
        agent_ticket["subject"] = ticket.issue[:50] + "..." if len(ticket.issue) > 50 else ticket.issue

    return agent_ticket


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_knowledge_base",
            description="Search product documentation for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="create_ticket",
            description="Create a support ticket in the system with channel tracking",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer email address or phone number"
                    },
                    "issue": {
                        "type": "string",
                        "description": "Description of the customer's issue"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Ticket priority"
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["email", "whatsapp", "web_form"],
                        "description": "Communication channel"
                    }
                },
                "required": ["customer_id", "issue", "priority", "channel"]
            }
        ),
        Tool(
            name="get_customer_history",
            description="Get customer's interaction history across ALL channels",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer email address or phone number"
                    }
                },
                "required": ["customer_id"]
            }
        ),
        Tool(
            name="escalate_to_human",
            description="Escalate a ticket to human support",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID to escalate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalation"
                    }
                },
                "required": ["ticket_id", "reason"]
            }
        ),
        Tool(
            name="send_response",
            description="Send response via the appropriate channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID to respond to"
                    },
                    "message": {
                        "type": "string",
                        "description": "Response message"
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["email", "whatsapp", "web_form"],
                        "description": "Channel to send through"
                    }
                },
                "required": ["ticket_id", "message", "channel"]
            }
        ),
        Tool(
            name="get_ticket_status",
            description="Get current status and details of a ticket",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID to query"
                    }
                },
                "required": ["ticket_id"]
            }
        ),
        Tool(
            name="get_statistics",
            description="Get overall system statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    global ticket_counter, escalation_counter

    try:
        if name == "search_knowledge_base":
            query = arguments.get("query", "")
            results = agent.doc_retriever.search(query, max_results=5)

            response = {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": [
                    {
                        "content": result[:500] + "..." if len(result) > 500 else result,
                        "relevance": "high" if i == 0 else "medium" if i < 3 else "low"
                    }
                    for i, result in enumerate(results)
                ]
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "create_ticket":
            customer_id = arguments.get("customer_id")
            issue = arguments.get("issue")
            priority = arguments.get("priority")
            channel = arguments.get("channel")

            # Generate ticket ID
            ticket_counter += 1
            ticket_id = f"TICKET-{ticket_counter:06d}"

            # Create ticket
            ticket = Ticket(ticket_id, customer_id, issue, priority, channel)
            tickets[ticket_id] = ticket

            # Process with agent
            agent_ticket = convert_to_agent_ticket(ticket)
            result = agent.process_ticket(agent_ticket)

            # Store agent response
            ticket.responses.append({
                "timestamp": datetime.utcnow().isoformat(),
                "role": "agent",
                "message": result['response'],
                "escalated": result['escalated']
            })

            # Update ticket status
            if result['escalated']:
                ticket.status = TicketStatus.ESCALATED
                ticket.escalation_reason = result['escalation_reason']
            else:
                ticket.status = TicketStatus.IN_PROGRESS

            ticket.updated_at = datetime.utcnow().isoformat()

            # Save conversation history
            agent.save_memory("conversation_history.json")

            response = {
                "success": True,
                "ticket": ticket.to_dict(),
                "agent_response": result['response'],
                "escalated": result['escalated']
            }

            if result['escalated']:
                response["escalation_reason"] = result['escalation_reason']
                response["escalation_priority"] = result['escalation_priority']

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "get_customer_history":
            customer_id = arguments.get("customer_id")

            if not agent.memory_enabled:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": "Memory not enabled"
                }))]

            # Try to find customer
            profile = None
            if customer_id in agent.conversation_manager.customers:
                profile = agent.conversation_manager.customers[customer_id]
            elif customer_id in agent.conversation_manager.phone_to_email:
                email = agent.conversation_manager.phone_to_email[customer_id]
                profile = agent.conversation_manager.customers.get(email)

            if not profile:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Customer not found: {customer_id}"
                }))]

            response = {
                "success": True,
                "customer": {
                    "customer_id": profile.customer_id,
                    "name": profile.name,
                    "email": profile.email,
                    "phone": profile.phone,
                    "first_contact": profile.first_contact,
                    "last_contact": profile.last_contact,
                    "total_interactions": profile.total_interactions
                },
                "conversation_summary": {
                    "topics_discussed": profile.topics_discussed,
                    "resolution_status": profile.resolution_status,
                    "current_sentiment": profile.current_sentiment,
                    "sentiment_history": profile.sentiment_history
                },
                "channel_usage": {
                    "original_channel": profile.original_channel,
                    "channels_used": profile.channels_used,
                    "channel_switches": profile.channel_switches
                },
                "metrics": {
                    "escalation_count": profile.escalation_count,
                    "conversation_length": len(profile.conversations)
                },
                "conversations": [
                    {
                        "timestamp": msg.timestamp,
                        "role": msg.role,
                        "content": msg.content,
                        "channel": msg.channel,
                        "sentiment": msg.sentiment,
                        "escalated": msg.escalated
                    }
                    for msg in profile.conversations
                ]
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "escalate_to_human":
            ticket_id = arguments.get("ticket_id")
            reason = arguments.get("reason")

            if ticket_id not in tickets:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Ticket not found: {ticket_id}"
                }))]

            ticket = tickets[ticket_id]

            # Generate escalation ID
            escalation_counter += 1
            escalation_id = f"ESC-{escalation_counter:06d}"

            # Update ticket
            ticket.status = TicketStatus.ESCALATED
            ticket.escalation_id = escalation_id
            ticket.escalation_reason = reason
            ticket.updated_at = datetime.utcnow().isoformat()

            ticket.responses.append({
                "timestamp": datetime.utcnow().isoformat(),
                "role": "system",
                "message": f"Ticket escalated to human support. Reason: {reason}",
                "escalated": True
            })

            response = {
                "success": True,
                "escalation_id": escalation_id,
                "ticket_id": ticket_id,
                "reason": reason,
                "escalated_at": ticket.updated_at,
                "ticket_status": ticket.status,
                "customer_id": ticket.customer_id
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "send_response":
            ticket_id = arguments.get("ticket_id")
            message = arguments.get("message")
            channel = arguments.get("channel")

            if ticket_id not in tickets:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Ticket not found: {ticket_id}"
                }))]

            ticket = tickets[ticket_id]

            ticket.responses.append({
                "timestamp": datetime.utcnow().isoformat(),
                "role": "agent",
                "message": message,
                "channel": channel,
                "escalated": False
            })

            ticket.updated_at = datetime.utcnow().isoformat()

            delivery_status = {
                "delivered": True,
                "channel": channel,
                "delivered_at": datetime.utcnow().isoformat()
            }

            response = {
                "success": True,
                "ticket_id": ticket_id,
                "message_sent": message[:100] + "..." if len(message) > 100 else message,
                "delivery_status": delivery_status,
                "ticket_status": ticket.status
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "get_ticket_status":
            ticket_id = arguments.get("ticket_id")

            if ticket_id not in tickets:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Ticket not found: {ticket_id}"
                }))]

            ticket = tickets[ticket_id]

            response = {
                "success": True,
                "ticket": ticket.to_dict()
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "get_statistics":
            customer_stats = agent.get_customer_stats() if agent.memory_enabled else {}

            ticket_stats = {
                "total_tickets": len(tickets),
                "by_status": {},
                "by_priority": {},
                "by_channel": {}
            }

            for ticket in tickets.values():
                status = ticket.status
                ticket_stats["by_status"][status] = ticket_stats["by_status"].get(status, 0) + 1

                priority = ticket.priority
                ticket_stats["by_priority"][priority] = ticket_stats["by_priority"].get(priority, 0) + 1

                channel = ticket.channel
                ticket_stats["by_channel"][channel] = ticket_stats["by_channel"].get(channel, 0) + 1

            response = {
                "success": True,
                "customer_statistics": customer_stats,
                "ticket_statistics": ticket_stats,
                "escalations": {
                    "total": escalation_counter
                }
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Unknown tool: {name}"
            }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


def main():
    """Main entry point"""
    print("Starting Customer Success AI Agent MCP Server...")
    print(f"Memory enabled: {agent.memory_enabled}")
    print(f"Loaded customers: {len(agent.conversation_manager.customers) if agent.memory_enabled else 0}")
    print("\nAvailable tools:")
    print("  - search_knowledge_base(query)")
    print("  - create_ticket(customer_id, issue, priority, channel)")
    print("  - get_customer_history(customer_id)")
    print("  - escalate_to_human(ticket_id, reason)")
    print("  - send_response(ticket_id, message, channel)")
    print("  - get_ticket_status(ticket_id)")
    print("  - get_statistics()")
    print("\nServer running...")

    server.run()


if __name__ == "__main__":
    main()
