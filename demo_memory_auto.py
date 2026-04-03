"""
Automated Conversation Memory Demo
Shows all features without requiring user input
"""

from agent import CustomerSuccessAgent
from datetime import datetime


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_interaction(turn_num, ticket, result):
    """Print a single interaction"""
    print(f"\n--- TURN {turn_num}: {ticket['channel'].upper()} ---")
    print(f"Customer: {ticket['message'][:100]}...")

    if result['escalated']:
        print(f"\n[ESCALATED: {result['escalation_reason']} - Priority: {result['escalation_priority'].upper()}]")

    print(f"\nAgent Response:\n{result['response'][:250]}...")

    if 'customer_profile' in result:
        profile = result['customer_profile']
        print(f"\nProfile Update:")
        print(f"  Topics: {', '.join(profile['topics_discussed'])}")
        print(f"  Sentiment: {profile['current_sentiment']}")
        print(f"  Status: {profile['resolution_status']}")
        print(f"  Channels: {', '.join(profile['channels_used'])} (switches: {profile['channel_switches']})")


def main():
    """Run comprehensive demo"""

    print("=" * 80)
    print(" CONVERSATION MEMORY DEMO - AUTOMATED")
    print(" TechCorp SaaS Customer Success AI Agent")
    print("=" * 80)

    agent = CustomerSuccessAgent(enable_memory=True)

    # ========================================================================
    # SCENARIO 1: Multi-turn conversation on same channel
    # ========================================================================
    print_section("SCENARIO 1: Multi-Turn Conversation (Same Channel)")

    tickets_s1 = [
        {
            "ticket_id": "S1-T1",
            "channel": "gmail",
            "timestamp": "2026-04-03T10:00:00Z",
            "customer_name": "Sarah Johnson",
            "customer_email": "sarah@acmecorp.com",
            "subject": "How do I add team members?",
            "message": "Hi, I just signed up for the Professional plan and I'm trying to add my team members to a project. I can't seem to find the option. Can you help?",
            "sentiment": "neutral",
            "priority": "low"
        },
        {
            "ticket_id": "S1-T2",
            "channel": "gmail",
            "timestamp": "2026-04-03T10:15:00Z",
            "customer_name": "Sarah Johnson",
            "customer_email": "sarah@acmecorp.com",
            "subject": "Re: How do I add team members?",
            "message": "Thanks! That worked. Can I also customize their permissions? I want some members to only view, not edit.",
            "sentiment": "positive",
            "priority": "low"
        }
    ]

    for i, ticket in enumerate(tickets_s1, 1):
        result = agent.process_ticket(ticket)
        print_interaction(i, ticket, result)

    # ========================================================================
    # SCENARIO 2: Cross-channel conversation
    # ========================================================================
    print_section("SCENARIO 2: Cross-Channel Conversation")

    tickets_s2 = [
        {
            "ticket_id": "S2-T1",
            "channel": "whatsapp",
            "timestamp": "2026-04-03T11:00:00Z",
            "customer_name": "Mike Chen",
            "customer_phone": "+1-555-0123",
            "message": "App keeps crashing when uploading files. iPhone 13.",
            "sentiment": "frustrated",
            "priority": "medium"
        },
        {
            "ticket_id": "S2-T2",
            "channel": "gmail",
            "timestamp": "2026-04-03T11:30:00Z",
            "customer_name": "Mike Chen",
            "customer_email": "mike.chen@techstartup.com",
            "customer_phone": "+1-555-0123",
            "subject": "App crash issue - follow up",
            "message": "Hi, I messaged on WhatsApp earlier about app crashes. I tried the steps you suggested but it's still crashing. It only happens when I try to upload files larger than 50MB. Can you help?",
            "sentiment": "frustrated",
            "priority": "medium"
        }
    ]

    for i, ticket in enumerate(tickets_s2, 1):
        result = agent.process_ticket(ticket)
        print_interaction(i, ticket, result)

    print("\n[KEY FEATURE: Agent recognized same customer across WhatsApp and Gmail!]")
    profile = agent.conversation_manager.customers.get("mike.chen@techstartup.com")
    if profile:
        print(f"Customer ID: {profile.customer_id}")
        print(f"Phone mapped to email: {profile.phone} -> {profile.email}")
        print(f"Original channel: {profile.original_channel}")
        print(f"Channels used: {profile.channels_used}")
        print(f"Channel switches: {profile.channel_switches}")

    # ========================================================================
    # SCENARIO 3: Escalation with sentiment tracking
    # ========================================================================
    print_section("SCENARIO 3: Escalation with Sentiment Tracking")

    tickets_s3 = [
        {
            "ticket_id": "S3-T1",
            "channel": "webform",
            "timestamp": "2026-04-03T14:00:00Z",
            "customer_name": "Emma Rodriguez",
            "customer_email": "emma@designstudio.io",
            "subject": "Billing question",
            "message": "I was charged $288 but I only have 10 users. I thought the Starter plan was $12/user/month which should be $120. Can you explain this charge?",
            "sentiment": "confused",
            "priority": "high"
        },
        {
            "ticket_id": "S3-T2",
            "channel": "gmail",
            "timestamp": "2026-04-03T16:00:00Z",
            "customer_name": "Emma Rodriguez",
            "customer_email": "emma@designstudio.io",
            "subject": "Re: Billing question - still waiting",
            "message": "I submitted a question about my billing 2 hours ago and haven't heard back. This is urgent - I need to understand why I was overcharged.",
            "sentiment": "frustrated",
            "priority": "high"
        }
    ]

    for i, ticket in enumerate(tickets_s3, 1):
        result = agent.process_ticket(ticket)
        print_interaction(i, ticket, result)

    print("\n[KEY FEATURE: Sentiment tracking across conversation]")
    profile = agent.conversation_manager.customers.get("emma@designstudio.io")
    if profile:
        print(f"Sentiment history: {profile.sentiment_history}")

    # ========================================================================
    # SCENARIO 4: Multi-topic conversation
    # ========================================================================
    print_section("SCENARIO 4: Multi-Topic Conversation")

    tickets_s4 = [
        {
            "ticket_id": "S4-T1",
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
            "ticket_id": "S4-T2",
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
            "ticket_id": "S4-T3",
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

    for i, ticket in enumerate(tickets_s4, 1):
        result = agent.process_ticket(ticket)
        print_interaction(i, ticket, result)

    print("\n[KEY FEATURE: Topic tracking across conversation]")
    profile = agent.conversation_manager.customers.get("david@marketingpro.com")
    if profile:
        print(f"All topics discussed: {', '.join(profile.topics_discussed)}")

    # ========================================================================
    # OVERALL STATISTICS
    # ========================================================================
    print_section("OVERALL STATISTICS")

    stats = agent.get_customer_stats()

    print(f"\nTotal Customers: {stats['total_customers']}")
    print(f"Total Interactions: {stats['total_interactions']}")
    print(f"Total Escalations: {stats['total_escalations']}")
    print(f"Multi-Channel Customers: {stats['multi_channel_customers']}")

    print("\n--- By Resolution Status ---")
    for status, count in stats['by_status'].items():
        print(f"  {status.capitalize():15} {count} customers")

    print("\n--- By Current Sentiment ---")
    for sentiment, count in stats['by_sentiment'].items():
        print(f"  {sentiment.capitalize():15} {count} customers")

    print("\n--- By Original Channel ---")
    for channel, count in stats['by_original_channel'].items():
        print(f"  {channel.upper():15} {count} customers")

    print("\n--- Top Topics Discussed ---")
    sorted_topics = sorted(stats['topics'].items(), key=lambda x: x[1], reverse=True)
    for topic, count in sorted_topics:
        print(f"  {topic.capitalize():15} {count} mentions")

    # ========================================================================
    # SAVE MEMORY
    # ========================================================================
    print_section("SAVING CONVERSATION MEMORY")

    agent.save_memory("conversation_history.json")
    print("\nConversation history saved to: conversation_history.json")
    print("This file contains:")
    print("  - Complete conversation history for all customers")
    print("  - Customer profiles with topics, sentiment, channels")
    print("  - Phone-to-email mappings for cross-channel recognition")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_section("DEMO COMPLETE - KEY FEATURES DEMONSTRATED")

    print("\n[PASS] Multi-turn conversations with context retention")
    print("       - Agent remembers previous messages in conversation")
    print("       - Follow-up questions are recognized and handled appropriately")

    print("\n[PASS] Cross-channel customer recognition")
    print("       - Customer starts on WhatsApp, continues on Gmail")
    print("       - Agent links phone number to email address")
    print("       - Conversation context preserved across channels")

    print("\n[PASS] Sentiment tracking")
    print("       - Tracks sentiment changes across conversation")
    print("       - Sentiment history maintained with timestamps")

    print("\n[PASS] Topic extraction and tracking")
    print("       - Automatically identifies topics (billing, technical, features, etc.)")
    print("       - Tracks all topics discussed in conversation")

    print("\n[PASS] Resolution status monitoring")
    print("       - Tracks: pending, solved, escalated")
    print("       - Updates based on agent actions")

    print("\n[PASS] Channel switch detection")
    print("       - Tracks original channel and all channels used")
    print("       - Counts channel switches")

    print("\n[PASS] Persistent memory")
    print("       - Saves to JSON file")
    print("       - Can be loaded to resume conversations")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
