-- LLM Council Database Schema for Supabase
-- Migration: 001_initial_schema
--
-- This migration creates all tables for the LLM Council application.
-- Run this in the Supabase SQL Editor to set up your database.
--
-- Note: SQLAlchemy models will auto-create tables on app startup,
-- but running this migration first ensures proper RLS policies.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- USER SETTINGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    council_models JSONB DEFAULT '[]',
    chairman_model VARCHAR(255),
    enhanced_features JSONB DEFAULT '{"web_search": true, "code_execution": true, "memory": true}',
    personas JSONB DEFAULT '{}',
    custom_personas JSONB DEFAULT '{}',
    budget_config JSONB DEFAULT '{}',
    custom_instructions TEXT,
    theme VARCHAR(20) DEFAULT 'light',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- USER API KEYS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    encrypted_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- ============================================
-- PROJECTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_prompt TEXT,
    council_config JSONB,
    knowledge_base JSONB DEFAULT '[]',
    memory JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) DEFAULT 'New Conversation',
    folder_id VARCHAR(50),
    tags TEXT[] DEFAULT '{}',
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_user_created ON conversations(user_id, created_at);

-- ============================================
-- MESSAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_index INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    message_type VARCHAR(20) DEFAULT 'council',
    content TEXT,
    stage1 JSONB,
    stage2 JSONB,
    stage3 JSONB,
    extra_data JSONB,
    thinking TEXT,
    model VARCHAR(100),
    usage_info JSONB,
    attached_files TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_conversation_index ON messages(conversation_id, message_index);

-- ============================================
-- FOLDERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS folders (
    id VARCHAR(50) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(10) DEFAULT '#4a90e2',
    icon VARCHAR(50) DEFAULT 'folder',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_folders_user_id ON folders(user_id);

-- ============================================
-- REFRESH TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    device_info TEXT,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- ============================================
-- RATINGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_index INTEGER NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    query_category VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, conversation_id, message_index, model_id)
);

CREATE INDEX idx_ratings_user_id ON ratings(user_id);

-- ============================================
-- USAGE ANALYTICS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS usage_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost FLOAT DEFAULT 0.0,
    request_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_user_date ON usage_analytics(user_id, request_date);

-- ============================================
-- SYSTEM CONFIG TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- TEAMS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_teams_owner_id ON teams(owner_id);

-- ============================================
-- TEAM MEMBERSHIPS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS team_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member',
    invited_by UUID,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

CREATE INDEX idx_team_memberships_team_id ON team_memberships(team_id);
CREATE INDEX idx_team_memberships_user_id ON team_memberships(user_id);

-- ============================================
-- TEAM CONVERSATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS team_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    shared_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shared_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(team_id, conversation_id)
);

CREATE INDEX idx_team_conversations_team_id ON team_conversations(team_id);

-- ============================================
-- API KEYS TABLE (Public API access)
-- ============================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(10) NOT NULL,
    scopes TEXT[] DEFAULT '{}',
    rate_limit INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- ============================================
-- PROMPT TEMPLATES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    category VARCHAR(50),
    is_public BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_user_category ON prompt_templates(user_id, category);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;

-- For backend access (service role bypasses RLS)
-- These policies allow the backend to access all data
-- The backend uses its own auth system, not Supabase Auth

CREATE POLICY "Backend full access" ON users FOR ALL USING (true);
CREATE POLICY "Backend full access" ON user_settings FOR ALL USING (true);
CREATE POLICY "Backend full access" ON user_api_keys FOR ALL USING (true);
CREATE POLICY "Backend full access" ON projects FOR ALL USING (true);
CREATE POLICY "Backend full access" ON conversations FOR ALL USING (true);
CREATE POLICY "Backend full access" ON messages FOR ALL USING (true);
CREATE POLICY "Backend full access" ON folders FOR ALL USING (true);
CREATE POLICY "Backend full access" ON refresh_tokens FOR ALL USING (true);
CREATE POLICY "Backend full access" ON ratings FOR ALL USING (true);
CREATE POLICY "Backend full access" ON usage_analytics FOR ALL USING (true);
CREATE POLICY "Backend full access" ON teams FOR ALL USING (true);
CREATE POLICY "Backend full access" ON team_memberships FOR ALL USING (true);
CREATE POLICY "Backend full access" ON team_conversations FOR ALL USING (true);
CREATE POLICY "Backend full access" ON api_keys FOR ALL USING (true);
CREATE POLICY "Backend full access" ON prompt_templates FOR ALL USING (true);
CREATE POLICY "Backend full access" ON system_config FOR ALL USING (true);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at
    BEFORE UPDATE ON user_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_api_keys_updated_at
    BEFORE UPDATE ON user_api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at
    BEFORE UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- INSERT ANONYMOUS USER
-- ============================================
-- This user is used for unauthenticated sessions
INSERT INTO users (id, email, name, is_active, is_verified)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'anonymous-00000000-0000-0000-0000-000000000000@local',
    'Anonymous',
    TRUE,
    TRUE
) ON CONFLICT (id) DO NOTHING;

-- Insert default settings for anonymous user
INSERT INTO user_settings (user_id, council_models, chairman_model)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    '["openai/gpt-4o", "google/gemini-2.5-flash", "anthropic/claude-sonnet-4", "x-ai/grok-3"]',
    'google/gemini-2.5-flash'
) ON CONFLICT (user_id) DO NOTHING;

-- Insert default folders for anonymous user
INSERT INTO folders (id, user_id, name, color, icon) VALUES
    ('clients', '00000000-0000-0000-0000-000000000000', 'Clients', '#4a90e2', 'briefcase'),
    ('internal', '00000000-0000-0000-0000-000000000000', 'Internal', '#9b59b6', 'users'),
    ('archive', '00000000-0000-0000-0000-000000000000', 'Archive', '#95a5a6', 'archive'),
    ('favorites', '00000000-0000-0000-0000-000000000000', 'Favorites', '#f39c12', 'star')
ON CONFLICT (id) DO NOTHING;
