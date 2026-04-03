-- ============================================================================
-- Customer Success CRM Database Schema
-- PostgreSQL 14+ with pgvector extension
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE customer_tier AS ENUM ('free', 'pro', 'enterprise');
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'waiting_customer', 'resolved', 'closed');
CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'urgent');
CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');
CREATE TYPE channel_type AS ENUM ('email', 'whatsapp', 'web_form', 'slack', 'phone');
CREATE TYPE escalation_status AS ENUM ('pending', 'assigned', 'in_progress', 'resolved');
CREATE TYPE notification_type AS ENUM ('escalation', 'ticket', 'alert', 'system');

-- ============================================================================
-- CUSTOMERS TABLE
-- Core customer information
-- ============================================================================

CREATE TABLE customers (
    id VARCHAR(50) PRIMARY KEY DEFAULT ('cust_' || uuid_generate_v4()::text),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    tier customer_tier NOT NULL DEFAULT 'free',
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',

    -- Metadata
    company VARCHAR(255),
    industry VARCHAR(100),
    employee_count INTEGER,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Flexible metadata storage
    metadata JSONB DEFAULT '{}',

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for customers
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_tier ON customers(tier);
CREATE INDEX idx_customers_active ON customers(is_active) WHERE is_active = true;
CREATE INDEX idx_customers_created_at ON customers(created_at);
CREATE INDEX idx_customers_metadata ON customers USING gin(metadata);

-- ============================================================================
-- CUSTOMER_IDENTIFIERS TABLE
-- Multiple identifiers per customer (phone, external IDs, etc.)
-- ============================================================================

CREATE TABLE customer_identifiers (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,

    identifier_type VARCHAR(50) NOT NULL,  -- 'phone', 'whatsapp', 'slack_user_id', 'external_crm_id'
    identifier_value VARCHAR(255) NOT NULL,

    is_primary BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(identifier_type, identifier_value)
);

-- Indexes for customer_identifiers
CREATE INDEX idx_customer_identifiers_customer_id ON customer_identifiers(customer_id);
CREATE INDEX idx_customer_identifiers_type_value ON customer_identifiers(identifier_type, identifier_value);
CREATE INDEX idx_customer_identifiers_primary ON customer_identifiers(customer_id, is_primary) WHERE is_primary = true;

-- ============================================================================
-- CONVERSATIONS TABLE
-- Tracks conversation threads across channels
-- ============================================================================

CREATE TABLE conversations (
    id VARCHAR(50) PRIMARY KEY DEFAULT ('conv_' || uuid_generate_v4()::text),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,

    channel channel_type NOT NULL,
    subject VARCHAR(500),

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_escalated BOOLEAN DEFAULT false,
    assigned_to VARCHAR(100),  -- Human agent if escalated

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for conversations
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_channel ON conversations(channel);
CREATE INDEX idx_conversations_active ON conversations(is_active) WHERE is_active = true;
CREATE INDEX idx_conversations_escalated ON conversations(is_escalated) WHERE is_escalated = true;
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);

-- ============================================================================
-- MESSAGES TABLE
-- Individual messages within conversations
-- ============================================================================

CREATE TABLE messages (
    id VARCHAR(50) PRIMARY KEY DEFAULT ('msg_' || uuid_generate_v4()::text),
    conversation_id VARCHAR(50) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,

    direction message_direction NOT NULL,
    channel channel_type NOT NULL,

    -- Content
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',  -- 'text', 'html', 'markdown'

    -- Metadata
    metadata JSONB DEFAULT '{}',  -- Attachments, formatting, channel-specific data

    -- Processing
    is_processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_time_ms INTEGER,

    -- Agent info (for outbound messages)
    agent_version VARCHAR(50),
    tools_used TEXT[],

    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for messages
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_customer_id ON messages(customer_id);
CREATE INDEX idx_messages_channel ON messages(channel);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_sent_at ON messages(sent_at DESC);
CREATE INDEX idx_messages_unprocessed ON messages(is_processed) WHERE is_processed = false;
CREATE INDEX idx_messages_metadata ON messages USING gin(metadata);

-- ============================================================================
-- TICKETS TABLE
-- Support ticket tracking system
-- ============================================================================

CREATE TABLE tickets (
    id VARCHAR(50) PRIMARY KEY DEFAULT ('TKT_' || LPAD(nextval('ticket_id_seq')::text, 6, '0')),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id VARCHAR(50) REFERENCES conversations(id) ON DELETE SET NULL,

    -- Ticket details
    subject VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),

    -- Status and priority
    status ticket_status NOT NULL DEFAULT 'open',
    priority ticket_priority NOT NULL DEFAULT 'medium',

    -- Assignment
    assigned_to VARCHAR(100),
    assigned_at TIMESTAMP WITH TIME ZONE,

    -- Resolution
    resolution TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),

    -- SLA tracking
    first_response_at TIMESTAMP WITH TIME ZONE,
    first_response_time_minutes INTEGER,
    resolution_time_minutes INTEGER,

    -- Metadata
    tags TEXT[],
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Sequence for ticket IDs
CREATE SEQUENCE ticket_id_seq START 1;

-- Indexes for tickets
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_conversation_id ON tickets(conversation_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX idx_tickets_open ON tickets(status) WHERE status IN ('open', 'in_progress');
CREATE INDEX idx_tickets_tags ON tickets USING gin(tags);
CREATE INDEX idx_tickets_category ON tickets(category);

-- ============================================================================
-- KNOWLEDGE_BASE TABLE
-- Documentation and help articles with vector embeddings
-- ============================================================================

CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,

    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),

    -- SEO and search
    slug VARCHAR(255) UNIQUE,
    keywords TEXT[],

    -- Vector embedding for semantic search (1536 dimensions for OpenAI embeddings)
    embedding vector(1536),

    -- Full-text search
    search_vector tsvector,

    -- Metadata
    author VARCHAR(255),
    tags TEXT[],
    related_article_ids INTEGER[],

    -- Status
    is_published BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,

    -- Analytics
    view_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,

    -- Versioning
    version INTEGER DEFAULT 1,
    previous_version_id INTEGER REFERENCES knowledge_base(id),

    -- Timestamps
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for knowledge_base
CREATE INDEX idx_kb_category ON knowledge_base(category);
CREATE INDEX idx_kb_published ON knowledge_base(is_published) WHERE is_published = true;
CREATE INDEX idx_kb_search_vector ON knowledge_base USING gin(search_vector);
CREATE INDEX idx_kb_embedding ON knowledge_base USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_kb_tags ON knowledge_base USING gin(tags);
CREATE INDEX idx_kb_keywords ON knowledge_base USING gin(keywords);
CREATE INDEX idx_kb_updated_at ON knowledge_base(updated_at DESC);

-- Trigger to automatically update search_vector
CREATE OR REPLACE FUNCTION kb_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.keywords, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER kb_search_vector_trigger
    BEFORE INSERT OR UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION kb_search_vector_update();

-- ============================================================================
-- CHANNEL_CONFIGS TABLE
-- Configuration for different communication channels
-- ============================================================================

CREATE TABLE channel_configs (
    id SERIAL PRIMARY KEY,

    channel channel_type NOT NULL UNIQUE,

    -- Configuration
    is_enabled BOOLEAN DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}',  -- Channel-specific settings

    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,

    -- Response settings
    default_response_timeout_seconds INTEGER DEFAULT 300,
    max_message_length INTEGER,
    supports_attachments BOOLEAN DEFAULT false,
    supports_rich_formatting BOOLEAN DEFAULT false,

    -- Credentials (encrypted)
    credentials JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for channel_configs
CREATE INDEX idx_channel_configs_enabled ON channel_configs(is_enabled) WHERE is_enabled = true;

-- ============================================================================
-- AGENT_METRICS TABLE
-- Performance tracking for the AI agent
-- ============================================================================

CREATE TABLE agent_metrics (
    id SERIAL PRIMARY KEY,

    -- Time period
    metric_date DATE NOT NULL,
    metric_hour INTEGER,  -- 0-23, NULL for daily aggregates

    -- Agent info
    agent_version VARCHAR(50) NOT NULL,
    channel channel_type,

    -- Volume metrics
    total_conversations INTEGER DEFAULT 0,
    total_messages_processed INTEGER DEFAULT 0,
    total_messages_sent INTEGER DEFAULT 0,

    -- Resolution metrics
    resolved_count INTEGER DEFAULT 0,
    escalated_count INTEGER DEFAULT 0,
    escalation_rate DECIMAL(5,2),  -- Percentage

    -- Performance metrics
    avg_response_time_ms INTEGER,
    avg_resolution_time_minutes INTEGER,
    avg_tools_per_conversation DECIMAL(5,2),

    -- Quality metrics
    customer_satisfaction_score DECIMAL(3,2),  -- 0-5 scale
    first_contact_resolution_rate DECIMAL(5,2),  -- Percentage

    -- Tool usage
    tool_usage_counts JSONB DEFAULT '{}',  -- {"search_kb": 150, "create_ticket": 45, ...}

    -- Error tracking
    error_count INTEGER DEFAULT 0,
    error_types JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(metric_date, metric_hour, agent_version, channel)
);

-- Indexes for agent_metrics
CREATE INDEX idx_agent_metrics_date ON agent_metrics(metric_date DESC);
CREATE INDEX idx_agent_metrics_version ON agent_metrics(agent_version);
CREATE INDEX idx_agent_metrics_channel ON agent_metrics(channel);
CREATE INDEX idx_agent_metrics_hourly ON agent_metrics(metric_date, metric_hour) WHERE metric_hour IS NOT NULL;

-- ============================================================================
-- ESCALATIONS TABLE
-- Tracks escalations to human agents
-- ============================================================================

CREATE TABLE escalations (
    id VARCHAR(50) PRIMARY KEY DEFAULT ('ESC_' || uuid_generate_v4()::text),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id VARCHAR(50) REFERENCES conversations(id) ON DELETE SET NULL,
    ticket_id VARCHAR(50) REFERENCES tickets(id) ON DELETE SET NULL,

    -- Escalation details
    reason TEXT NOT NULL,
    context TEXT NOT NULL,  -- Full conversation context
    priority ticket_priority NOT NULL DEFAULT 'medium',

    -- Status
    status escalation_status NOT NULL DEFAULT 'pending',

    -- Assignment
    assigned_to VARCHAR(100),
    assigned_at TIMESTAMP WITH TIME ZONE,

    -- Resolution
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,

    -- SLA
    response_time_minutes INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for escalations
CREATE INDEX idx_escalations_customer_id ON escalations(customer_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_priority ON escalations(priority);
CREATE INDEX idx_escalations_pending ON escalations(status) WHERE status = 'pending';
CREATE INDEX idx_escalations_created_at ON escalations(created_at DESC);

-- ============================================================================
-- NOTIFICATIONS TABLE
-- System notifications for human agents
-- ============================================================================

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,

    type notification_type NOT NULL,
    target VARCHAR(100) NOT NULL,  -- User ID, team name, or 'all'

    -- Content
    message TEXT NOT NULL,
    priority ticket_priority NOT NULL DEFAULT 'medium',

    -- Links
    related_entity_type VARCHAR(50),  -- 'escalation', 'ticket', 'conversation'
    related_entity_id VARCHAR(50),

    -- Status
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,

    -- Delivery
    delivery_channels channel_type[],
    delivered_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for notifications
CREATE INDEX idx_notifications_target ON notifications(target);
CREATE INDEX idx_notifications_unread ON notifications(is_read) WHERE is_read = false;
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================================================
-- INTERACTIONS TABLE
-- Tracks all customer interactions for history
-- ============================================================================

CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id VARCHAR(50) REFERENCES conversations(id) ON DELETE SET NULL,

    channel channel_type NOT NULL,

    -- Interaction summary
    summary TEXT NOT NULL,
    interaction_type VARCHAR(50),  -- 'support', 'sales', 'feedback', 'onboarding'

    -- Outcome
    outcome VARCHAR(50),  -- 'resolved', 'escalated', 'pending', 'abandoned'
    sentiment VARCHAR(20),  -- 'positive', 'neutral', 'negative'

    -- Duration
    duration_seconds INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for interactions
CREATE INDEX idx_interactions_customer_id ON interactions(customer_id);
CREATE INDEX idx_interactions_channel ON interactions(channel);
CREATE INDEX idx_interactions_created_at ON interactions(created_at DESC);
CREATE INDEX idx_interactions_outcome ON interactions(outcome);

-- ============================================================================
-- MESSAGE_QUEUE TABLE
-- Queue for outbound message delivery
-- ============================================================================

CREATE TABLE message_queue (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(50) NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(id) ON DELETE CASCADE,

    channel channel_type NOT NULL,

    -- Queue status
    status VARCHAR(20) NOT NULL DEFAULT 'queued',  -- 'queued', 'processing', 'sent', 'failed'

    -- Retry logic
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,

    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for message_queue
CREATE INDEX idx_message_queue_status ON message_queue(status);
CREATE INDEX idx_message_queue_pending ON message_queue(status, next_retry_at)
    WHERE status IN ('queued', 'failed');
CREATE INDEX idx_message_queue_channel ON message_queue(channel);
CREATE INDEX idx_message_queue_created_at ON message_queue(created_at DESC);

-- ============================================================================
-- AUDIT_LOG TABLE
-- Comprehensive audit trail for compliance
-- ============================================================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,

    -- Entity
    entity_type VARCHAR(50) NOT NULL,  -- 'customer', 'ticket', 'message', etc.
    entity_id VARCHAR(50) NOT NULL,

    -- Action
    action VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete', 'view'
    actor VARCHAR(100) NOT NULL,  -- User ID or 'system' or 'agent'
    actor_type VARCHAR(20) NOT NULL,  -- 'human', 'ai_agent', 'system'

    -- Changes
    old_values JSONB,
    new_values JSONB,

    -- Context
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit_log
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_identifiers_updated_at BEFORE UPDATE ON customer_identifiers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channel_configs_updated_at BEFORE UPDATE ON channel_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_escalations_updated_at BEFORE UPDATE ON escalations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active conversations with latest message
CREATE VIEW active_conversations_summary AS
SELECT
    c.id,
    c.customer_id,
    cu.name as customer_name,
    cu.email as customer_email,
    c.channel,
    c.subject,
    c.is_escalated,
    c.assigned_to,
    c.started_at,
    c.last_message_at,
    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count,
    (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY sent_at DESC LIMIT 1) as last_message
FROM conversations c
JOIN customers cu ON c.customer_id = cu.id
WHERE c.is_active = true
ORDER BY c.last_message_at DESC;

-- Open tickets summary
CREATE VIEW open_tickets_summary AS
SELECT
    t.id,
    t.customer_id,
    cu.name as customer_name,
    cu.email as customer_email,
    t.subject,
    t.status,
    t.priority,
    t.assigned_to,
    t.created_at,
    EXTRACT(EPOCH FROM (NOW() - t.created_at))/60 as age_minutes
FROM tickets t
JOIN customers cu ON t.customer_id = cu.id
WHERE t.status IN ('open', 'in_progress', 'waiting_customer')
ORDER BY t.priority DESC, t.created_at ASC;

-- Agent performance daily summary
CREATE VIEW agent_performance_daily AS
SELECT
    metric_date,
    agent_version,
    channel,
    SUM(total_conversations) as total_conversations,
    SUM(resolved_count) as resolved_count,
    SUM(escalated_count) as escalated_count,
    AVG(escalation_rate) as avg_escalation_rate,
    AVG(avg_response_time_ms) as avg_response_time_ms,
    AVG(customer_satisfaction_score) as avg_csat
FROM agent_metrics
WHERE metric_hour IS NOT NULL
GROUP BY metric_date, agent_version, channel
ORDER BY metric_date DESC;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default channel configurations
INSERT INTO channel_configs (channel, is_enabled, config, max_message_length, supports_attachments, supports_rich_formatting) VALUES
('email', true, '{"smtp_host": "smtp.example.com", "smtp_port": 587}', 10000, true, true),
('whatsapp', true, '{"api_version": "v1", "business_account_id": ""}', 1000, true, false),
('web_form', true, '{"endpoint": "/api/v1/support"}', 5000, true, true);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE customers IS 'Core customer information and profiles';
COMMENT ON TABLE customer_identifiers IS 'Multiple identifiers per customer across channels';
COMMENT ON TABLE conversations IS 'Conversation threads across all channels';
COMMENT ON TABLE messages IS 'Individual messages within conversations';
COMMENT ON TABLE tickets IS 'Support ticket tracking system';
COMMENT ON TABLE knowledge_base IS 'Documentation with vector embeddings for semantic search';
COMMENT ON TABLE channel_configs IS 'Configuration for communication channels';
COMMENT ON TABLE agent_metrics IS 'AI agent performance metrics and analytics';
COMMENT ON TABLE escalations IS 'Escalations to human agents';
COMMENT ON TABLE notifications IS 'System notifications for human agents';
COMMENT ON TABLE interactions IS 'Historical record of all customer interactions';
COMMENT ON TABLE message_queue IS 'Queue for outbound message delivery';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for compliance';
