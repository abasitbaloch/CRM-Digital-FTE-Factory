"""
Test script for Customer Success AI Agent
Processes all sample tickets and generates performance metrics
"""

import json
from collections import defaultdict
from agent import CustomerSuccessAgent


def analyze_all_tickets():
    """Process all sample tickets and generate analytics"""

    # Initialize agent
    agent = CustomerSuccessAgent()

    # Load all tickets
    with open("context/sample-tickets.json", "r", encoding="utf-8") as f:
        tickets = json.load(f)

    # Track metrics
    metrics = {
        "total_tickets": len(tickets),
        "escalated": 0,
        "ai_handled": 0,
        "by_channel": defaultdict(lambda: {"total": 0, "escalated": 0, "ai_handled": 0}),
        "by_priority": defaultdict(int),
        "escalation_reasons": defaultdict(int),
        "by_sentiment": defaultdict(lambda: {"total": 0, "escalated": 0})
    }

    results = []

    print("Processing all 52 sample tickets...")
    print("=" * 80)

    for ticket in tickets:
        result = agent.process_ticket(ticket)
        results.append(result)

        channel = ticket["channel"]
        sentiment = ticket["sentiment"]

        # Update metrics
        metrics["by_channel"][channel]["total"] += 1
        metrics["by_sentiment"][sentiment]["total"] += 1

        if result["escalated"]:
            metrics["escalated"] += 1
            metrics["by_channel"][channel]["escalated"] += 1
            metrics["by_sentiment"][sentiment]["escalated"] += 1
            metrics["by_priority"][result["escalation_priority"]] += 1
            metrics["escalation_reasons"][result["escalation_reason"]] += 1
        else:
            metrics["ai_handled"] += 1
            metrics["by_channel"][channel]["ai_handled"] += 1

    return results, metrics


def print_metrics(metrics):
    """Print formatted metrics report"""

    print("\n" + "=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)

    # Overall stats
    print(f"\nTotal Tickets Processed: {metrics['total_tickets']}")
    print(f"AI Handled: {metrics['ai_handled']} ({metrics['ai_handled']/metrics['total_tickets']*100:.1f}%)")
    print(f"Escalated: {metrics['escalated']} ({metrics['escalated']/metrics['total_tickets']*100:.1f}%)")

    # By channel
    print("\n--- By Channel ---")
    for channel, stats in sorted(metrics["by_channel"].items()):
        total = stats["total"]
        escalated = stats["escalated"]
        ai_handled = stats["ai_handled"]
        print(f"{channel.upper():12} | Total: {total:2} | AI: {ai_handled:2} ({ai_handled/total*100:4.1f}%) | Escalated: {escalated:2} ({escalated/total*100:4.1f}%)")

    # By escalation priority
    if metrics["by_priority"]:
        print("\n--- Escalation Priority Distribution ---")
        for priority, count in sorted(metrics["by_priority"].items(), key=lambda x: {"critical": 3, "high": 2, "medium": 1}.get(x[0], 0), reverse=True):
            print(f"{priority.upper():10} | {count:2} tickets")

    # Top escalation reasons
    print("\n--- Top Escalation Reasons ---")
    for reason, count in sorted(metrics["escalation_reasons"].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{count:2}x | {reason}")

    # By sentiment
    print("\n--- By Sentiment ---")
    for sentiment, stats in sorted(metrics["by_sentiment"].items(), key=lambda x: x[1]["total"], reverse=True):
        total = stats["total"]
        escalated = stats["escalated"]
        if total > 0:
            print(f"{sentiment:12} | Total: {total:2} | Escalated: {escalated:2} ({escalated/total*100:4.1f}%)")

    print("\n" + "=" * 80)


def show_escalation_examples(results):
    """Show examples of escalated tickets"""

    print("\n" + "=" * 80)
    print("ESCALATION EXAMPLES")
    print("=" * 80)

    escalated = [r for r in results if r["escalated"]]

    # Group by priority
    by_priority = defaultdict(list)
    for result in escalated:
        by_priority[result["escalation_priority"]].append(result)

    for priority in ["critical", "high", "medium"]:
        if priority in by_priority:
            print(f"\n--- {priority.upper()} Priority ---")
            for result in by_priority[priority][:2]:  # Show 2 examples per priority
                ticket = result["ticket"]
                print(f"\nTicket: {ticket['ticket_id']} ({ticket['channel']})")
                print(f"Customer: {ticket['customer_name']}")
                print(f"Message: {ticket['message'][:100]}...")
                print(f"Reason: {result['escalation_reason']}")


def show_ai_handled_examples(results):
    """Show examples of AI-handled tickets"""

    print("\n" + "=" * 80)
    print("AI-HANDLED EXAMPLES")
    print("=" * 80)

    ai_handled = [r for r in results if not r["escalated"]]

    # Show diverse examples
    channels_shown = set()
    count = 0

    for result in ai_handled:
        ticket = result["ticket"]
        channel = ticket["channel"]

        if channel not in channels_shown and count < 3:
            print(f"\n--- {channel.upper()} Example ---")
            print(f"Ticket: {ticket['ticket_id']}")
            print(f"Question: {ticket['message'][:80]}...")
            print(f"Response Preview: {result['response'][:150]}...")
            channels_shown.add(channel)
            count += 1


def main():
    """Run comprehensive test suite"""

    print("=" * 80)
    print("CUSTOMER SUCCESS AI AGENT - COMPREHENSIVE TEST")
    print("=" * 80)

    # Process all tickets
    results, metrics = analyze_all_tickets()

    # Print reports
    print_metrics(metrics)
    show_escalation_examples(results)
    show_ai_handled_examples(results)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    ai_resolution_rate = metrics["ai_handled"] / metrics["total_tickets"] * 100
    escalation_rate = metrics["escalated"] / metrics["total_tickets"] * 100

    print(f"\nAI Resolution Rate: {ai_resolution_rate:.1f}%")
    print(f"Escalation Rate: {escalation_rate:.1f}%")

    # Evaluation
    print("\nEvaluation:")
    if escalation_rate < 20:
        print("[PASS] Escalation rate is within target (<20%)")
    else:
        print("[REVIEW] Escalation rate is above target (>20%)")

    if ai_resolution_rate > 60:
        print("[PASS] AI resolution rate meets target (>60%)")
    else:
        print("[REVIEW] AI resolution rate below target (<60%)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
