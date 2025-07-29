# BaseChat Backend

A production-ready microservice backend for conversational AI applications, built with FastAPI, LangGraph, OpenAI API, SQLAlchemy ORM, and Redis caching.

## 🏗️ Architecture

The backend follows a **microservice architecture** with three main services:

### 1. Main Backend Service (`main-backend`)
- **Port**: 8000
- **Purpose**: Orchestration, conversation management, caching, and chat history
- **Technologies**: FastAPI, LangGraph, LangChain, SQLAlchemy, Alembic, Redis
- **Features**:
  - Conversation state management
  - LangGraph workflow orchestration
  - SQLAlchemy ORM database management
  - Alembic database migrations
  - Redis-based caching system
  - Chat history and context management
  - User management and session tracking
  - Multi-modal input processing
  - Streaming responses
  - Cache monitoring and management

### 2. LLM Agent Service (`llm-agent`)
- **Port**: 8001
- **Purpose**: Direct LLM interactions with caching support
- **Technologies**: FastAPI, OpenAI API, vLLM (future)
- **Features**:
  - OpenAI API integration
  - vLLM support (local LLM)
  - Text generation and streaming
  - Model selection and configuration
  - Rate limiting and error handling
  - Cached response management

### 3. MCP Server (`mcp-server`)
- **Port**: 8002
- **Purpose**: Model Context Protocol tools
- **Technologies**: FastAPI, MCP
- **Features**:
  - Extensible tool system
  - Tool caching and optimization
  - Dynamic tool loading
  - Tool execution monitoring

## 🗄️ Database System

### SQLAlchemy ORM Integration
- **Models**: `app/models/database_models.py`
- **Service**: `app/services/sqlalchemy_service.py`
- **Features**:
  - Async database operations
  - Connection pooling
  - Automatic session management
  - Type-safe queries
  - Relationship mapping

### Database Schema
```sql
-- Users and Preferences
users (id, username, email, password_hash, is_active, created_at, updated_at)
user_preferences (user_id, default_model, default_temperature, max_tokens, created_at, updated_at)

-- Chat Sessions and Messages
chat_sessions (id, user_id, title, model_type, model_name, is_active, created_at, updated_at)
messages (id, session_id, role, content, tokens_used, model_used, mcp_tools_used, meta_info, created_at)
```

### Alembic Migrations
- **Configuration**: `alembic.ini`, `alembic/env.py`
- **Migrations**: `alembic/versions/`
- **Features**:
  - Automatic migration on startup
  - Version control for schema changes
  - Rollback support
  - Docker volume persistence

## 💬 Chat History System

### Features
- **User Management**: Create, update, and manage user accounts
- **Session Management**: Create and manage chat sessions
- **Message Storage**: Store and retrieve conversation messages
- **History Retrieval**: Get user conversation history
- **Statistics**: User activity and usage statistics

### API Endpoints
- `POST /history/users` - Create new user
- `GET /history/users/{user_id}` - Get user details
- `POST /history/sessions` - Create chat session
- `GET /history/users/{user_id}/sessions` - Get user sessions
- `POST /history/messages` - Save message
- `GET /history/sessions/{session_id}/messages` - Get session messages
- `POST /history/chat/with-history` - Chat with history context
- `GET /history/users/{user_id}/stats` - Get user statistics

## 🏭 Factory Pattern Implementation

Both services implement the **Factory Pattern** for improved maintainability, testability, and dependency injection:

### App Factory
- **Location**: `app/factory/app_factory.py`
- **Purpose**: Creates and configures FastAPI applications
- **Features**:
  - Centralized application creation
  - Middleware configuration
  - Route registration
  - Exception handling
  - Health checks
  - CORS configuration
  - Cache API integration
  - Database initialization
  - Alembic migration automation

### Service Factory
- **Location**: `app/factory/service_factory.py`
- **Purpose**: Manages service dependencies
- **Features**:
  - Dependency injection
  - Service lifecycle management
  - Testing support
  - Resource cleanup
  - LLM service selection (OpenAI/vLLM)

### Benefits
- ✅ **Testability**: Easy to mock dependencies
- ✅ **Maintainability**: Centralized configuration
- ✅ **Flexibility**: Easy to swap implementations
- ✅ **Production Ready**: Proper error handling and logging
- ✅ **Caching**: Integrated Redis caching system
- ✅ **Database**: SQLAlchemy ORM integration

