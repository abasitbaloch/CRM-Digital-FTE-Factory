# Customer Success FTE - Specification Document

**Version**: 1.0.0  
**Status**: Crystallized  
**Last Updated**: 2026-04-03  
**Phase**: Post-Incubation

---

## Purpose

The Customer Success AI Agent (FTE) provides automated, context-aware customer support across multiple communication channels. The agent:

1. **Answers product questions** using comprehensive documentation
2. **Maintains conversation context** across channels and interactions
3. **Recognizes customers** regardless of communication channel (email, phone, web)
4. **Tracks sentiment** to detect customer satisfaction and escalation needs
5. **Routes intelligently** between AI handling and human escalation
6. **Adapts communication style** to match channel expectations

**Core Value Proposition**: Resolve 60%+ of customer inquiries automatically while ensuring critical issues reach human support with full context.

---

## Supported Channels

### 1. Email (Gmail)

**Identifier**: `gmail` or `email`

**Response Style**:
- **Tone**: Formal, professional
- **Structure**: 
  - Greeting with customer name
  - Acknowledgment of question
  - Detailed answer with step-by-step instructions
  - Offer for additional help
  - Professional sign-off
- **Formatting**: Full paragraphs, bullet points for lists, proper grammar

**Max Length**: 500-800 characters (3-5 paragraphs)

**Performance**: 66.7% AI resolution rate (tested on 18 tickets)

**Example**:
```
Hi Sarah,

Thanks for reaching out! I'd be happy to help.

Here's how to add team members to your project:

1. Open your project in TaskFlow Pro
2. Click the "Team" icon in the top right corner
3. Click "Add Members"
4. Enter email addresses or select from workspace members
5. Choose permission level (Viewer, Editor, Admin)
6. Click "Send Invitations"

Is there anything else I can help you with?

Best regards,
TechCorp Support Team
```

---

### 2. WhatsApp

**Identifier**: `whatsapp`

**Response Style**:
- **Tone**: Concise, friendly, conversational
- **Structure**:
  - Brief greeting (optional if urgent)
  - Direct answer to question
  - Quick follow-up if needed
- **Formatting**: Short sentences, line breaks for readability, minimal punctuation

**Max Length**: 200 characters (2-4 sentences)

**Performance**: 88.2% AI resolution rate (tested on 17 tickets) - **Best performing channel**

**Example**:
```
Hi Mike! Try these steps: 1. Update app 2. Restart device 3. Clear cache. Still crashing? Let me know!
```

**Critical Constraint**: Responses exceeding 200 characters must be truncated with "..." - users expect instant, scannable messages.

---

### 3. Web Form

**Identifier**: `webform` or `web_form`

**Response Style**:
- **Tone**: Semi-formal, balanced, helpful
- **Structure**:
  - Greeting with customer name
  - Direct answer to question
  - Additional context if helpful
  - Clear next steps or call-to-action
- **Formatting**: 2-3 paragraphs, clear and concise

**Max Length**: 300-500 characters (2-3 paragraphs)

**Performance**: 52.9% AI resolution rate (tested on 17 tickets) - **Needs improvement**

**Example**:
```
Hi Emma,

Thanks for reaching out about your billing question.

I can see the confusion. You're on the Professional plan ($24/user/month), not Starter. The $288 charge is for 12 users at the Professional rate.

Would you like me to process a downgrade to Starter?

Best,
TechCorp Support
```

---

## Scope

### In Scope - AI Can Handle

**Product Questions**:
- ✅ How-to questions covered in documentation
- ✅ Feature availability and capabilities
- ✅ Account setup and onboarding
- ✅ Basic troubleshooting (app crashes, slow performance, login issues)
- ✅ Integration setup instructions (when documented)
- ✅ Export/import data procedures
- ✅ Workflow customization
- ✅ Team member management
- ✅ Notification settings

**Billing Questions (Non-Dispute)**:
- ✅ How billing works (prorated charges, per-user pricing)
- ✅ Payment methods accepted
- ✅ Plan differences and features
- ✅ Upgrade/downgrade procedures
- ✅ Invoice explanations (when charges are correct)

**Account Management**:
- ✅ Password reset instructions
- ✅ 2FA setup
- ✅ Profile updates
- ✅ Workspace management

**Performance Target**: 60%+ of tickets handled without escalation

---

### Out of Scope - Must Escalate

**CRITICAL Priority (Escalate Immediately)**:

1. **Legal Threats**
   - Keywords: "lawyer", "legal action", "sue", "attorney", "court"
   - GDPR data deletion requests (Article 17)
   - Subpoenas or legal discovery
   - **Reason**: Legal liability, requires specialized handling
   - **Tested**: 100% detection rate on 3 test cases

2. **Angry Customers**
   - Sentiment: "angry" or "critical"
   - Threats to cancel, post negative reviews, report to authorities
   - ALL CAPS messages with negative content
   - **Reason**: Requires empathy, de-escalation skills, authority to offer solutions
   - **Tested**: 100% detection rate on 2 test cases

3. **Security Incidents**
   - Unauthorized account access
   - Suspected breaches
   - Account locked with urgent need
   - **Reason**: Immediate attention required, potential data exposure

**HIGH Priority (Escalate Within 4 Hours)**:

1. **Billing Disputes**
   - Customer disputes charge amount
   - Claims of duplicate charges
   - Requests for refunds (especially annual subscriptions)
   - **Reason**: Requires financial authority, may involve credits/refunds
   - **Tested**: 100% detection rate on 4 test cases

2. **Enterprise Inquiries**
   - Teams >50 users
   - Custom pricing requests
   - SSO/SAML setup
   - Custom contract terms
   - **Reason**: High-value customers, complex requirements
   - **Tested**: 100% detection rate on 3 test cases

3. **Compliance & Security Documentation**
   - SOC 2 audit reports
   - Data Processing Agreements (DPA)
   - Security questionnaires
   - Data retention policies
   - **Reason**: Legal/compliance expertise required
   - **Tested**: 100% detection rate on 3 test cases

**MEDIUM Priority (Escalate Within 24 Hours)**:

1. **Complex Technical Issues**
   - Issue persists after documented troubleshooting
   - Integration failures after multiple attempts
   - Data loss or corruption
   - API/webhook issues
   - **Reason**: Requires engineering investigation

2. **Account Changes Requiring Approval**
   - Trial extensions beyond 14 days
   - Account ownership transfers
   - Bulk user management (>20 users)
   - **Reason**: Business judgment required

**Escalation Rate**: Currently 30.8% (target: <20%) - needs tuning to reduce false escalations

---

## Tools

### MCP Server Tools (7 Tools)

#### 1. search_knowledge_base

**Purpose**: Search product documentation for relevant information to answer customer questions.

**Inputs**:
- `query` (string, required): Search query text
- `max_results` (integer, optional): Maximum results (default: 3)

**Outputs**:
- `results` (list): Documentation snippets with relevance scores
- `results_count` (integer): Number of results found
- `confidence` (float): Confidence in top result (0.0-1.0)

**Constraints**:
- Maximum 5 results per query
- Results limited to 500 characters each
- Keyword-based search (not semantic)
- Response time: <20ms

**Performance**: 90% confidence on relevant queries

---

#### 2. create_ticket

**Purpose**: Create support ticket with automatic agent response and channel tracking.

**Inputs**:
- `customer_id` (string, required): Email or phone number
- `issue` (string, required): Customer's issue description
- `priority` (string, required): low, medium, high, critical
- `channel` (string, required): email, whatsapp, web_form

**Outputs**:
- `ticket` (dict): Complete ticket details with ID
- `agent_response` (string): Generated response
- `escalated` (boolean): Whether ticket was escalated
- `escalation_reason` (string): Reason if escalated

**Constraints**:
- Ticket ID format: TICKET-XXXXXX (6 digits)
- Automatic escalation detection
- Conversation memory integration
- Response time: <100ms

**Performance**: 69.2% AI resolution rate

---

#### 3. get_customer_history

**Purpose**: Retrieve complete customer interaction history across ALL channels.

**Inputs**:
- `customer_id` (string, required): Email or phone number

**Outputs**:
- `customer` (dict): Customer profile
- `conversation_summary` (dict): Topics, status, sentiment
- `channel_usage` (dict): Channels used, switches
- `conversations` (list): Complete message history

**Constraints**:
- Links phone numbers to email addresses
- Returns up to 100 messages per customer
- Response time: <10ms

**Performance**: 100% cross-channel recognition accuracy

---

#### 4. escalate_to_human

**Purpose**: Manually escalate ticket to human support with reason.

**Inputs**:
- `ticket_id` (string, required): Ticket to escalate
- `reason` (string, required): Escalation reason

