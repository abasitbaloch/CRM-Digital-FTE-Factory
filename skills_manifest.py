"""
Skills Manifest - Customer Success AI Agent
Formal definition of agent capabilities as reusable skills
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from abc import ABC, abstractmethod


class SkillCategory(str, Enum):
    """Skill categories"""
    KNOWLEDGE = "knowledge"
    ANALYSIS = "analysis"
    DECISION = "decision"
    FORMATTING = "formatting"
    IDENTIFICATION = "identification"


class SkillPriority(str, Enum):
    """Skill execution priority"""
    CRITICAL = "critical"  # Must execute
    HIGH = "high"          # Should execute
    MEDIUM = "medium"      # Can execute
    LOW = "low"            # Optional


@dataclass
class SkillInput:
    """Skill input specification"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class SkillOutput:
    """Skill output specification"""
    name: str
    type: str
    description: str


@dataclass
class SkillMetadata:
    """Skill metadata"""
    name: str
    description: str
    category: SkillCategory
    priority: SkillPriority
    version: str
    author: str = "TechCorp AI Team"
    tags: List[str] = field(default_factory=list)


@dataclass
class SkillDefinition:
    """Complete skill definition"""
    metadata: SkillMetadata
    when_to_use: str
    inputs: List[SkillInput]
    outputs: List[SkillOutput]
    dependencies: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


class Skill(ABC):
    """Base class for all skills"""

    def __init__(self, definition: SkillDefinition):
        self.definition = definition

    @abstractmethod
    def execute(self, **inputs) -> Dict[str, Any]:
        """Execute the skill with given inputs"""
        pass

    def validate_inputs(self, **inputs) -> bool:
        """Validate that all required inputs are provided"""
        for input_spec in self.definition.inputs:
            if input_spec.required and input_spec.name not in inputs:
                raise ValueError(f"Missing required input: {input_spec.name}")
        return True


# ============================================================================
# SKILL 1: Knowledge Retrieval
# ============================================================================

KNOWLEDGE_RETRIEVAL_DEFINITION = SkillDefinition(
    metadata=SkillMetadata(
        name="knowledge_retrieval",
        description="Search product documentation for relevant information",
        category=SkillCategory.KNOWLEDGE,
        priority=SkillPriority.HIGH,
        version="1.0.0",
        tags=["search", "documentation", "knowledge-base"]
    ),
    when_to_use="Customer asks product questions or needs information",
    inputs=[
        SkillInput(
            name="query",
            type="string",
            description="Search query text from customer message",
            required=True
        ),
        SkillInput(
            name="max_results",
            type="integer",
            description="Maximum number of results to return",
            required=False,
            default=3
        ),
        SkillInput(
            name="conversation_topics",
            type="list[string]",
            description="Topics discussed in conversation for context",
            required=False,
            default=[]
        )
    ],
    outputs=[
        SkillOutput(
            name="results",
            type="list[dict]",
            description="List of relevant documentation snippets with relevance scores"
        ),
        SkillOutput(
            name="results_count",
            type="integer",
            description="Number of results found"
        ),
        SkillOutput(
            name="confidence",
            type="float",
            description="Confidence score for top result (0.0-1.0)"
        )
    ],
    examples=[
        {
            "input": {
                "query": "how to add team members",
                "max_results": 3
            },
            "output": {
                "results": [
                    {
                        "content": "Here's how to add team members...",
                        "relevance": "high",
                        "confidence": 0.95
                    }
                ],
                "results_count": 3,
                "confidence": 0.95
            }
        }
    ]
)


class KnowledgeRetrievalSkill(Skill):
    """Knowledge retrieval skill implementation"""

    def __init__(self, doc_retriever):
        super().__init__(KNOWLEDGE_RETRIEVAL_DEFINITION)
        self.doc_retriever = doc_retriever

    def execute(self, **inputs) -> Dict[str, Any]:
        """Execute knowledge retrieval"""
        self.validate_inputs(**inputs)

        query = inputs['query']
        max_results = inputs.get('max_results', 3)
        conversation_topics = inputs.get('conversation_topics', [])

        # Enhance query with conversation topics
        enhanced_query = query
        if conversation_topics:
            enhanced_query += " " + " ".join(conversation_topics)

        # Search documentation
        results = self.doc_retriever.search(enhanced_query, max_results=max_results)

        # Calculate confidence based on result quality
        confidence = 0.9 if results else 0.0

        return {
            "results": [
                {
                    "content": result,
                    "relevance": "high" if i == 0 else "medium" if i < 2 else "low",
                    "confidence": confidence - (i * 0.1)
                }
                for i, result in enumerate(results)
            ],
            "results_count": len(results),
            "confidence": confidence
        }


