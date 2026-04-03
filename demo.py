"""
Quick demo script for the Customer Success AI Agent
"""

from agent import CustomerSuccessAgent

def demo():
    """Run a quick demo with diverse examples"""

    agent = CustomerSuccessAgent()

    # Test cases showing different scenarios
    test_cases = [
        {
            "name": "Simple How-To (Gmail)",
            "ticket": {
                "ticket_id": "DEMO-001",
                "channel": "gmail",
                "timestamp": "2026-04-03T10:00:00Z",
                "customer_name": "Alex Thompson",
                "customer_email": "alex@startup.com",
                "subject": "How do I export my data?",
                "message": "We're evaluating different tools and want to export our data to test migration. Where can I find the export option?",
                "sentiment": "neutral",
                "priority": "low"
            }
        },
        {
            "name": "Quick Question (WhatsApp)",
            "ticket": {
                "ticket_id": "DEMO-002",
                "channel": "whatsapp",
                "timestamp": "2026-04-03T10:05:00Z",
                "customer_name": "Maria Garcia",
                "customer_phone": "+1-555-0789",
                "message": "Does the app work on iPad?",
                "sentiment": "neutral",
                "priority": "low"
            }
        },
        {
            "name": "Escalation - Refund (Web Form)",
            "ticket": {
                "ticket_id": "DEMO-003",
                "channel": "webform",
                "timestamp": "2026-04-03T10:10:00Z",
                "customer_name": "David Kim",
                "customer_email": "david@company.com",
                "subject": "Refund request",
                "message": "We've been using TaskFlow for 2 months but it doesn't have the features we need. We're switching to a competitor. Can we get a refund for the remaining 10 months of our annual subscription?",
                "sentiment": "disappointed",
                "priority": "high"
            }
        }
    ]

    print("=" * 80)
    print("CUSTOMER SUCCESS AI AGENT - QUICK DEMO")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"DEMO {i}: {test['name']}")
        print(f"{'='*80}")

        ticket = test['ticket']
        print(f"\nChannel: {ticket['channel'].upper()}")
        print(f"Customer: {ticket['customer_name']}")
        print(f"Message: {ticket['message']}")

        result = agent.process_ticket(ticket)

        print(f"\n--- AGENT DECISION ---")
        print(f"Escalated: {'YES' if result['escalated'] else 'NO'}")
        if result['escalated']:
            print(f"Reason: {result['escalation_reason']}")
            print(f"Priority: {result['escalation_priority'].upper()}")

        print(f"\n--- RESPONSE ---")
        print(result['response'])

    print(f"\n{'='*80}")
    print("DEMO COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    demo()