**Outputs**:
- `escalation_id` (string): Unique escalation ID (ESC-XXXXXX)
- `escalated_at` (timestamp): Escalation timestamp
- `ticket_status` (string): Updated status

**Constraints**:
- Cannot un-escalate once escalated
- Escalation ID format: ESC-XXXXXX (6 digits)
- Response time: <5ms

---

#### 5. send_response

**Purpose**: Send response to ticket via appropriate channel.

**Inputs**:
- `ticket_id` (string, required): Target ticket
- `message` (string, required): Response message
- `channel` (string, required): Delivery channel

**Outputs**:
- `delivery_status` (dict): Delivery confirmation
- `message_sent` (string): Message preview
- `ticket_status` (string): Updated ticket status

**Constraints**:
- Channel-specific formatting applied automatically
- Maximum message length enforced per channel
- Response time: <5ms
- **Note**: Currently simulated delivery (not real channel integration)

---

#### 6. get_ticket_status

**Purpose**: Query current status and details of a ticket.

**Inputs**:
- `ticket_id` (string, required): Ticket to query

**Outputs**:
- `ticket` (dict): Complete ticket details including responses

**Constraints**:
- Response time: <1ms
- Returns all ticket metadata

---

#### 7. get_statistics

**Purpose**: Retrieve system-wide statistics for monitoring and reporting.

**Inputs**: None

**Outputs**:
- `customer_statistics` (dict): Customer metrics
- `ticket_statistics` (dict): Ticket metrics by status, priority, channel
- `escalations` (dict): Escalation counts

**Constraints**:
- Real-time calculation
- Response time: <20ms

---

### Skills System (5 Skills)

#### 1. Customer Identification (CRITICAL)

**Purpose**: Identify and link customers across channels for unified conversation history.

**Inputs**: email, phone, name, channel

**Outputs**: customer_id, is_new_customer, merged_history, confidence

**Constraints**:
- Email is primary identifier
- Phone numbers mapped to email when both available
- Confidence: 1.0 for email, 0.8 for phone-only

**Performance**: 100% accuracy in cross-channel recognition

---

#### 2. Sentiment Analysis (CRITICAL)

**Purpose**: Analyze customer message sentiment and track emotional trends.

**Inputs**: message, previous_sentiment

**Outputs**: sentiment, confidence, sentiment_trend, indicators

**Constraints**:
- 5 sentiment types: neutral, positive, frustrated, angry, confused
- Keyword-based detection (not AI-powered)
- Trend: improving, stable, deteriorating

**Performance**: 85%+ accuracy on test cases

---

#### 3. Knowledge Retrieval (HIGH)

**Purpose**: Search product documentation with conversation context.

**Inputs**: query, max_results, conversation_topics

**Outputs**: results, results_count, confidence

**Constraints**:
- Keyword-based search
- Enhanced with conversation topics
- Maximum 5 results

**Performance**: 90% confidence on relevant queries

---

#### 4. Escalation Decision (CRITICAL)

**Purpose**: Decide if ticket requires human escalation based on content and sentiment.

**Inputs**: message, sentiment, sentiment_trend, conversation_context

**Outputs**: should_escalate, reason, priority, confidence

**Constraints**:
- Rule-based detection
- Sentiment-aware (escalates on deteriorating trends)
- 3 priority levels: critical, high, medium

**Performance**: 90% confidence in decisions

---

#### 5. Channel Adaptation (HIGH)

**Purpose**: Format responses appropriately for target channel.

**Inputs**: response_text, target_channel, customer_name, is_followup

**Outputs**: formatted_response, character_count, tone

**Constraints**:
- 3 tones: formal (email), semi-formal (web), casual (WhatsApp)
- Enforces channel max lengths
- Personalizes with customer name

**Performance**: 100% formatting accuracy

---

## Performance Requirements

### Response Time

- **Knowledge Base Search**: <20ms (p95)
- **Ticket Creation**: <100ms (p95)
- **Customer History Lookup**: <10ms (p95)
- **Escalation**: <5ms (p95)
- **Send Response**: <5ms (p95)
- **Statistics**: <20ms (p95)

**Tested**: All tools meet performance targets

---

### Accuracy

- **AI Resolution Rate**: ≥60% (Current: 69.2%) ✅
- **Cross-Channel Recognition**: ≥95% (Current: 100%) ✅
- **Sentiment Detection**: ≥80% (Current: 85%) ✅
- **Escalation Detection**: ≥90% (Current: 90%) ✅
- **Channel Formatting**: 100% (Current: 100%) ✅

