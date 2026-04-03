"""
Skills Integration - Customer Success AI Agent
Integrates formal skills with the existing agent
"""

import json
from skills_manifest import (
    SkillsRegistry,
    KnowledgeRetrievalSkill,
    SentimentAnalysisSkill,
    EscalationDecisionSkill,
    ChannelAdaptationSkill,
    CustomerIdentificationSkill
)
from agent import CustomerSuccessAgent


class SkillsEnabledAgent(CustomerSuccessAgent):
    """Agent with formal skills integration"""

    def __init__(self, context_dir: str = "context", enable_memory: bool = True):
        super().__init__(context_dir, enable_memory)

        # Initialize skills registry
        self.skills_registry = SkillsRegistry()

        # Register skills
        self._register_skills()

    def _register_skills(self):
        """Register all skills with the agent"""

        # Skill 1: Knowledge Retrieval
        knowledge_skill = KnowledgeRetrievalSkill(self.doc_retriever)
        self.skills_registry.register(knowledge_skill)

        # Skill 2: Sentiment Analysis
        sentiment_skill = SentimentAnalysisSkill()
        self.skills_registry.register(sentiment_skill)

        # Skill 3: Escalation Decision
        escalation_skill = EscalationDecisionSkill(self.escalation_engine)
        self.skills_registry.register(escalation_skill)

        # Skill 4: Channel Adaptation
        channel_skill = ChannelAdaptationSkill(self.response_generator)
        self.skills_registry.register(channel_skill)

        # Skill 5: Customer Identification
        if self.memory_enabled:
            identification_skill = CustomerIdentificationSkill(self.conversation_manager)
            self.skills_registry.register(identification_skill)

    def process_ticket_with_skills(self, raw_ticket: dict) -> dict:
        """Process ticket using formal skills"""

        result = {
            "ticket": raw_ticket,
            "skills_executed": [],
            "skill_outputs": {}
        }

        # SKILL 1: Customer Identification
        if self.memory_enabled:
            identification_skill = self.skills_registry.get_skill("customer_identification")
            if identification_skill:
                identification_output = identification_skill.execute(
                    email=raw_ticket.get("customer_email"),
                    phone=raw_ticket.get("customer_phone"),
                    name=raw_ticket.get("customer_name", "Customer"),
                    channel=raw_ticket["channel"]
                )
                result["skills_executed"].append("customer_identification")
                result["skill_outputs"]["customer_identification"] = identification_output

        # SKILL 2: Sentiment Analysis
        sentiment_skill = self.skills_registry.get_skill("sentiment_analysis")
        if sentiment_skill:
            previous_sentiment = raw_ticket.get("sentiment", "neutral")
            sentiment_output = sentiment_skill.execute(
                message=raw_ticket["message"],
                previous_sentiment=previous_sentiment
            )
            result["skills_executed"].append("sentiment_analysis")
            result["skill_outputs"]["sentiment_analysis"] = sentiment_output

            # Update ticket with analyzed sentiment
            raw_ticket["sentiment"] = sentiment_output["sentiment"]

        # SKILL 3: Knowledge Retrieval
        knowledge_skill = self.skills_registry.get_skill("knowledge_retrieval")
        if knowledge_skill:
            conversation_topics = []
            if self.memory_enabled and "customer_identification" in result["skill_outputs"]:
                merged_history = result["skill_outputs"]["customer_identification"]["merged_history"]
                conversation_topics = merged_history.get("topics_discussed", [])

            knowledge_output = knowledge_skill.execute(
                query=raw_ticket["message"],
                max_results=3,
                conversation_topics=conversation_topics
            )
            result["skills_executed"].append("knowledge_retrieval")
            result["skill_outputs"]["knowledge_retrieval"] = knowledge_output

        # Process with base agent
        base_result = self.process_ticket(raw_ticket)

        # SKILL 4: Escalation Decision (enhanced)
        escalation_skill = self.skills_registry.get_skill("escalation_decision")
        if escalation_skill and "sentiment_analysis" in result["skill_outputs"]:
            sentiment_data = result["skill_outputs"]["sentiment_analysis"]
            escalation_output = escalation_skill.execute(
                message=raw_ticket["message"],
                sentiment=sentiment_data["sentiment"],
                sentiment_trend=sentiment_data["sentiment_trend"],
                conversation_context={}
            )
            result["skills_executed"].append("escalation_decision")
            result["skill_outputs"]["escalation_decision"] = escalation_output

        # SKILL 5: Channel Adaptation
        channel_skill = self.skills_registry.get_skill("channel_adaptation")
        if channel_skill:
            is_followup = False
            if self.memory_enabled and "customer_identification" in result["skill_outputs"]:
                merged_history = result["skill_outputs"]["customer_identification"]["merged_history"]
                is_followup = merged_history.get("total_interactions", 0) > 0

            channel_output = channel_skill.execute(
                response_text=base_result["response"],
                target_channel=raw_ticket["channel"],
                customer_name=raw_ticket.get("customer_name", "Customer"),
                is_followup=is_followup
            )
            result["skills_executed"].append("channel_adaptation")
            result["skill_outputs"]["channel_adaptation"] = channel_output

        # Merge with base result
        result.update({
            "response": base_result["response"],
            "escalated": base_result["escalated"],
            "escalation_reason": base_result["escalation_reason"],
            "processed_at": base_result["processed_at"]
        })

        if "customer_profile" in base_result:
            result["customer_profile"] = base_result["customer_profile"]

        return result

    def export_skills_manifest(self, filepath: str):
        """Export skills manifest to JSON file"""
        manifest = self.skills_registry.export_manifest()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        print(f"Skills manifest exported to: {filepath}")