# ============================================================================
# SKILL 2: Sentiment Analysis
# ============================================================================

SENTIMENT_ANALYSIS_DEFINITION = SkillDefinition(
    metadata=SkillMetadata(
        name="sentiment_analysis",
        description="Analyze customer message sentiment and emotional state",
        category=SkillCategory.ANALYSIS,
        priority=SkillPriority.CRITICAL,
        version="1.0.0",
        tags=["sentiment", "emotion", "analysis"]
    ),
    when_to_use="Every customer message to track emotional state",
    inputs=[
        SkillInput(
            name="message",
            type="string",
            description="Customer message text to analyze",
            required=True
        ),
        SkillInput(
            name="previous_sentiment",
            type="string",
            description="Previous sentiment for trend analysis",
            required=False,
            default="neutral"
        )
    ],
    outputs=[
        SkillOutput(
            name="sentiment",
            type="string",
            description="Detected sentiment: neutral, positive, frustrated, angry, confused"
        ),
        SkillOutput(
            name="confidence",
            type="float",
            description="Confidence score (0.0-1.0)"
        ),
        SkillOutput(
            name="sentiment_trend",
            type="string",
            description="Trend: improving, stable, deteriorating"
        ),
        SkillOutput(
            name="indicators",
            type="list[string]",
            description="Key words/phrases that influenced sentiment"
        )
    ],
    examples=[
        {
            "input": {
                "message": "This is unacceptable! I've been waiting for 2 days!",
                "previous_sentiment": "frustrated"
            },
            "output": {
                "sentiment": "angry",
                "confidence": 0.95,
                "sentiment_trend": "deteriorating",
                "indicators": ["unacceptable", "waiting", "2 days", "!"]
            }
        }
    ]
)


class SentimentAnalysisSkill(Skill):
    """Sentiment analysis skill implementation"""

    def __init__(self):
        super().__init__(SENTIMENT_ANALYSIS_DEFINITION)

        # Sentiment indicators
        self.sentiment_keywords = {
            "angry": ["unacceptable", "terrible", "worst", "horrible", "disgusting", "furious", "outraged"],
            "frustrated": ["frustrated", "annoying", "still not working", "tried everything", "doesn't work"],
            "confused": ["confused", "don't understand", "unclear", "not sure", "what does", "how do"],
            "positive": ["thank", "thanks", "great", "perfect", "excellent", "love", "appreciate", "helpful"],
            "disappointed": ["disappointed", "expected", "thought it would", "not what i wanted"]
        }

    def execute(self, **inputs) -> Dict[str, Any]:
        """Execute sentiment analysis"""
        self.validate_inputs(**inputs)

        message = inputs['message'].lower()
        previous_sentiment = inputs.get('previous_sentiment', 'neutral')

        # Detect sentiment
        sentiment_scores = {}
        indicators = []

        for sentiment, keywords in self.sentiment_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message)
            if score > 0:
                sentiment_scores[sentiment] = score
                indicators.extend([kw for kw in keywords if kw in message])

        # Determine primary sentiment
        if sentiment_scores:
            sentiment = max(sentiment_scores, key=sentiment_scores.get)
            confidence = min(0.6 + (sentiment_scores[sentiment] * 0.1), 0.99)
        else:
            sentiment = "neutral"
            confidence = 0.5

        # Check for intensity markers
        if "!" in message or message.isupper():
            if sentiment in ["frustrated", "confused"]:
                sentiment = "angry"
                confidence = min(confidence + 0.1, 0.99)
            indicators.append("high intensity")

        # Determine trend
        sentiment_order = ["positive", "neutral", "confused", "frustrated", "angry", "disappointed"]
        prev_idx = sentiment_order.index(previous_sentiment) if previous_sentiment in sentiment_order else 1
        curr_idx = sentiment_order.index(sentiment) if sentiment in sentiment_order else 1

        if curr_idx > prev_idx:
            trend = "deteriorating"
        elif curr_idx < prev_idx:
            trend = "improving"
        else:
            trend = "stable"

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "sentiment_trend": trend,
            "indicators": indicators[:5]  # Top 5 indicators
        }