---

### Scalability

- **Concurrent Tickets**: 100+ simultaneous
- **Customer Database**: 10,000+ customers (current JSON storage)
- **Conversation History**: 100 messages per customer
- **Memory Overhead**: <5ms per ticket ✅

**Production Recommendation**: Migrate to PostgreSQL for >10,000 customers

---

### Availability

- **Uptime Target**: 99.5%
- **Error Rate**: <1%
- **Graceful Degradation**: Continue with reduced functionality if memory unavailable

---

## Guardrails

### 1. Escalation Safety

**MUST NEVER**:
- Skip escalation for legal threats
- Skip escalation for angry customers (sentiment: angry)
- Skip escalation for billing disputes
- Skip escalation for security incidents

**MUST ALWAYS**:
- Escalate when confidence <0.7 on critical decisions
- Escalate when sentiment trend is "deteriorating" for 2+ messages
- Escalate when customer explicitly requests human support
- Preserve full conversation context in escalation

**Monitoring**: Track false escalation rate (target: <5%)

---

### 2. Data Privacy

**MUST NEVER**:
- Log credit card numbers, passwords, or sensitive PII
- Share customer data across customer profiles
- Retain data beyond retention policy (90 days for resolved tickets)

**MUST ALWAYS**:
- Encrypt conversation history at rest
- Support GDPR deletion requests within 30 days
- Anonymize data for analytics

**Compliance**: GDPR, SOC 2 Type II

---

### 3. Response Quality

**MUST NEVER**:
- Provide incorrect product information
- Make promises about features not in documentation
- Offer discounts or credits (escalate to human)
- Claim WCAG compliance without manual testing

**MUST ALWAYS**:
- Base responses on product documentation
- Acknowledge uncertainty ("Let me connect you with a specialist")
- Maintain professional tone
- Respect channel formatting rules

**Quality Checks**:
- Response must be <500 chars for email
- Response must be <200 chars for WhatsApp
- Response must include customer name
- Response must match channel tone

---

### 4. Context Preservation

**MUST ALWAYS**:
- Maintain conversation history across channels
- Include previous messages in context (last 5 messages)
- Track topics discussed
- Preserve sentiment history

**MUST NEVER**:
- Lose conversation context on channel switch
- Forget customer identity
- Reset conversation state without reason

**Performance**: <5ms overhead for context retrieval

---

### 5. Rate Limiting

**Limits**:
- 10 tickets per customer per hour
- 100 knowledge base searches per customer per hour
- 1000 total tickets per hour (system-wide)

**Behavior on Limit**:
- Return error with retry-after header
- Log rate limit violations
- Alert on sustained violations

---

### 6. Error Handling

**On Tool Failure**:
- Return structured error response
- Log error with context
- Escalate to human if critical path
- Never expose internal errors to customer

**On Memory Failure**:
- Continue without conversation context
- Log warning
- Notify operations team

**On Documentation Unavailable**:
- Escalate to human
- Return "I'll connect you with a specialist" message

---

## Edge Cases Discovered

### 1. Cross-Channel Customer Recognition

**Issue**: Customer starts on WhatsApp (phone only), continues on Gmail (email only)

**Solution**: Map phone to email when both provided, use phone-to-email lookup table

**Status**: ✅ Solved - 100% accuracy

---

### 2. Sentiment Deterioration

**Issue**: Customer sentiment worsens from "confused" → "frustrated" → "angry"

**Solution**: Track sentiment history, escalate on deteriorating trend even if individual message doesn't trigger

**Status**: ✅ Solved - Escalation Decision skill monitors trends

---

### 3. WhatsApp Message Length

**Issue**: Detailed responses exceed 200 character limit

**Solution**: Truncate with "..." and offer to send details via email

**Status**: ✅ Solved - Channel Adaptation skill enforces limits

---

### 4. Billing Confusion vs. Dispute

**Issue**: Customer confused about charge (not disputing) vs. customer disputing charge

**Solution**: Escalate if customer uses words like "wrong", "error", "overcharged", "dispute"

**Status**: ✅ Solved - Escalation rules distinguish confusion from dispute

---

### 5. Multiple Topics in One Message

**Issue**: Customer asks about offline mode, Slack integration, and enterprise pricing in one message

