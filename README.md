# BaseChat

LangGraph, MCP(Model Context Protocol), LLM 에이전트를 통합한 지능형 채팅 시스템

## 개요

BaseChat은 FastAPI 기반 메인 백엔드, LangGraph 워크플로우, MCP 서버, LLM 에이전트, 그리고 Next.js 프론트엔드로 구성된 완전한 AI 채팅 플랫폼입니다. SQLAlchemy ORM과 Alembic 마이그레이션을 통해 안정적인 데이터베이스 관리, Redis 기반 캐싱 시스템을 통해 확장 가능하고 고성능의 시스템을 제공합니다.

## 주요 기능

- **LangGraph 워크플로우**: 대화 상태 관리 및 조건부 라우팅
- **MCP(Model Context Protocol) 통합**: 확장 가능한 도구 시스템
- **LLM 에이전트**: OpenAI API 및 vLLM 지원 (로컬/클라우드)
- **SQLAlchemy ORM**: 안정적인 데이터베이스 관리 및 쿼리 최적화
- **Alembic 마이그레이션**: 데이터베이스 스키마 버전 관리
- **채팅 히스토리**: 사용자별 대화 세션 및 메시지 관리
- **Redis 캐싱 시스템**: LLM 응답, MCP 도구, 의도 분석 캐싱
- **Next.js 프론트엔드**: 현대적이고 반응형 사용자 인터페이스
- **Docker Compose**: 전체 스택을 한 번에 실행
- **실시간 스트리밍**: 고성능 텍스트 스트리밍 지원
- **PostgreSQL**: 관계형 데이터베이스 및 벡터 검색 지원

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Main Backend   │    │   LLM Agent     │
│   (Next.js)     │◄──►│  (FastAPI +     │◄──►│  (OpenAI/vLLM)  │
│   Port: 3000    │    │   LangGraph +   │    │   Port: 8001    │
│                 │    │   SQLAlchemy +  │    │                 │
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
                       │   (SQLAlchemy + │    │   (Cache)       │
                       │   Alembic)      │    │   Port: 6379    │
                       │   Port: 5432    │    │                 │
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

# Database Configuration
DATABASE_URL=YOUR-DATABASE-URL

# Model Configuration
DEFAULT_MODEL=gpt-3.5-turbo
MAX_TOKENS=4000
TEMPERATURE=0.7

# Cache Configuration
CACHE_ENABLED=true
CACHE_LLM_TTL=3600
CACHE_MCP_TTL=1800
CACHE_INTENT_TTL=7200
REDIS_URL=redis://basechat_redis:6379/0
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
│   │   │   │   ├── history.py # 채팅 히스토리 API
│   │   │   │   └── mcp_tools.py # MCP 도구 API
│   │   │   ├── core/          # 핵심 설정 및 그래프
│   │   │   ├── services/      # 서비스 레이어
│   │   │   │   ├── cache_manager.py # Redis 캐시 관리
│   │   │   │   ├── llm_client.py    # LLM 클라이언트
│   │   │   │   ├── mcp_client.py    # MCP 클라이언트
│   │   │   │   ├── sqlalchemy_service.py # SQLAlchemy 데이터베이스 서비스
│   │   │   │   └── sqlalchemy_chat_history_service.py # 채팅 히스토리 서비스
│   │   │   ├── models/        # 데이터 모델
│   │   │   │   ├── database_models.py # SQLAlchemy ORM 모델
│   │   │   │   ├── chat_history.py # 채팅 히스토리 Pydantic 모델
│   │   │   │   └── user.py    # 사용자 Pydantic 모델
│   │   │   └── utils/         # 유틸리티
│   │   ├── alembic/           # Alembic 마이그레이션
│   │   │   ├── versions/      # 마이그레이션 파일들
│   │   │   └── env.py         # Alembic 환경 설정
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

## 데이터베이스 시스템

### SQLAlchemy ORM
- **모델**: `app/models/database_models.py`
- **서비스**: `app/services/sqlalchemy_service.py`
- **기능**: 
  - 사용자 관리 (users, user_preferences)
  - 채팅 세션 관리 (chat_sessions)
  - 메시지 저장 (messages)
  - 관계형 데이터 모델링
  - 비동기 데이터베이스 작업

### Alembic 마이그레이션
- **설정**: `alembic.ini`, `alembic/env.py`
- **마이그레이션**: `alembic/versions/`
- **기능**:
  - 데이터베이스 스키마 버전 관리
  - 자동 마이그레이션 적용 (애플리케이션 시작 시)
  - 롤백 지원
  - Docker 환경에서 마이그레이션 히스토리 보존

### 채팅 히스토리 기능
- **API 엔드포인트**: `/history/*`
- **기능**:
  - 사용자 생성 및 관리
  - 채팅 세션 생성 및 관리
  - 메시지 저장 및 조회
  - 사용자별 대화 히스토리
  - 세션별 메시지 검색
  - 사용자 통계 및 분석

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

### 데이터베이스 마이그레이션
```bash
# 마이그레이션 생성
docker exec backend-main-backend-1 alembic revision --autogenerate -m "Description"

# 마이그레이션 적용
docker exec backend-main-backend-1 alembic upgrade head

# 마이그레이션 상태 확인
docker exec backend-main-backend-1 alembic current
```

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

## API 문서

### 채팅 히스토리 API
- `POST /history/users` - 사용자 생성
- `GET /history/users/{user_id}` - 사용자 조회
- `POST /history/sessions` - 채팅 세션 생성
- `GET /history/users/{user_id}/sessions` - 사용자 세션 목록
- `POST /history/messages` - 메시지 저장
- `GET /history/sessions/{session_id}/messages` - 세션 메시지 목록
- `POST /history/chat/with-history` - 히스토리 기반 채팅
- `GET /history/users/{user_id}/stats` - 사용자 통계

### 캐시 API
- `GET /cache/health` - 캐시 상태 확인
- `GET /cache/stats` - 캐시 통계
- `DELETE /cache/invalidate/*` - 캐시 무효화

## 문제 해결

### 일반적인 문제
1. **포트 충돌**: 다른 서비스가 사용 중인 포트 확인
2. **메모리 부족**: Docker 메모리 할당량 증가
3. **API 키 오류**: OpenAI API 키 설정 확인
4. **데이터베이스 연결 오류**: PostgreSQL 서비스 상태 확인

### 로그 확인
```bash
# 시스템 서비스 로그
cd system-docker
docker-compose logs

# 애플리케이션 로그
cd backend
docker-compose logs
```

### 데이터베이스 문제 해결
```bash
# 데이터베이스 연결 확인
docker exec basechat_postgres psql -U admin -d basechat -c "SELECT 1;"

# 마이그레이션 상태 확인
docker exec backend-main-backend-1 alembic current

# 테이블 상태 확인
docker exec basechat_postgres psql -U admin -d basechat -c "\dt"
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