# ============================================================================
# SKILL 3: Escalation Decision
# ============================================================================

ESCALATION_DECISION_DEFINITION = SkillDefinition(
    metadata=SkillMetadata(
        name="escalation_decision",
        description="Decide if ticket should be escalated to human support",
        category=SkillCategory.DECISION,
        priority=SkillPriority.CRITICAL,
        version="1.0.0",
        tags=["escalation", "decision", "routing"]
    ),
    when_to_use="After generating response, before sending to customer",
    inputs=[
        SkillInput(
            name="message",
            type="string",
            description="Customer message text",
            required=True
        ),
        SkillInput(
            name="sentiment",
            type="string",
            description="Current sentiment",
            required=True
        ),
        SkillInput(
            name="sentiment_trend",
            type="string",
            description="Sentiment trend: improving, stable, deteriorating",
            required=False,
            default="stable"
        ),
        SkillInput(
            name="conversation_context",
            type="dict",
            description="Conversation history and context",
            required=False,
            default={}
        )
    ],
    outputs=[
        SkillOutput(
            name="should_escalate",
            type="boolean",
            description="Whether to escalate to human"
        ),
        SkillOutput(
            name="reason",
            type="string",
            description="Reason for escalation decision"
        ),
        SkillOutput(
            name="priority",
            type="string",
            description="Escalation priority: critical, high, medium"
        ),
        SkillOutput(
            name="confidence",
            type="float",
            description="Confidence in decision (0.0-1.0)"
        )
    ],
    examples=[
        {
            "input": {
                "message": "I'm contacting my lawyer about this",
                "sentiment": "angry",
                "sentiment_trend": "deteriorating"
            },
            "output": {
                "should_escalate": True,
                "reason": "Legal threat detected",
                "priority": "critical",
                "confidence": 0.99
            }
        }
    ]
)


class EscalationDecisionSkill(Skill):
    """Escalation decision skill implementation"""

    def __init__(self, escalation_engine):
        super().__init__(ESCALATION_DECISION_DEFINITION)
        self.escalation_engine = escalation_engine

    def execute(self, **inputs) -> Dict[str, Any]:
        """Execute escalation decision"""
        self.validate_inputs(**inputs)

        message = inputs['message']
        sentiment = inputs['sentiment']
        sentiment_trend = inputs.get('sentiment_trend', 'stable')

        # Create minimal ticket for escalation engine
        ticket = type('Ticket', (), {
            'message': message,
            'sentiment': sentiment,
            'subject': ''
        })()

        # Use escalation engine
        should_escalate, reason, priority = self.escalation_engine.analyze(ticket)

        # Adjust based on sentiment trend
        confidence = 0.9
        if sentiment_trend == "deteriorating" and not should_escalate:
            # Consider escalating if sentiment is getting worse
            if sentiment in ["frustrated", "angry"]:
                should_escalate = True
                reason = "Deteriorating customer sentiment"
                priority = "high"
                confidence = 0.85

        return {
            "should_escalate": should_escalate,
            "reason": reason,
            "priority": priority if should_escalate else "n/a",
            "confidence": confidence
        }


# ============================================================================
# SKILL 4: Channel Adaptation
# ============================================================================

