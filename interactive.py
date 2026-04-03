"""
Interactive testing interface for Customer Success AI Agent
Allows manual testing of individual tickets
"""

import json
from datetime import datetime
from agent import CustomerSuccessAgent


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)


def get_channel():
    """Get channel selection from user"""
    print("\nSelect Channel:")
    print("1. Gmail (Email)")
    print("2. WhatsApp")
    print("3. Web Form")

    while True:
        choice = input("\nEnter choice (1-3): ").strip()
        if choice == "1":
            return "gmail"
        elif choice == "2":
            return "whatsapp"
        elif choice == "3":
            return "webform"
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def get_ticket_input(channel):
    """Get ticket details from user"""
    print(f"\n--- Creating {channel.upper()} Ticket ---")

    customer_name = input("Customer Name: ").strip() or "Test Customer"

    if channel == "whatsapp":
        contact = input("Phone Number: ").strip() or "+1-555-0000"
        subject = None
    else:
        contact = input("Email Address: ").strip() or "customer@example.com"
        subject = input("Subject: ").strip() or "Customer Inquiry"

    print("\nMessage (press Enter twice when done):")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    message = "\n".join(lines[:-1]) if lines else "Test message"

    print("\nSentiment:")
    print("1. Neutral")
    print("2. Frustrated")
    print("3. Angry")
    print("4. Positive")

    sentiment_choice = input("Select sentiment (1-4, default 1): ").strip() or "1"
    sentiment_map = {"1": "neutral", "2": "frustrated", "3": "angry", "4": "positive"}
    sentiment = sentiment_map.get(sentiment_choice, "neutral")

    return {
        "ticket_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "channel": channel,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "customer_name": customer_name,
        "customer_email": contact if channel != "whatsapp" else None,
        "customer_phone": contact if channel == "whatsapp" else None,
        "subject": subject,
        "message": message,
        "sentiment": sentiment,
        "priority": "low"
    }


def display_result(ticket, result):
    """Display processing result"""
    print_header("TICKET DETAILS")

    print(f"\nTicket ID: {ticket['ticket_id']}")
    print(f"Channel: {ticket['channel'].upper()}")
    print(f"Customer: {ticket['customer_name']}")
    if ticket.get('subject'):
        print(f"Subject: {ticket['subject']}")
    print(f"Sentiment: {ticket['sentiment']}")
    print(f"\nMessage:\n{ticket['message']}")

    print_header("AGENT ANALYSIS")

    print(f"\nEscalated: {'YES [!]' if result['escalated'] else 'NO'}")
    print(f"Reason: {result['escalation_reason']}")

    if result['escalated']:
        print(f"Priority: {result['escalation_priority'].upper()}")

    print(f"Relevant Docs Found: {result['relevant_docs_count']} sections")

    print_header(f"RESPONSE ({ticket['channel'].upper()})")
    print(f"\n{result['response']}")

    print_header("METADATA")
    print(f"\nProcessed At: {result['processed_at']}")


def load_sample_ticket():
    """Load a sample ticket for quick testing"""
    print("\nSelect Sample Ticket:")
    print("1. Simple how-to question (Gmail)")
    print("2. Technical issue (WhatsApp)")
    print("3. Billing question (Web Form)")
    print("4. Refund request - escalation (WhatsApp)")
    print("5. Legal threat - escalation (Gmail)")

    choice = input("\nEnter choice (1-5): ").strip()

    samples = {
        "1": {
            "ticket_id": "SAMPLE-001",
            "channel": "gmail",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "customer_name": "Sarah Johnson",
            "customer_email": "sarah@example.com",
            "subject": "How do I add team members?",
            "message": "Hi, I just signed up for the Professional plan and I'm trying to add my team members to a project. I can't seem to find the option. Can you help?",
            "sentiment": "neutral",
            "priority": "low"
        },
        "2": {
            "ticket_id": "SAMPLE-002",
            "channel": "whatsapp",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "customer_name": "Mike Chen",
            "customer_phone": "+1-555-0123",
            "subject": None,
            "message": "App keeps crashing when I try to upload files. Using iPhone 13. Help!",
            "sentiment": "frustrated",
            "priority": "medium"
        },
        "3": {
            "ticket_id": "SAMPLE-003",
            "channel": "webform",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "customer_name": "Emma Rodriguez",
            "customer_email": "emma@example.com",
            "subject": "Billing question",
            "message": "I was charged $288 but I only have 10 users. I thought the Starter plan was $12/user/month which should be $120. Can you explain this charge?",
            "sentiment": "confused",
            "priority": "high"
        },
        "4": {
            "ticket_id": "SAMPLE-004",
            "channel": "whatsapp",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "customer_name": "Priya Patel",
            "customer_phone": "+44-7700-900123",
            "subject": None,
            "message": "Can I get a refund? We're not using the service anymore",
            "sentiment": "neutral",
            "priority": "high"
        },
        "5": {
            "ticket_id": "SAMPLE-005",
            "channel": "gmail",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "customer_name": "Robert Martinez",
            "customer_email": "robert@example.com",
            "subject": "This is unacceptable - legal action",
            "message": "I've been trying to cancel my subscription for 3 weeks and you keep charging me. This is fraudulent and I'm contacting my lawyer if this isn't resolved immediately. I want a full refund for the last 3 months.",
            "sentiment": "angry",
            "priority": "critical"
        }
    }

    return samples.get(choice)


def main():
    """Main interactive loop"""
    print_header("CUSTOMER SUCCESS AI AGENT - INTERACTIVE TESTING")

    # Initialize agent
    print("\nInitializing agent...")
    agent = CustomerSuccessAgent()
    print("Agent ready!")

    while True:
        print("\n" + "-" * 80)
        print("\nOptions:")
        print("1. Create custom ticket")
        print("2. Load sample ticket")
        print("3. Exit")

        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "1":
            # Custom ticket
            channel = get_channel()
            ticket = get_ticket_input(channel)

        elif choice == "2":
            # Sample ticket
            ticket = load_sample_ticket()
            if not ticket:
                print("Invalid choice. Please try again.")
                continue

        elif choice == "3":
            print("\nExiting. Thank you!")
            break

        else:
            print("Invalid choice. Please try again.")
            continue

        # Process ticket
        print("\nProcessing ticket...")
        result = agent.process_ticket(ticket)

        # Display result
        display_result(ticket, result)

        # Continue?
        cont = input("\n\nProcess another ticket? (y/n): ").strip().lower()
        if cont != 'y':
            print("\nExiting. Thank you!")
            break


if __name__ == "__main__":
    main()
