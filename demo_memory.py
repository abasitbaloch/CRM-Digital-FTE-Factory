"""
Conversation Memory Demo
Demonstrates multi-turn conversations with channel switching
"""

from agent import CustomerSuccessAgent
from datetime import datetime, timedelta
import json


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_customer_profile(agent, customer_id):
    """Print customer profile details"""
    if not agent.memory_enabled:
        print("Memory not enabled")
        return

    profile = agent.conversation_manager.customers.get(customer_id)
    if not profile:
        print(f"No profile found for {customer_id}")
        return

    print(f"\nCustomer ID: {profile.customer_id}")
    print(f"Name: {profile.name}")
    print(f"Email: {profile.email}")
    print(f"Phone: {profile.phone or 'N/A'}")
    print(f"\nTopics Discussed: {', '.join(profile.topics_discussed)}")
    print(f"Resolution Status: {profile.resolution_status}")
    print(f"Current Sentiment: {profile.current_sentiment}")
    print(f"\nOriginal Channel: {profile.original_channel}")
    print(f"Channels Used: {', '.join(profile.channels_used)}")
    print(f"Channel Switches: {profile.channel_switches}")
    print(f"\nTotal Interactions: {profile.total_interactions}")
    print(f"Escalations: {profile.escalation_count}")
    print(f"Conversation Length: {len(profile.conversations)} messages")


def demo_scenario_1():
    """
    Scenario 1: Simple multi-turn conversation on same channel
    Customer asks about adding team members, then follows up about permissions
    """
    print_section("SCENARIO 1: Multi-Turn Conversation (Same Channel)")

    agent = CustomerSuccessAgent(enable_memory=True)

    # Turn 1: Initial question via Gmail
    ticket1 = {
        "ticket_id": "DEMO-001",
        "channel": "gmail",
        "timestamp": "2026-04-03T10:00:00Z",
        "customer_name": "Sarah Johnson",
        "customer_email": "sarah@acmecorp.com",
        "subject": "How do I add team members?",
        "message": "Hi, I just signed up for the Professional plan and I'm trying to add my team members to a project. I can't seem to find the option. Can you help?",
        "sentiment": "neutral",
        "priority": "low"
    }

    print("\n--- TURN 1: Initial Question (Gmail) ---")
    print(f"Customer: {ticket1['message']}")

    result1 = agent.process_ticket(ticket1)
    print(f"\nAgent Response:\n{result1['response']}")
    print(f"\nTopics Extracted: {result1['customer_profile']['topics_discussed']}")

    # Turn 2: Follow-up question via Gmail
    ticket2 = {
        "ticket_id": "DEMO-002",
        "channel": "gmail",
        "timestamp": "2026-04-03T10:15:00Z",
        "customer_name": "Sarah Johnson",
        "customer_email": "sarah@acmecorp.com",
        "subject": "Re: How do I add team members?",
        "message": "Thanks! That worked. Can I also customize their permissions? I want some members to only view, not edit.",
        "sentiment": "positive",
        "priority": "low"
    }

    print("\n--- TURN 2: Follow-Up Question (Gmail) ---")
    print(f"Customer: {ticket2['message']}")

    result2 = agent.process_ticket(ticket2)
    print(f"\nAgent Response:\n{result2['response']}")
    print(f"\nTopics Discussed: {result2['customer_profile']['topics_discussed']}")
    print(f"Sentiment Changed: {result1['customer_profile']['current_sentiment']} -> {result2['customer_profile']['current_sentiment']}")

    print_section("Customer Profile After Scenario 1")
    print_customer_profile(agent, "sarah@acmecorp.com")

    return agent