CHANNEL_ADAPTATION_DEFINITION = SkillDefinition(
    metadata=SkillMetadata(
        name="channel_adaptation",
        description="Format response appropriately for target channel",
        category=SkillCategory.FORMATTING,
        priority=SkillPriority.HIGH,
        version="1.0.0",
        tags=["formatting", "channel", "adaptation"]
    ),
    when_to_use="Before sending any response to customer",
    inputs=[
        SkillInput(
            name="response_text",
            type="string",
            description="Raw response text to format",
            required=True
        ),
        SkillInput(
            name="target_channel",
            type="string",
            description="Target channel: gmail, whatsapp, webform",
            required=True
        ),
        SkillInput(
            name="customer_name",
            type="string",
            description="Customer name for personalization",
            required=True
        ),
        SkillInput(
            name="is_followup",
            type="boolean",
            description="Whether this is a follow-up message",
            required=False,
            default=False
        )
    ],
    outputs=[
        SkillOutput(
            name="formatted_response",
            type="string",
            description="Response formatted for target channel"
        ),
        SkillOutput(
            name="character_count",
            type="integer",
            description="Character count of formatted response"
        ),
        SkillOutput(
            name="tone",
            type="string",
            description="Applied tone: formal, semi-formal, casual"
        )
    ],
    examples=[
        {
            "input": {
                "response_text": "Here's how to export data: Go to Settings > Export",
                "target_channel": "whatsapp",
                "customer_name": "John",
                "is_followup": False
            },
            "output": {
                "formatted_response": "Hi John! Go to Settings > Export to export your data.",
                "character_count": 58,
                "tone": "casual"
            }
        }
    ]
)


class ChannelAdaptationSkill(Skill):
    """Channel adaptation skill implementation"""

    def __init__(self, response_generator):
        super().__init__(CHANNEL_ADAPTATION_DEFINITION)
        self.response_generator = response_generator

    def execute(self, **inputs) -> Dict[str, Any]:
        """Execute channel adaptation"""
        self.validate_inputs(**inputs)

        response_text = inputs['response_text']
        target_channel = inputs['target_channel']
        customer_name = inputs['customer_name']
        is_followup = inputs.get('is_followup', False)

        # Map channel names
        channel_map = {
            "gmail": "gmail",
            "email": "gmail",
            "whatsapp": "whatsapp",
            "webform": "webform",
            "web_form": "webform"
        }

        channel = channel_map.get(target_channel, target_channel)

        # Format response
        formatted = self.response_generator._format_response(
            channel,
            customer_name.split()[0],  # First name
            response_text,
            is_followup
        )

        # Determine tone
        tone_map = {
            "gmail": "formal",
            "webform": "semi-formal",
            "whatsapp": "casual"
        }

        return {
            "formatted_response": formatted,
            "character_count": len(formatted),
            "tone": tone_map.get(channel, "semi-formal")
        }


# ============================================================================
# SKILL 5: Customer Identification
# ============================================================================

CUSTOMER_IDENTIFICATION_DEFINITION = SkillDefinition(
    metadata=SkillMetadata(
        name="customer_identification",
        description="Identify and link customer across channels",
        category=SkillCategory.IDENTIFICATION,
        priority=SkillPriority.CRITICAL,
        version="1.0.0",
        tags=["identification", "cross-channel", "customer"]
    ),
    when_to_use="On every incoming message to identify customer",
    inputs=[
        SkillInput(
            name="email",
            type="string",
            description="Customer email address",
            required=False,
            default=None
        ),
        SkillInput(
            name="phone",
            type="string",
            description="Customer phone number",
            required=False,
            default=None
        ),
        SkillInput(
            name="name",
            type="string",
            description="Customer name",
            required=False,
            default="Customer"
        ),
        SkillInput(
            name="channel",
            type="string",
            description="Current channel",
            required=True
        )
    ],
    outputs=[
        SkillOutput(
            name="customer_id",
            type="string",
            description="Unified customer identifier"
        ),
        SkillOutput(
            name="is_new_customer",
            type="boolean",
            description="Whether this is a new customer"
        ),
        SkillOutput(
            name="merged_history",
            type="dict",
            description="Merged conversation history across channels"
        ),
        SkillOutput(
            name="confidence",
            type="float",
            description="Confidence in identification (0.0-1.0)"
        )
    ],
    examples=[
        {
            "input": {
                "email": "john@example.com",
                "phone": "+1-555-0123",
                "name": "John Doe",
                "channel": "gmail"
            },
            "output": {
                "customer_id": "john@example.com",
                "is_new_customer": False,
                "merged_history": {
                    "total_interactions": 5,
                    "channels_used": ["whatsapp", "gmail"]
                },
                "confidence": 1.0
            }
        }
    ]
)


