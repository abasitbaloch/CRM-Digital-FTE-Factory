# TechCorp SaaS - Escalation Rules

## Overview
This document defines when customer inquiries should be escalated from AI agent to human support representatives. The goal is to handle routine questions efficiently with AI while ensuring complex, sensitive, or high-risk situations receive appropriate human attention.

---

## Automatic Escalation Triggers

### 1. Pricing & Financial Disputes
**Trigger when:**
- Customer disputes a charge or mentions "wrong amount," "overcharged," "billing error"
- Requests for refunds (partial or full)
- Questions about custom Enterprise pricing or quotes
- Payment failures requiring manual intervention
- Requests to change payment terms (NET 30 to NET 60, etc.)
- Annual subscription refund requests

**Why:** Financial matters require human judgment, approval authority, and may involve legal/contractual considerations.

**Examples:**
- "I was charged twice this month"
- "Can we get a refund for the remaining months?"
- "Need a custom quote for 150 users"

---

### 2. Legal & Compliance Matters
**Trigger when:**
- Customer mentions: "lawyer," "legal action," "sue," "attorney," "court"
- GDPR data deletion requests (Article 17 "right to be forgotten")
- Requests for legal documents: DPA (Data Processing Agreement), BAA (Business Associate Agreement), MSA (Master Service Agreement)
- Compliance audit requests (SOC 2 reports, security questionnaires)
- Data breach notifications or security incident reports
- Subpoena or legal discovery requests

**Why:** Legal matters require specialized expertise and may have significant business/liability implications.

**Examples:**
- "I'm contacting my lawyer if this isn't resolved"
- "Under GDPR Article 17, I request deletion of my data"
- "We need a signed DPA for our legal team"

---

### 3. Negative Sentiment & Threats
**Trigger when:**
- Sentiment analysis detects "angry" or "critical" priority
- Customer threatens to cancel or mentions competitor switch
- Mentions of public complaints: "telling everyone," "posting on social media," "writing a review"
- ALL CAPS messages or excessive punctuation (!!!, ???)
- Words indicating extreme frustration: "unacceptable," "terrible," "worst," "horrible," "disgusting"
- Threats to report to regulatory bodies (BBB, FTC, consumer protection)

**Why:** Upset customers require empathy, de-escalation skills, and authority to offer solutions (discounts, credits, etc.).

**Examples:**
- "This is TERRIBLE SERVICE"
- "I'm canceling and telling everyone to avoid your company"
- "Absolutely unacceptable - legal action if not resolved immediately"

---

### 4. Enterprise & High-Value Accounts
**Trigger when:**
- Customer is on Enterprise plan (check account tier)
- Requests for Enterprise features: SSO setup, custom data residency, dedicated support
- Questions about SLAs, uptime guarantees, or service commitments
- Multi-year contract negotiations or renewals
- Requests involving >50 users or >$10K annual contract value
- Strategic partnership or integration discussions

**Why:** High-value customers expect white-glove service and may have complex needs requiring account management.

**Examples:**
- "We're an Enterprise customer trying to set up SAML SSO"
- "Need to discuss our contract renewal"
- "Interested in Enterprise plan for 150 people"

---

### 5. Security & Privacy Incidents
**Trigger when:**
- Reports of unauthorized account access or suspected breach
- Password reset issues after multiple failed attempts
- Account locked/suspended notifications
- Questions about data encryption, security certifications
- Requests for security documentation or penetration test results
- Reports of suspicious activity or potential vulnerabilities

**Why:** Security matters require immediate attention and specialized technical expertise.

**Examples:**
- "My account was accessed from a location I don't recognize"
- "Account locked - need urgent access for client presentation"
- "Found a potential security vulnerability in your API"

---

### 6. Technical Issues Beyond Documentation
**Trigger when:**
- Customer reports the same issue multiple times (>2 attempts)
- Issue persists after following documented troubleshooting steps
- Integration failures with third-party services (Slack, GitHub, etc.) after reconnection attempts
- API issues, webhook failures, or developer-focused problems
- Data loss or corruption reports
- Performance issues affecting multiple users or entire workspace
- Mobile app crashes that persist after reinstall

