# BaseChat Frontend

BaseChat 프로젝트의 Next.js 기반 프론트엔드 애플리케이션입니다. 현대적이고 반응형 사용자 인터페이스를 제공하며, AI 채팅 기능과 채팅 히스토리 관리를 지원합니다.

## 🚀 Features

- [Next.js](https://nextjs.org) App Router
  - Advanced routing for seamless navigation and performance
  - React Server Components (RSCs) and Server Actions for server-side rendering and increased performance
- [AI SDK](https://sdk.vercel.ai/docs)
  - Unified API for generating text, structured objects, and tool calls with LLMs
  - Hooks for building dynamic chat and generative user interfaces
  - Supports OpenAI, xAI, Fireworks, and other model providers
- [shadcn/ui](https://ui.shadcn.com)
  - Styling with [Tailwind CSS](https://tailwindcss.com)
  - Component primitives from [Radix UI](https://radix-ui.com) for accessibility and flexibility
- Chat History Management
  - User session management
  - Conversation history tracking
  - Message persistence
  - Session-based chat context
- Data Persistence
  - Integration with BaseChat backend for chat history
  - User preferences and settings storage
  - Session management
- [Auth.js](https://authjs.dev)
  - Simple and secure authentication
  - User session management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Main Backend   │    │   Database      │
│   (Next.js)     │◄──►│  (FastAPI)      │◄──►│  (PostgreSQL)   │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
│                 │    │                 │    │                 │
│ - Chat UI       │    │ - API Endpoints │    │ - User Data     │
│ - History       │    │ - Chat History  │    │ - Sessions      │
│ - Auth          │    │ - User Mgmt     │    │ - Messages      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- pnpm (recommended) or npm
- BaseChat backend running (see backend README)

### 1. Environment Setup
```bash
# Copy environment configuration
cp env.example .env.local

# Edit with your backend API URL
nano .env.local
```

### 2. Install Dependencies
```bash
# Using pnpm (recommended)
pnpm install

# Or using npm
npm install
```

### 3. Development Server
```bash
# Start development server
pnpm dev

# Or using npm
npm run dev
```

Your app should now be running on [localhost:3000](http://localhost:3000).

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file with the following variables:

```bash
# Backend API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_LLM_AGENT_URL=http://localhost:8001
NEXT_PUBLIC_MCP_SERVER_URL=http://localhost:8002

# Authentication (if using Auth.js)
AUTH_SECRET=your-auth-secret-here
AUTH_URL=http://localhost:3000

# Database (if using direct database connection)
DATABASE_URL=postgresql://admin:higk8156@localhost:5432/basechat

# Optional: Analytics and Monitoring
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

## 📁 Project Structure

```
frontend/
├── app/                      # Next.js App Router
│   ├── (auth)/              # Authentication pages
│   │   ├── login/           # Login page
│   │   ├── register/        # Registration page
│   │   └── layout.tsx       # Auth layout
│   ├── (chat)/              # Chat pages
│   │   ├── page.tsx         # Main chat interface
│   │   ├── history/         # Chat history page
│   │   └── layout.tsx       # Chat layout
│   ├── api/                 # API routes
│   ├── globals.css          # Global styles
│   ├── layout.tsx           # Root layout
│   └── page.tsx             # Home page
├── components/              # React components
│   ├── ui/                  # shadcn/ui components
│   ├── chat/                # Chat-related components
│   ├── history/             # History-related components
│   └── auth/                # Authentication components
├── hooks/                   # Custom React hooks
│   ├── use-chat.ts          # Chat functionality
│   ├── use-history.ts       # History management
│   └── use-auth.ts          # Authentication
├── lib/                     # Utility libraries
├── public/                  # Static assets
└── tests/                   # Test files
```

## 🎨 UI Components

### Chat Interface
- **ChatWindow**: Main chat interface with message display
- **MessageInput**: User input with send functionality
- **MessageBubble**: Individual message display
- **ChatHeader**: Chat session information

### History Management
- **HistoryPanel**: Sidebar with chat history
- **SessionList**: List of user's chat sessions
- **SessionItem**: Individual session display
- **HistorySearch**: Search through chat history

### Authentication
- **LoginForm**: User login interface
- **RegisterForm**: User registration interface
- **UserProfile**: User profile management

## 🔌 API Integration

### Backend API Endpoints

The frontend integrates with the BaseChat backend API:

#### Chat History API
- `POST /history/users` - Create user
- `GET /history/users/{user_id}` - Get user
- `POST /history/sessions` - Create session
- `GET /history/users/{user_id}/sessions` - Get user sessions
- `POST /history/messages` - Save message
- `GET /history/sessions/{session_id}/messages` - Get session messages
- `POST /history/chat/with-history` - Chat with history

#### Chat API
- `POST /chat/` - Send chat message
- `POST /chat/stream` - Stream chat response

#### Cache API
- `GET /cache/health` - Cache status
- `GET /cache/stats` - Cache statistics

### API Client

The frontend uses a custom API client for backend communication:

```typescript
// Example API usage
import { apiClient } from '@/lib/api-client'

// Create user
const user = await apiClient.post('/history/users', {
  username: 'testuser',
  email: 'test@example.com',
  password: 'password123'
})

// Get chat history
const sessions = await apiClient.get(`/history/users/${userId}/sessions`)
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm test:coverage

# Run E2E tests
pnpm test:e2e
```

### Test Structure
- **Unit Tests**: Component and utility function tests
- **Integration Tests**: API integration tests
- **E2E Tests**: Full user workflow tests

## 🚀 Deployment

### Vercel Deployment (Recommended)

1. **Connect Repository**
   ```bash
   # Install Vercel CLI
   npm i -g vercel
   
   # Link to Vercel
   vercel link
   ```

2. **Environment Variables**
   - Set environment variables in Vercel dashboard
   - Configure backend API URLs for production

3. **Deploy**
   ```bash
   vercel --prod
   ```

### Docker Deployment

```bash
# Build Docker image
docker build -t basechat-frontend .

# Run container
docker run -p 3000:3000 basechat-frontend
```

### Environment Configuration

For production deployment, ensure these environment variables are set:

```bash
# Production API URLs
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
NEXT_PUBLIC_LLM_AGENT_URL=https://your-llm-agent-domain.com
NEXT_PUBLIC_MCP_SERVER_URL=https://your-mcp-server-domain.com

# Security
AUTH_SECRET=your-production-auth-secret
NEXTAUTH_URL=https://your-frontend-domain.com
```

## 🔧 Development

### Adding New Features

1. **Create Components**
   ```bash
   # Create new component
   mkdir components/new-feature
   touch components/new-feature/index.tsx
   ```

2. **Add API Integration**
   ```bash
   # Add API endpoint
   touch lib/api/new-feature.ts
   ```

3. **Add Tests**
   ```bash
   # Add test file
   touch tests/new-feature.test.tsx
   ```

### Code Style

The project uses:
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling

### Git Workflow

1. Create feature branch
2. Make changes
3. Add tests
4. Run linting and tests
5. Submit pull request

## 📊 Performance

### Optimization Features
- **Next.js App Router**: Optimized routing and rendering
- **React Server Components**: Reduced client-side JavaScript
- **Image Optimization**: Automatic image optimization
- **Code Splitting**: Automatic code splitting
- **Caching**: API response caching

### Monitoring
- **Performance Metrics**: Core Web Vitals monitoring
- **Error Tracking**: Error boundary and logging
- **Analytics**: User behavior tracking (optional)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

MIT License

## 🆘 Support

For support and questions:
- Check the [BaseChat Backend README](../backend/README.md)
- Create an issue in the repository
- Review the [Next.js documentation](https://nextjs.org/docs)
