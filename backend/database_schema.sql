-- =============================================================================
-- BaseChat Database Schema for Chat History Management
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- User Management Tables
-- =============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    default_model VARCHAR(50) DEFAULT 'gpt-3.5-turbo',
    default_temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id)
);

-- =============================================================================
-- Chat History Tables
-- =============================================================================

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    model_type VARCHAR(50) NOT NULL, -- 'openai', 'vllm'
    model_name VARCHAR(100) NOT NULL, -- 'gpt-4', 'llama2-7b'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    mcp_tools_used JSONB, -- MCP tools usage record
    metadata JSONB, -- Additional metadata (temperature, max_tokens, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Indexes for messages table
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- Indexes for chat_sessions table
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_model_type ON chat_sessions(model_type);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- =============================================================================
-- Sample Data for Testing
-- =============================================================================

-- Insert sample user (password: test123)
INSERT INTO users (id, username, email, password_hash) VALUES 
    ('550e8400-e29b-41d4-a716-446655440000', 'testuser', 'test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2.')
ON CONFLICT (username) DO NOTHING;

-- Insert sample user preferences
INSERT INTO user_preferences (user_id, default_model, default_temperature, max_tokens) VALUES 
    ('550e8400-e29b-41d4-a716-446655440000', 'gpt-3.5-turbo', 0.7, 1000)
ON CONFLICT (user_id) DO NOTHING;

-- Insert sample chat session
INSERT INTO chat_sessions (id, user_id, title, model_type, model_name) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'Sample Chat Session', 'openai', 'gpt-3.5-turbo')
ON CONFLICT DO NOTHING;

-- Insert sample messages
INSERT INTO messages (session_id, role, content, tokens_used, model_used) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 'user', 'Hello, how are you?', 7, 'gpt-3.5-turbo'),
    ('550e8400-e29b-41d4-a716-446655440001', 'assistant', 'Hello! I am doing well, thank you for asking. How can I help you today?', 15, 'gpt-3.5-turbo')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 