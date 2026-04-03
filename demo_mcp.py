"""
MCP Server Demo - Customer Success AI Agent
Demonstrates all available MCP tools
"""

import asyncio
import json
from mcp_server import CustomerSuccessMCPServer


async def demo_mcp_tools():
    """Demonstrate all MCP tools"""

    print("=" * 80)
    print("CUSTOMER SUCCESS AI AGENT - MCP SERVER DEMO")
    print("=" * 80)

    # Initialize server
    server = CustomerSuccessMCPServer()

    # ========================================================================
    # TOOL 1: search_knowledge_base
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 1: search_knowledge_base")
    print("=" * 80)

    print("\nSearching for: 'how to add team members'")
    result = await server.server._tool_handlers["search_knowledge_base"]("how to add team members")
    data = json.loads(result)

    print(f"\nResults found: {data['results_count']}")
    if data['success'] and data['results']:
        print(f"\nTop result (relevance: {data['results'][0]['relevance']}):")
        print(data['results'][0]['content'][:200] + "...")

    # ========================================================================
    # TOOL 2: create_ticket
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 2: create_ticket")
    print("=" * 80)

    print("\nCreating ticket for customer: sarah@example.com")
    result = await server.server._tool_handlers["create_ticket"](
        customer_id="sarah@example.com",
        issue="I can't add team members to my project. Where is the option?",
        priority="low",
        channel="email"
    )
    data = json.loads(result)

    if data['success']:
        ticket_id_1 = data['ticket']['ticket_id']
        print(f"\n✓ Ticket created: {ticket_id_1}")
        print(f"  Status: {data['ticket']['status']}")
        print(f"  Escalated: {data['escalated']}")
        print(f"\n  Agent Response Preview:")
        print(f"  {data['agent_response'][:150]}...")

    # ========================================================================
    # TOOL 3: Create another ticket (cross-channel scenario)
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 2: create_ticket (Cross-Channel Scenario)")
    print("=" * 80)

    print("\nCreating ticket via WhatsApp: +1-555-0123")
    result = await server.server._tool_handlers["create_ticket"](
        customer_id="+1-555-0123",
        issue="App keeps crashing when I upload files",
        priority="medium",
        channel="whatsapp"
    )
    data = json.loads(result)

    if data['success']:
        ticket_id_2 = data['ticket']['ticket_id']
        print(f"\n✓ Ticket created: {ticket_id_2}")
        print(f"  Status: {data['ticket']['status']}")

    # Now same customer via email
    print("\nSame customer follows up via email: mike@example.com")
    result = await server.server._tool_handlers["create_ticket"](
        customer_id="mike@example.com",
        issue="I messaged on WhatsApp about app crashes. Still not working after trying your steps.",
        priority="high",
        channel="email"
    )
    data = json.loads(result)

    if data['success']:
        ticket_id_3 = data['ticket']['ticket_id']
        print(f"\n✓ Ticket created: {ticket_id_3}")
        print(f"  Status: {data['ticket']['status']}")
        print(f"  Escalated: {data['escalated']}")
        if data['escalated']:
            print(f"  Escalation Reason: {data['escalation_reason']}")

    # ========================================================================
    # TOOL 4: get_customer_history
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 3: get_customer_history")
    print("=" * 80)

    print("\nGetting history for: sarah@example.com")
    result = await server.server._tool_handlers["get_customer_history"]("sarah@example.com")
    data = json.loads(result)

    if data['success']:
        customer = data['customer']
        print(f"\n✓ Customer Profile:")
        print(f"  Name: {customer['name']}")
        print(f"  Email: {customer['email']}")
        print(f"  Total Interactions: {customer['total_interactions']}")

        summary = data['conversation_summary']
        print(f"\n  Conversation Summary:")
        print(f"    Topics: {', '.join(summary['topics_discussed'])}")
        print(f"    Status: {summary['resolution_status']}")
        print(f"    Sentiment: {summary['current_sentiment']}")

        channels = data['channel_usage']
        print(f"\n  Channel Usage:")
        print(f"    Original: {channels['original_channel']}")
        print(f"    Used: {', '.join(channels['channels_used'])}")
        print(f"    Switches: {channels['channel_switches']}")

        print(f"\n  Conversation History ({len(data['conversations'])} messages):")
        for msg in data['conversations'][:4]:  # Show first 4 messages
            role = msg['role'].upper()
            content = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
            print(f"    [{role}] {content}")

    # ========================================================================
    # TOOL 5: get_ticket_status
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 4: get_ticket_status")
    print("=" * 80)

    print(f"\nGetting status for ticket: {ticket_id_1}")
    result = await server.server._tool_handlers["get_ticket_status"](ticket_id_1)
    data = json.loads(result)

    if data['success']:
        ticket = data['ticket']
        print(f"\n✓ Ticket Status:")
        print(f"  ID: {ticket['ticket_id']}")
        print(f"  Customer: {ticket['customer_id']}")
        print(f"  Status: {ticket['status']}")
        print(f"  Priority: {ticket['priority']}")
        print(f"  Channel: {ticket['channel']}")
        print(f"  Created: {ticket['created_at']}")
        print(f"  Responses: {len(ticket['responses'])}")

    # ========================================================================
    # TOOL 6: send_response
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 5: send_response")
    print("=" * 80)

    print(f"\nSending follow-up response to ticket: {ticket_id_1}")
    result = await server.server._tool_handlers["send_response"](
        ticket_id=ticket_id_1,
        message="Just following up - were you able to add your team members successfully? Let me know if you need any additional help!",
        channel="email"
    )
    data = json.loads(result)

    if data['success']:
        print(f"\n✓ Response sent:")
        print(f"  Ticket: {data['ticket_id']}")
        print(f"  Channel: {data['delivery_status']['channel']}")
        print(f"  Delivered: {data['delivery_status']['delivered']}")
        print(f"  Message: {data['message_sent']}")

    # ========================================================================
    # TOOL 7: escalate_to_human
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 6: escalate_to_human")
    print("=" * 80)

    # Create a ticket that needs escalation
    print("\nCreating ticket that needs escalation...")
    result = await server.server._tool_handlers["create_ticket"](
        customer_id="angry@customer.com",
        issue="I've been charged twice this month and no one is responding to my emails. This is unacceptable!",
        priority="critical",
        channel="email"
    )
    data = json.loads(result)

    if data['success']:
        ticket_id_4 = data['ticket']['ticket_id']
        print(f"✓ Ticket created: {ticket_id_4}")

        # Manually escalate
        print(f"\nEscalating ticket {ticket_id_4} to human support...")
        result = await server.server._tool_handlers["escalate_to_human"](
            ticket_id=ticket_id_4,
            reason="Customer is very upset about billing issue - requires immediate human attention"
        )
        data = json.loads(result)

        if data['success']:
            print(f"\n✓ Escalation created:")
            print(f"  Escalation ID: {data['escalation_id']}")
            print(f"  Ticket ID: {data['ticket_id']}")
            print(f"  Reason: {data['reason']}")
            print(f"  Status: {data['ticket_status']}")

    # ========================================================================
    # TOOL 8: get_statistics
    # ========================================================================
    print("\n" + "=" * 80)
    print("TOOL 7: get_statistics")
    print("=" * 80)

    print("\nGetting overall system statistics...")
    result = await server.server._tool_handlers["get_statistics"]()
    data = json.loads(result)

    if data['success']:
        print("\n✓ System Statistics:")

        # Customer stats
        if data['customer_statistics']:
            cust_stats = data['customer_statistics']
            print(f"\n  Customers:")
            print(f"    Total: {cust_stats.get('total_customers', 0)}")
            print(f"    Multi-channel: {cust_stats.get('multi_channel_customers', 0)}")
            print(f"    Total interactions: {cust_stats.get('total_interactions', 0)}")

            if cust_stats.get('topics'):
                print(f"\n  Top Topics:")
                sorted_topics = sorted(cust_stats['topics'].items(), key=lambda x: x[1], reverse=True)
                for topic, count in sorted_topics[:5]:
                    print(f"    {topic}: {count}")

        # Ticket stats
        ticket_stats = data['ticket_statistics']
        print(f"\n  Tickets:")
        print(f"    Total: {ticket_stats['total_tickets']}")

        if ticket_stats['by_status']:
            print(f"\n    By Status:")
            for status, count in ticket_stats['by_status'].items():
                print(f"      {status}: {count}")

        if ticket_stats['by_priority']:
            print(f"\n    By Priority:")
            for priority, count in ticket_stats['by_priority'].items():
                print(f"      {priority}: {count}")

        if ticket_stats['by_channel']:
            print(f"\n    By Channel:")
            for channel, count in ticket_stats['by_channel'].items():
                print(f"      {channel}: {count}")

        print(f"\n  Escalations:")
        print(f"    Total: {data['escalations']['total']}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)

    print("\n✓ All 7 MCP tools demonstrated:")
    print("  1. search_knowledge_base - Search product documentation")
    print("  2. create_ticket - Create support tickets with channel tracking")
    print("  3. get_customer_history - Get complete customer interaction history")
    print("  4. get_ticket_status - Get current ticket status")
    print("  5. send_response - Send responses via appropriate channel")
    print("  6. escalate_to_human - Escalate tickets to human support")
    print("  7. get_statistics - Get overall system statistics")

    print("\n✓ Key features demonstrated:")
    print("  - Cross-channel customer recognition")
    print("  - Conversation memory and context")
    print("  - Automatic escalation detection")
    print("  - Topic extraction and tracking")
    print("  - Sentiment monitoring")
    print("  - Multi-channel support (email, WhatsApp, web form)")

    print("\n" + "=" * 80)


async def main():
    """Run the demo"""
    await demo_mcp_tools()


if __name__ == "__main__":
    asyncio.run(main())