def main():
    """Demo: Skills-enabled agent"""

    print("=" * 80)
    print("SKILLS-ENABLED AGENT DEMO")
    print("=" * 80)

    # Initialize skills-enabled agent
    agent = SkillsEnabledAgent(enable_memory=True)

    print(f"\nRegistered skills: {len(agent.skills_registry.list_skills())}")
    for skill_name in agent.skills_registry.list_skills():
        print(f"  - {skill_name}")

    # Test ticket
    ticket = {
        "ticket_id": "SKILLS-001",
        "channel": "gmail",
        "timestamp": "2026-04-03T10:00:00Z",
        "customer_name": "Alice Johnson",
        "customer_email": "alice@example.com",
        "subject": "How do I export my data?",
        "message": "I need to export all my project data to CSV format. Where can I find this option?",
        "sentiment": "neutral",
        "priority": "low"
    }

    print("\n" + "=" * 80)
    print("PROCESSING TICKET WITH SKILLS")
    print("=" * 80)

    print(f"\nTicket: {ticket['ticket_id']}")
    print(f"Customer: {ticket['customer_name']}")
    print(f"Message: {ticket['message']}")

    # Process with skills
    result = agent.process_ticket_with_skills(ticket)

    print(f"\n--- SKILLS EXECUTED ---")
    for i, skill_name in enumerate(result["skills_executed"], 1):
        print(f"{i}. {skill_name}")

    print(f"\n--- SKILL OUTPUTS ---")

    # Customer Identification
    if "customer_identification" in result["skill_outputs"]:
        output = result["skill_outputs"]["customer_identification"]
        print(f"\nCustomer Identification:")
        print(f"  Customer ID: {output['customer_id']}")
        print(f"  New Customer: {output['is_new_customer']}")
        print(f"  Confidence: {output['confidence']:.2f}")

    # Sentiment Analysis
    if "sentiment_analysis" in result["skill_outputs"]:
        output = result["skill_outputs"]["sentiment_analysis"]
        print(f"\nSentiment Analysis:")
        print(f"  Sentiment: {output['sentiment']}")
        print(f"  Confidence: {output['confidence']:.2f}")
        print(f"  Trend: {output['sentiment_trend']}")
        print(f"  Indicators: {', '.join(output['indicators'][:3])}")

    # Knowledge Retrieval
    if "knowledge_retrieval" in result["skill_outputs"]:
        output = result["skill_outputs"]["knowledge_retrieval"]
        print(f"\nKnowledge Retrieval:")
        print(f"  Results Found: {output['results_count']}")
        print(f"  Confidence: {output['confidence']:.2f}")
        if output['results']:
            print(f"  Top Result: {output['results'][0]['content'][:80]}...")

    # Escalation Decision
    if "escalation_decision" in result["skill_outputs"]:
        output = result["skill_outputs"]["escalation_decision"]
        print(f"\nEscalation Decision:")
        print(f"  Should Escalate: {output['should_escalate']}")
        print(f"  Reason: {output['reason']}")
        print(f"  Confidence: {output['confidence']:.2f}")

    # Channel Adaptation
    if "channel_adaptation" in result["skill_outputs"]:
        output = result["skill_outputs"]["channel_adaptation"]
        print(f"\nChannel Adaptation:")
        print(f"  Tone: {output['tone']}")
        print(f"  Character Count: {output['character_count']}")

    print(f"\n--- FINAL RESPONSE ---")
    print(result["response"][:300] + "...")

    # Export manifest
    print("\n" + "=" * 80)
    print("EXPORTING SKILLS MANIFEST")
    print("=" * 80)

    agent.export_skills_manifest("skills_manifest.json")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