## 🚀 Caching System

### Overview
Redis-based multi-layer caching system for optimizing LangGraph node execution:

### Cache Layers
1. **LLM Response Caching**: Cache identical LLM inputs (TTL: 1 hour)
2. **MCP Tool Caching**: Cache tool execution results (TTL: 30 minutes)
3. **Intent Analysis Caching**: Cache user intent analysis (TTL: 2 hours)

### Cache Management
- **Location**: `app/services/cache_manager.py`
- **Features**:
  - Automatic cache key generation
  - TTL management
  - Cache invalidation strategies
  - Performance metrics collection
  - Health monitoring

### Cache API Endpoints
- `GET /cache/health` - Cache system health check
- `GET /cache/stats` - Cache performance statistics
- `DELETE /cache/invalidate/llm` - Invalidate LLM cache
- `DELETE /cache/invalidate/mcp` - Invalidate MCP tool cache
- `DELETE /cache/invalidate/intent` - Invalidate intent analysis cache

### Performance Benefits
- **LLM Call Reduction**: 60-80% expected
- **Response Time Improvement**: 90%+ (cache hit)
- **Cost Savings**: 40-60% expected

## 🔧 Configuration Management

### Environment Variables
The services use `python-dotenv` for loading configuration from `.env` files:

```bash
# Copy the example configuration
cp env.example .env

# Edit .env with your settings
nano .env
```

### Key Configuration
```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# Database Configuration
DATABASE_URL=YOUR-DATABASE-URL

# Model Configuration
DEFAULT_MODEL=gpt-4
MAX_TOKENS=4000
TEMPERATURE=0.7

# Cache Configuration
CACHE_ENABLED=true
CACHE_LLM_TTL=3600
CACHE_MCP_TTL=1800
CACHE_INTENT_TTL=7200

# Redis Configuration
REDIS_URL=redis://basechat_redis:6379/0
REDIS_HOST=basechat_redis
REDIS_PORT=6379

# Service Configuration
MAIN_BACKEND_HOST=0.0.0.0
MAIN_BACKEND_PORT=8000
LLM_AGENT_HOST=0.0.0.0
LLM_AGENT_PORT=8001

# Security
SECRET_KEY=your-secret-key-change-in-production
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- PostgreSQL (provided via Docker)
- Redis (provided via Docker)

### 1. Environment Setup
```bash
# Copy environment configuration
cp env.example .env

# Edit with your OpenAI API key and database settings
nano .env
```

### 2. Using Docker Compose (Recommended)
```bash
# Start all services
docker-compose --profile openai up -d --build

# Or for vLLM (local LLM)
docker-compose --profile vllm up -d --build
```

### 3. Manual Setup
```bash
# Install dependencies
pip install -r main-backend/requirements.txt
pip install -r llm-agent/requirements.txt
pip install -r mcp-server/requirements.txt

# Start services
cd main-backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd llm-agent && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
cd mcp-server && uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

## 📁 Project Structure

```
backend/
├── main-backend/              # Main backend service
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   ├── cache.py      # Cache monitoring API
│   │   │   ├── chat.py       # Chat API
│   │   │   ├── history.py    # Chat history API
│   │   │   └── mcp_tools.py  # MCP tools API
│   │   ├── core/             # Core configuration
│   │   │   ├── config.py     # Settings management
│   │   │   └── graph.py      # LangGraph workflow
│   │   ├── services/         # Business logic
│   │   │   ├── cache_manager.py      # Redis cache management
│   │   │   ├── llm_client.py         # LLM client with caching
│   │   │   ├── mcp_client.py         # MCP client with caching
│   │   │   ├── sqlalchemy_service.py # SQLAlchemy database service
│   │   │   └── sqlalchemy_chat_history_service.py # Chat history service
│   │   ├── models/           # Data models
│   │   │   ├── database_models.py    # SQLAlchemy ORM models
│   │   │   ├── chat_history.py       # Chat history Pydantic models
│   │   │   └── user.py               # User Pydantic models
│   │   └── utils/            # Utilities
│   ├── alembic/              # Database migrations
│   │   ├── versions/         # Migration files
│   │   └── env.py            # Alembic environment
│   ├── tests/                # Unit tests
│   │   └── test_cache_manager.py
│   ├── requirements.txt      # Python dependencies
│   └── docker-compose.test.yml  # Test environment
├── llm-agent/                # LLM agent service
│   ├── app/
│   │   ├── api/              # LLM API endpoints
│   │   ├── services/         # LLM services
│   │   │   ├── base_llm_service.py    # Abstract base class
│   │   │   ├── openai_service.py      # OpenAI implementation
│   │   │   ├── vllm_service.py        # vLLM implementation
│   │   │   └── llm_factory.py         # LLM service factory
│   │   └── models/           # Request/response models
│   └── requirements.txt
├── mcp-server/               # MCP server
│   ├── app/
│   │   ├── api/              # MCP API endpoints
│   │   └── tools/            # MCP tools
│   └── requirements.txt
├── docker-compose.yml        # Service orchestration
└── env.example               # Environment template
```