class CustomerIdentificationSkill(Skill):
    """Customer identification skill implementation"""

    def __init__(self, conversation_manager):
        super().__init__(CUSTOMER_IDENTIFICATION_DEFINITION)
        self.conversation_manager = conversation_manager

    def execute(self, **inputs) -> Dict[str, Any]:
        """Execute customer identification"""
        self.validate_inputs(**inputs)

        email = inputs.get('email')
        phone = inputs.get('phone')
        name = inputs.get('name', 'Customer')
        channel = inputs['channel']

        # Create minimal ticket for conversation manager
        from datetime import datetime
        ticket = {
            'customer_email': email,
            'customer_phone': phone,
            'customer_name': name,
            'channel': channel,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Get or create customer profile
        profile = self.conversation_manager.get_or_create_customer(ticket)

        # Determine if new customer
        is_new = profile.total_interactions == 0

        # Calculate confidence
        confidence = 1.0 if email else 0.8  # Email is more reliable than phone

        # Build merged history
        merged_history = {
            "total_interactions": profile.total_interactions,
            "channels_used": profile.channels_used,
            "topics_discussed": profile.topics_discussed,
            "resolution_status": profile.resolution_status,
            "current_sentiment": profile.current_sentiment
        }

        return {
            "customer_id": profile.customer_id,
            "is_new_customer": is_new,
            "merged_history": merged_history,
            "confidence": confidence
        }


# ============================================================================
# Skills Registry
# ============================================================================

class SkillsRegistry:
    """Central registry for all skills"""

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.definitions: Dict[str, SkillDefinition] = {}

    def register(self, skill: Skill):
        """Register a skill"""
        name = skill.definition.metadata.name
        self.skills[name] = skill
        self.definitions[name] = skill.definition

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get skill by name"""
        return self.skills.get(name)

    def list_skills(self) -> List[str]:
        """List all registered skills"""
        return list(self.skills.keys())

    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a category"""
        return [
            skill for skill in self.skills.values()
            if skill.definition.metadata.category == category
        ]

    def export_manifest(self) -> Dict[str, Any]:
        """Export skills manifest as JSON"""
        return {
            "version": "1.0.0",
            "skills": {
                name: {
                    "metadata": {
                        "name": defn.metadata.name,
                        "description": defn.metadata.description,
                        "category": defn.metadata.category,
                        "priority": defn.metadata.priority,
                        "version": defn.metadata.version,
                        "tags": defn.metadata.tags
                    },
                    "when_to_use": defn.when_to_use,
                    "inputs": [
                        {
                            "name": inp.name,
                            "type": inp.type,
                            "description": inp.description,
                            "required": inp.required
                        }
                        for inp in defn.inputs
                    ],
                    "outputs": [
                        {
                            "name": out.name,
                            "type": out.type,
                            "description": out.description
                        }
                        for out in defn.outputs
                    ]
                }
                for name, defn in self.definitions.items()
            }
        }


if __name__ == "__main__":
    # Demo: Create skills registry
    print("=" * 80)
    print("SKILLS MANIFEST - Customer Success AI Agent")
    print("=" * 80)

    registry = SkillsRegistry()

    # Register skill definitions (without implementations for demo)
    registry.definitions = {
        "knowledge_retrieval": KNOWLEDGE_RETRIEVAL_DEFINITION,
        "sentiment_analysis": SENTIMENT_ANALYSIS_DEFINITION,
        "escalation_decision": ESCALATION_DECISION_DEFINITION,
        "channel_adaptation": CHANNEL_ADAPTATION_DEFINITION,
        "customer_identification": CUSTOMER_IDENTIFICATION_DEFINITION
    }

    # Export manifest
    manifest = registry.export_manifest()

    print("\nRegistered Skills:")
    for name, skill_def in manifest['skills'].items():
        print(f"\n{name}:")
        print(f"  Category: {skill_def['metadata']['category']}")
        print(f"  Priority: {skill_def['metadata']['priority']}")
        print(f"  Description: {skill_def['metadata']['description']}")
        print(f"  When to use: {skill_def['when_to_use']}")
        print(f"  Inputs: {len(skill_def['inputs'])}")
        print(f"  Outputs: {len(skill_def['outputs'])}")

    print("\n" + "=" * 80)
    print("Skills manifest created successfully!")
    print("=" * 80)