**Solution**: Extract all topics, answer what we can, escalate if any topic requires escalation

**Status**: ✅ Solved - Topic extraction tracks all topics, escalation triggers on any match

---

### 6. Follow-up Question Recognition

**Issue**: Customer says "Thanks! Can I also..." - is this a new question or follow-up?

**Solution**: Detect follow-up indicators ("also", "and", "what about"), adjust greeting accordingly

**Status**: ✅ Solved - Channel Adaptation skill detects follow-ups

---

### 7. False Escalations

**Issue**: 30.8% escalation rate exceeds 20% target

**Root Cause**: Enterprise keywords ("150 users", "team of") trigger escalation even for simple questions

**Solution**: Refine escalation rules to require multiple indicators, not single keyword

**Status**: ⚠️ Needs tuning - Reduce false positive rate

---

## Metrics Dashboard

### Real-Time Metrics

- Total tickets processed
- AI resolution rate (by channel)
- Escalation rate (by priority)
- Average response time
- Customer satisfaction (when available)

### Historical Metrics

- Tickets per day/week/month
- Resolution rate trends
- Top topics discussed
- Escalation reasons distribution
- Sentiment distribution

### Alerts

- Escalation rate >35% (sustained 1 hour)
- AI resolution rate <55% (sustained 1 hour)
- Response time >200ms (p95)
- Error rate >2%
- Memory system unavailable

---

## Testing Requirements

### Unit Tests

- Each skill tested independently
- Each MCP tool tested independently
- Conversation memory tested with edge cases
- Escalation rules tested with all trigger types

**Coverage**: 100% of core functions

---

### Integration Tests

- Multi-turn conversations
- Cross-channel scenarios
- Escalation workflows
- Memory persistence

**Test Suite**: `test_agent.py`, `test_mcp.py`, `skills_integration.py`

---

### Performance Tests

- 100 concurrent tickets
- 10,000 customer database
- Memory overhead measurement
- Response time percentiles

**Benchmark**: All tools <100ms (p95)

---

### Acceptance Criteria

- ✅ AI resolution rate ≥60%
- ✅ Cross-channel recognition ≥95%
- ✅ Escalation detection ≥90%
- ✅ Response time <100ms (p95)
- ⚠️ Escalation rate <20% (currently 30.8%)

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing
- [ ] Documentation complete
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] Escalation rules tuned (reduce to <20%)

### Deployment

- [ ] Database migration (JSON → PostgreSQL)
- [ ] MCP server deployed
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Backup strategy implemented

### Post-Deployment

- [ ] Monitor escalation rate
- [ ] Track AI resolution rate
- [ ] Collect customer feedback
- [ ] Tune escalation rules based on data
- [ ] Iterate on response quality

---

## Future Enhancements

### Phase 2 (Next 30 Days)

1. **Claude API Integration**
   - Replace template responses with AI-generated
   - Improve edge case handling
   - Target: 75% AI resolution rate

2. **Real Channel Integration**
   - Gmail API for email
   - WhatsApp Business API
   - Web form webhooks

3. **Database Migration**
   - PostgreSQL for scalability
   - Support 100,000+ customers

### Phase 3 (60-90 Days)

1. **Semantic Search**
   - Embeddings-based documentation search
   - Better relevance matching

2. **Predictive Escalation**
   - ML model to predict escalation risk
   - Proactive escalation

3. **Multi-Language Support**
   - Detect customer language
   - Respond in their language

---

## Appendix

### Test Data Summary

- **Total Sample Tickets**: 52
- **Channels**: Gmail (18), WhatsApp (17), Web Form (17)
- **Sentiments**: Neutral (27), Frustrated (8), Positive (7), Angry (2), Confused (2)
- **Escalations**: 16 (30.8%)
- **AI Handled**: 36 (69.2%)

### Performance Baselines

- **WhatsApp**: 88.2% AI handled (best)
- **Gmail**: 66.7% AI handled
- **Web Form**: 52.9% AI handled (needs improvement)

### Key Files

- `agent.py` - Core agent implementation
- `conversation_memory.py` - Memory system
- `mcp_server.py` - MCP server
- `skills_manifest.py` - Skills definitions
- `skills_integration.py` - Skills orchestration

---

**Document Status**: ✅ Crystallized  
**Ready for**: Production deployment after escalation tuning  
**Next Review**: After 1000 production tickets processed