## 🗄️ Database Management

### Alembic Migrations
```bash
# Create new migration
docker exec backend-main-backend-1 alembic revision --autogenerate -m "Description"

# Apply migrations
docker exec backend-main-backend-1 alembic upgrade head

# Check migration status
docker exec backend-main-backend-1 alembic current

# Rollback migration
docker exec backend-main-backend-1 alembic downgrade -1
```

### Database Operations
```bash
# Connect to database
docker exec basechat_postgres psql -U admin -d basechat

# Check tables
docker exec basechat_postgres psql -U admin -d basechat -c "\dt"

# Check data
docker exec basechat_postgres psql -U admin -d basechat -c "SELECT COUNT(*) FROM users;"
```

## 🧪 Testing

### Running Tests
```bash
# Navigate to main backend
cd main-backend

# Run cache system tests
./run_tests.sh

# Or run manually
python -m pytest tests/ -v
```

### Test Coverage
- Cache manager functionality
- LLM client caching
- MCP client caching
- Cache invalidation strategies
- Performance metrics
- Database operations
- Chat history functionality

## 📊 Monitoring

### Health Checks
- `GET /health` - Service health status
- `GET /cache/health` - Cache system health
- `GET /cache/stats` - Cache performance metrics
- `GET /history/health` - Chat history system health

### Logging
- Structured logging with loguru
- Performance monitoring
- Cache hit/miss tracking
- Error tracking and reporting
- Database operation logging

## 🔄 LLM Service Selection

### OpenAI (Default)
```bash
# Use OpenAI API
docker-compose --profile openai up -d
```

### vLLM (Local LLM)
```bash
# Use vLLM for local inference
docker-compose --profile vllm up -d
```

### Configuration
```bash
# Environment variable
LLM_TYPE=openai  # or vllm
```

## 🚀 Performance Optimization

### Caching Strategies
1. **LLM Response Caching**: Reduces API calls by 60-80%
2. **MCP Tool Caching**: Reduces tool execution time by 50-70%
3. **Intent Analysis Caching**: Reduces analysis time by 70%+

### Database Optimization
1. **Connection Pooling**: Efficient database connections
2. **Async Operations**: Non-blocking database queries
3. **Indexed Queries**: Optimized data retrieval
4. **Migration Management**: Automated schema updates

### Best Practices
- Monitor cache hit rates
- Adjust TTL based on usage patterns
- Use cache invalidation strategically
- Monitor Redis memory usage
- Regular database maintenance
- Monitor migration status

## 🛠️ Development

### Adding New MCP Tools
1. Create tool in `mcp-server/app/tools/`
2. Register tool in MCP server
3. Update tool documentation
4. Add caching if needed

### Extending Cache System
1. Add new cache methods to `CacheManager`
2. Update cache key generation
3. Add monitoring endpoints
4. Update tests

### Adding New LLM Providers
1. Implement `BaseLLMService` interface
2. Add to `LLMFactory`
3. Update configuration
4. Add tests

### Database Schema Changes
1. Update SQLAlchemy models in `database_models.py`
2. Generate Alembic migration
3. Test migration on development database
4. Apply migration to production

## 📈 Production Deployment

### Docker Compose
```bash
# Production deployment
docker-compose --profile openai -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment Variables
- Set `DEBUG=false`
- Configure proper `SECRET_KEY`
- Set production Redis configuration
- Configure monitoring and logging
- Set production database URL

### Monitoring
- Cache performance metrics
- Service health checks
- Error rate monitoring
- Response time tracking
- Database performance monitoring
- Migration status monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License 