def demo_scenario_2():
    """
    Scenario 2: Channel switching
    Customer starts on WhatsApp, switches to Gmail for detailed question
    """
    print_section("SCENARIO 2: Cross-Channel Conversation")

    agent = CustomerSuccessAgent(enable_memory=True)

    # Turn 1: Quick question via WhatsApp
    ticket1 = {
        "ticket_id": "DEMO-003",
        "channel": "whatsapp",
        "timestamp": "2026-04-03T11:00:00Z",
        "customer_name": "Mike Chen",
        "customer_phone": "+1-555-0123",
        "message": "App keeps crashing when uploading files. iPhone 13.",
        "sentiment": "frustrated",
        "priority": "medium"
    }

    print("\n--- TURN 1: Initial Report (WhatsApp) ---")
    print(f"Customer: {ticket1['message']}")

    result1 = agent.process_ticket(ticket1)
    print(f"\nAgent Response:\n{result1['response']}")

    # Turn 2: Follow-up via Gmail with more details
    ticket2 = {
        "ticket_id": "DEMO-004",
        "channel": "gmail",
        "timestamp": "2026-04-03T11:30:00Z",
        "customer_name": "Mike Chen",
        "customer_email": "mike.chen@techstartup.com",
        "customer_phone": "+1-555-0123",
        "subject": "App crash issue - follow up",
        "message": "Hi, I messaged on WhatsApp earlier about app crashes. I tried the steps you suggested (updated app, restarted phone, cleared cache) but it's still crashing. It only happens when I try to upload files larger than 50MB. Can you help?",
        "sentiment": "frustrated",
        "priority": "medium"
    }

    print("\n--- TURN 2: Detailed Follow-Up (Gmail) ---")
    print(f"Customer: {ticket2['message']}")

    result2 = agent.process_ticket(ticket2)
    print(f"\nAgent Response:\n{result2['response']}")
    print(f"\n[AGENT RECOGNIZES SAME CUSTOMER ACROSS CHANNELS]")
    print(f"Customer ID: {result2['customer_profile']['customer_id']}")
    print(f"Channels Used: {result2['customer_profile']['channels_used']}")
    print(f"Channel Switches: {result2['customer_profile']['channel_switches']}")

    print_section("Customer Profile After Scenario 2")
    print_customer_profile(agent, "mike.chen@techstartup.com")

    return agent


def demo_scenario_3():
    """
    Scenario 3: Escalation tracking
    Customer has billing issue that gets escalated, sentiment deteriorates
    """
    print_section("SCENARIO 3: Escalation with Sentiment Tracking")

    agent = CustomerSuccessAgent(enable_memory=True)

    # Turn 1: Initial billing question
    ticket1 = {
        "ticket_id": "DEMO-005",
        "channel": "webform",
        "timestamp": "2026-04-03T14:00:00Z",
        "customer_name": "Emma Rodriguez",
        "customer_email": "emma@designstudio.io",
        "subject": "Billing question",
        "message": "I was charged $288 but I only have 10 users. I thought the Starter plan was $12/user/month which should be $120. Can you explain this charge?",
        "sentiment": "confused",
        "priority": "high"
    }

    print("\n--- TURN 1: Billing Question (Web Form) ---")
    print(f"Customer: {ticket1['message']}")

    result1 = agent.process_ticket(ticket1)
    print(f"\nAgent Decision: {'ESCALATED' if result1['escalated'] else 'AI HANDLED'}")
    if result1['escalated']:
        print(f"Reason: {result1['escalation_reason']}")
        print(f"Priority: {result1['escalation_priority']}")
    print(f"\nAgent Response:\n{result1['response']}")

    # Turn 2: Customer follows up, more frustrated
    ticket2 = {
        "ticket_id": "DEMO-006",
        "channel": "gmail",
        "timestamp": "2026-04-03T16:00:00Z",
        "customer_name": "Emma Rodriguez",
        "customer_email": "emma@designstudio.io",
        "subject": "Re: Billing question - still waiting",
        "message": "I submitted a question about my billing 2 hours ago and haven't heard back. This is urgent - I need to understand why I was overcharged before I can approve next month's budget.",
        "sentiment": "frustrated",
        "priority": "high"
    }

    print("\n--- TURN 2: Follow-Up (Gmail) ---")
    print(f"Customer: {ticket2['message']}")

    result2 = agent.process_ticket(ticket2)
    print(f"\nAgent Response:\n{result2['response']}")
    print(f"\nSentiment Progression: {result1['customer_profile']['current_sentiment']} → {result2['customer_profile']['current_sentiment']}")
    print(f"Resolution Status: {result2['customer_profile']['resolution_status']}")

    print_section("Customer Profile After Scenario 3")
    print_customer_profile(agent, "emma@designstudio.io")

    return agent


