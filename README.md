# BaseChat

LangGraph, MCP(Model Context Protocol), LLM 에이전트를 통합한 지능형 채팅 시스템

## 개요

BaseChat은 FastAPI 기반 메인 백엔드, LangGraph 워크플로우, MCP 서버, LLM 에이전트, 그리고 Next.js 프론트엔드로 구성된 완전한 AI 채팅 플랫폼입니다. 모듈형 아키텍처와 Redis 기반 캐싱 시스템을 통해 확장 가능하고 고성능의 시스템을 제공합니다.

## 주요 기능

- **LangGraph 워크플로우**: 대화 상태 관리 및 조건부 라우팅
- **MCP(Model Context Protocol) 통합**: 확장 가능한 도구 시스템
- **LLM 에이전트**: OpenAI API 및 vLLM 지원 (로컬/클라우드)
- **Redis 캐싱 시스템**: LLM 응답, MCP 도구, 의도 분석 캐싱
- **Next.js 프론트엔드**: 현대적이고 반응형 사용자 인터페이스
- **Docker Compose**: 전체 스택을 한 번에 실행
- **실시간 스트리밍**: 고성능 텍스트 스트리밍 지원
- **pgvector 데이터베이스**: 벡터 검색 및 임베딩 저장

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Main Backend   │    │   LLM Agent     │
│   (Next.js)     │◄──►│  (FastAPI +     │◄──►│  (OpenAI/vLLM)  │
│   Port: 3000    │    │   LangGraph +   │    │   Port: 8001    │
│                 │    │   Redis Cache)  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   MCP Server    │
                       │   (Tools)       │
                       │   Port: 8002    │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │     Redis       │
                       │   (pgvector)    │    │   (Cache)       │
                       │   Port: 5432    │    │   Port: 6379    │
                       └─────────────────┘    └─────────────────┘
```

## 빠른 시작

### 1. 사전 요구사항

- Docker 및 Docker Compose 설치
- OpenAI API 키 (LLM 에이전트용)

### 2. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd base-chat

# 환경 변수 파일 생성
cp backend/env.example backend/.env
```

### 3. 환경 변수 설정

`backend/.env` 파일을 편집하여 필요한 설정을 추가합니다:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# Model Configuration
DEFAULT_MODEL=gpt-3.5-turbo
MAX_TOKENS=4000
TEMPERATURE=0.7

# Cache Configuration
CACHE_ENABLED=true
CACHE_LLM_TTL=3600
CACHE_MCP_TTL=1800
CACHE_INTENT_TTL=7200
```

### 4. 시스템 실행

#### 전체 시스템 실행 (권장)
```bash
# OpenAI API 사용 (기본값)
./start-system.sh

# 또는 vLLM 사용 (로컬 LLM)
./start-system.sh vllm
```

#### 개별 서비스 실행
```bash
# 시스템 서비스만 실행 (PostgreSQL, Redis, Nginx)
cd system-docker
docker-compose up -d

# 애플리케이션 서비스 실행
cd backend
docker-compose --profile openai up -d --build
```

### 5. 서비스 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **LLM 에이전트**: http://localhost:8001
- **MCP 서버**: http://localhost:8002
- **캐시 모니터링**: http://localhost:8000/cache/health

## 프로젝트 구조

```
base-chat/
├── backend/                    # 백엔드 애플리케이션
│   ├── main-backend/          # 메인 백엔드 (FastAPI + LangGraph)
│   │   ├── app/
│   │   │   ├── api/           # API 엔드포인트
│   │   │   │   ├── cache.py   # 캐시 모니터링 API
│   │   │   │   ├── chat.py    # 채팅 API
│   │   │   │   └── mcp_tools.py # MCP 도구 API
│   │   │   ├── core/          # 핵심 설정 및 그래프
│   │   │   ├── services/      # 서비스 레이어
│   │   │   │   ├── cache_manager.py # Redis 캐시 관리
│   │   │   │   ├── llm_client.py    # LLM 클라이언트
│   │   │   │   └── mcp_client.py    # MCP 클라이언트
│   │   │   └── models/        # 데이터 모델
│   │   ├── tests/             # 단위 테스트
│   │   └── requirements.txt   # Python 의존성
│   ├── llm-agent/             # LLM 에이전트 서비스
│   ├── mcp-server/            # MCP 서버
│   └── docker-compose.yml     # 백엔드 서비스 구성
├── system-docker/             # 시스템 인프라 서비스
│   ├── docker-compose.yml     # PostgreSQL, Redis, Nginx
│   ├── init-scripts/          # 데이터베이스 초기화 스크립트
│   └── nginx/                 # Nginx 설정
├── frontend/                  # Next.js 프론트엔드
├── start-system.sh           # 전체 시스템 시작 스크립트
├── stop-system.sh            # 시스템 중지 스크립트
└── restart-system.sh         # 시스템 재시작 스크립트
```

## 캐싱 시스템

### 개요
Redis 기반 다층 캐싱 시스템으로 LangGraph 노드 실행 성능을 최적화합니다.

### 캐시 레이어
1. **LLM 응답 캐싱**: 동일한 입력에 대한 LLM 응답 캐싱 (TTL: 1시간)
2. **MCP 도구 캐싱**: 도구 호출 결과 캐싱 (TTL: 30분)
3. **의도 분석 캐싱**: 사용자 의도 분석 결과 캐싱 (TTL: 2시간)

### 캐시 모니터링 API
- `GET /cache/health` - 캐시 시스템 상태 확인
- `GET /cache/stats` - 캐시 성능 통계 조회
- `DELETE /cache/invalidate/llm` - LLM 캐시 무효화
- `DELETE /cache/invalidate/mcp` - MCP 도구 캐시 무효화
- `DELETE /cache/invalidate/intent` - 의도 분석 캐시 무효화

### 성능 개선 효과
- **LLM 호출 감소**: 60-80% 예상
- **응답 속도 개선**: 90% 이상 (캐시 히트 시)
- **비용 절감**: 40-60% 예상

## 개발 가이드

### 테스트 실행
```bash
cd backend/main-backend
./run_tests.sh
```

### 로그 확인
```bash
# 전체 시스템 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f main-backend
```

### 환경 변수
주요 환경 변수는 각 디렉토리의 `env.example` 파일을 참조하세요.

## 문제 해결

### 일반적인 문제
1. **포트 충돌**: 다른 서비스가 사용 중인 포트 확인
2. **메모리 부족**: Docker 메모리 할당량 증가
3. **API 키 오류**: OpenAI API 키 설정 확인

### 로그 확인
```bash
# 시스템 서비스 로그
cd system-docker
docker-compose logs

# 애플리케이션 로그
cd backend
docker-compose logs
```

## 기여 가이드

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 라이선스

MIT License

## 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요. 