**Why:** Complex technical issues may require engineering investigation or escalation to product team.

**Examples:**
- "Followed all troubleshooting steps but Slack integration still not working"
- "Tasks aren't syncing - already tried logging out and back in"
- "API rate limits too low for our use case"

---

### 7. Account Changes Requiring Approval
**Trigger when:**
- Trial extension requests beyond standard 14 days
- Downgrade requests that may result in data loss
- Account ownership transfer requests
- Bulk user management (adding/removing >20 users at once)
- Requests to bypass system limitations or policies
- Custom contract terms or non-standard arrangements

**Why:** These require business judgment and may have revenue or operational implications.

**Examples:**
- "Can you extend our trial by another week?"
- "Need to transfer account ownership to new admin"
- "Downgrading from Professional to Starter - will we lose data?"

---

## Conditional Escalation (AI Should Attempt First)

### Billing Questions (Non-Dispute)
- **AI handles:** How billing works, explaining charges, prorated billing, payment methods accepted
- **Escalate if:** Customer disputes the explanation or insists on speaking to billing team

### Feature Requests
- **AI handles:** Acknowledge request, explain current workarounds, direct to feature request portal
- **Escalate if:** Customer is Enterprise tier or request is urgent/blocking their workflow

### General Product Questions
- **AI handles:** All questions answerable from product-docs.md
- **Escalate if:** Documentation doesn't cover the question or customer needs clarification after 2+ exchanges

---

## Do NOT Escalate (AI Should Handle)

### Routine Questions
- How-to questions covered in documentation
- Feature availability questions
- Password resets (provide self-service link)
- Basic troubleshooting (app crashes, slow performance, login issues)
- Account setup and onboarding
- Export data instructions
- Integration setup instructions (when documented)

### Positive Feedback
- Thank you messages
- Feature compliments
- Referral program inquiries
- General praise

### Low-Priority Inquiries
- Feature availability questions
- Language/localization availability
- Device compatibility questions
- Workflow customization questions

---

## Escalation Process

When escalating, the AI agent should:

1. **Log the escalation reason** in the ticket metadata
2. **Summarize the conversation** for the human agent (customer question, AI responses provided, reason for escalation)
3. **Set priority level:**
   - **Critical:** Legal threats, security incidents, angry customers, GDPR requests
   - **High:** Billing disputes, Enterprise customers, refund requests, compliance matters
   - **Medium:** Technical issues, trial extensions, account changes
   - **Low:** Feature requests, general questions requiring human judgment

4. **Notify the customer:**
   - **Gmail/Web Form:** "I've escalated your inquiry to our support team. A specialist will respond within [timeframe] via email."
   - **WhatsApp:** "Connecting you with our support team. You'll hear back within [timeframe]."

5. **Response time commitments:**
   - **Critical:** Within 2 hours (24/7)
   - **High:** Within 4 hours (business hours)
   - **Medium:** Within 24 hours
   - **Low:** Within 48 hours

---

## Edge Cases & Special Handling

### Multiple Issues in One Message
- If message contains both routine question AND escalation trigger → escalate entire conversation
- Example: "How do I export data? Also, I want a refund." → Escalate for refund, but provide export instructions in escalation summary

### Unclear Intent
- If sentiment is ambiguous or trigger words appear in non-threatening context → use judgment
- Example: "This is unacceptable... ly good! Love the new feature!" → Do NOT escalate

### VIP/Founder Requests
- If customer email domain matches known VIP list → automatic escalation regardless of question type
- Tag as "VIP" in escalation metadata

---

## Monitoring & Continuous Improvement

Track escalation metrics:
- **Escalation rate by channel** (target: <15% of total tickets)
- **False escalations** (tickets that could have been handled by AI)
- **Missed escalations** (tickets that should have been escalated but weren't)
- **Customer satisfaction** post-escalation

Review escalation rules quarterly and update based on:
- New product features or policy changes
- Patterns in false/missed escalations
- Customer feedback
- Support team capacity