def demo_scenario_4():
    """
    Scenario 4: Multiple topics in one conversation
    Customer asks about several different features
    """
    print_section("SCENARIO 4: Multi-Topic Conversation")

    agent = CustomerSuccessAgent(enable_memory=True)

    tickets = [
        {
            "ticket_id": "DEMO-007",
            "channel": "gmail",
            "timestamp": "2026-04-03T15:00:00Z",
            "customer_name": "David Kim",
            "customer_email": "david@marketingpro.com",
            "subject": "Questions about features",
            "message": "Hi, we're evaluating TaskFlow Pro. Can you tell me if the mobile app works offline?",
            "sentiment": "neutral",
            "priority": "low"
        },
        {
            "ticket_id": "DEMO-008",
            "channel": "gmail",
            "timestamp": "2026-04-03T15:10:00Z",
            "customer_name": "David Kim",
            "customer_email": "david@marketingpro.com",
            "subject": "Re: Questions about features",
            "message": "Great! Also, can we integrate with Slack? We use it for all team communication.",
            "sentiment": "positive",
            "priority": "low"
        },
        {
            "ticket_id": "DEMO-009",
            "channel": "gmail",
            "timestamp": "2026-04-03T15:20:00Z",
            "customer_name": "David Kim",
            "customer_email": "david@marketingpro.com",
            "subject": "Re: Questions about features",
            "message": "Perfect. One more thing - we're a team of 150 people. Do you have enterprise pricing with SSO?",
            "sentiment": "positive",
            "priority": "high"
        }
    ]

    for i, ticket in enumerate(tickets, 1):
        print(f"\n--- TURN {i} ---")
        print(f"Customer: {ticket['message']}")

        result = agent.process_ticket(ticket)
        print(f"\nAgent Response:\n{result['response'][:200]}...")

        if result['escalated']:
            print(f"\n[ESCALATED: {result['escalation_reason']}]")

        print(f"\nTopics So Far: {', '.join(result['customer_profile']['topics_discussed'])}")

    print_section("Customer Profile After Scenario 4")
    print_customer_profile(agent, "david@marketingpro.com")

    return agent


def demo_overall_stats():
    """
    Run all scenarios and show overall statistics
    """
    print_section("RUNNING ALL SCENARIOS")

    agent = CustomerSuccessAgent(enable_memory=True)

    # Run all scenarios with the same agent instance
    print("\nProcessing Scenario 1...")
    demo_scenario_1()

    print("\nProcessing Scenario 2...")
    demo_scenario_2()

    print("\nProcessing Scenario 3...")
    demo_scenario_3()

    print("\nProcessing Scenario 4...")
    demo_scenario_4()

    # Get overall stats
    print_section("OVERALL STATISTICS")

    stats = agent.get_customer_stats()

    print(f"\nTotal Customers: {stats['total_customers']}")
    print(f"Total Interactions: {stats['total_interactions']}")
    print(f"Total Escalations: {stats['total_escalations']}")
    print(f"Multi-Channel Customers: {stats['multi_channel_customers']}")

    print("\n--- By Resolution Status ---")
    for status, count in stats['by_status'].items():
        print(f"{status.capitalize():15} {count:3} customers")

    print("\n--- By Current Sentiment ---")
    for sentiment, count in stats['by_sentiment'].items():
        print(f"{sentiment.capitalize():15} {count:3} customers")

    print("\n--- By Original Channel ---")
    for channel, count in stats['by_original_channel'].items():
        print(f"{channel.upper():15} {count:3} customers")

    print("\n--- Top Topics Discussed ---")
    sorted_topics = sorted(stats['topics'].items(), key=lambda x: x[1], reverse=True)
    for topic, count in sorted_topics[:5]:
        print(f"{topic.capitalize():15} {count:3} mentions")

    # Save memory to file
    print("\n--- Saving Conversation Memory ---")
    agent.save_memory("conversation_history.json")
    print("Saved to: conversation_history.json")


def main():
    """Run all demos"""
    print("=" * 80)
    print(" CONVERSATION MEMORY DEMO")
    print(" TechCorp SaaS Customer Success AI Agent")
    print("=" * 80)

    # Run individual scenarios
    print("\n[Running individual scenarios to demonstrate features]\n")

    demo_scenario_1()
    input("\nPress Enter to continue to Scenario 2...")

    demo_scenario_2()
    input("\nPress Enter to continue to Scenario 3...")

    demo_scenario_3()
    input("\nPress Enter to continue to Scenario 4...")

    demo_scenario_4()

    print("\n\n")
    print("=" * 80)
    print(" DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("✓ Multi-turn conversations with context retention")
    print("✓ Cross-channel customer recognition (WhatsApp → Gmail)")
    print("✓ Sentiment tracking across interactions")
    print("✓ Topic extraction and tracking")
    print("✓ Resolution status monitoring")
    print("✓ Channel switch detection")
    print("✓ Escalation tracking")
    print("=" * 80)


if __name__ == "__main__":
    main()
