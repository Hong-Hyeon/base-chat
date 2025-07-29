# System Docker Services

이 디렉토리는 BaseChat 시스템의 핵심 인프라 서비스들을 관리합니다.

## 서비스 구성

### 1. PostgreSQL with pgvector

**이미지**: `pgvector/pgvector:pg16`
**포트**: 5432
**기능**: 
- 벡터 검색을 위한 pgvector 확장
- 대화 히스토리 및 사용자 데이터 저장
- OpenAI 임베딩 벡터 저장 및 유사도 검색
- LangGraph 워크플로우 상태 저장

**주요 테이블**:
- `users`: 사용자 정보
- `chats`: 채팅 세션
- `messages`: 메시지 내용
- `embeddings`: 메시지 임베딩 벡터 (vector(1536))
- `conversation_states`: LangGraph 대화 상태

### 2. Redis (Cache & Session)

**이미지**: `redis:7-alpine`
**포트**: 6379
**기능**:
- **캐싱 시스템**: LLM 응답, MCP 도구, 의도 분석 캐싱
- 세션 관리
- 실시간 데이터 저장
- 작업 큐
- 성능 메트릭 저장

**캐시 키 구조**:
- `llm:{hash}`: LLM 응답 캐시 (TTL: 1시간)
- `mcp:{tool}:{hash}`: MCP 도구 결과 캐시 (TTL: 30분)
- `intent:{hash}`: 의도 분석 결과 캐시 (TTL: 2시간)

### 3. Nginx

**이미지**: `nginx:alpine`
**포트**: 80, 443
**기능**:
- 리버스 프록시
- 로드 밸런싱
- SSL 종료
- 정적 파일 서빙
- API 라우팅

## 빠른 시작

### 1. 환경 변수 설정

```bash
# 환경 변수 파일 복사
cp env.example .env

# 필요에 따라 설정 수정
nano .env
```

### 2. 서비스 시작

```bash
# 모든 시스템 서비스 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d postgres redis
```

### 3. 서비스 상태 확인

```bash
# 모든 서비스 상태
docker-compose ps

# 특정 서비스 로그
docker-compose logs postgres
docker-compose logs redis
docker-compose logs nginx
```

## PostgreSQL pgvector 사용법

### 1. 데이터베이스 연결

```bash
# PostgreSQL 컨테이너에 접속
docker-compose exec postgres psql -U basechat_user -d basechat

# 또는 외부에서 연결
psql -h localhost -p 5432 -U basechat_user -d basechat
```

### 2. pgvector 확장 확인

```sql
-- pgvector 확장 확인
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 벡터 타입 확인
\dT vector
```

### 3. 임베딩 벡터 저장 예제

```sql
-- 임베딩 테이블 생성
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    embedding vector(1536), -- OpenAI embedding dimension
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
ON embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 임베딩 벡터 삽입
INSERT INTO embeddings (message_id, embedding, model_name)
VALUES (1, '[0.1, 0.2, ...]'::vector, 'text-embedding-ada-002');

-- 유사도 검색
SELECT m.content, e.embedding <=> '[0.1, 0.2, ...]'::vector as distance
FROM embeddings e
JOIN messages m ON e.message_id = m.id
ORDER BY distance
LIMIT 5;
```

## Redis 캐싱 시스템

### 1. Redis 연결

```bash
# Redis 컨테이너에 접속
docker-compose exec redis redis-cli

# 또는 외부에서 연결
redis-cli -h localhost -p 6379
```

### 2. 캐시 모니터링

```bash
# 캐시 키 확인
KEYS *

# 특정 패턴의 키 확인
KEYS llm:*
KEYS mcp:*
KEYS intent:*

# 캐시 통계 확인
INFO memory
INFO keyspace
```

### 3. 캐시 성능 최적화

```bash
# 메모리 사용량 확인
INFO memory

# 캐시 히트율 확인
INFO stats

# 캐시 무효화
DEL llm:*
DEL mcp:*
DEL intent:*
```

### 4. 캐시 설정

```bash
# Redis 설정 확인
CONFIG GET maxmemory
CONFIG GET maxmemory-policy

# 메모리 정책 설정 (LRU)
CONFIG SET maxmemory-policy allkeys-lru
```

## Nginx 설정

### 1. 라우팅 규칙

```nginx
# 프론트엔드 (Next.js)
location / {
    proxy_pass http://frontend:3000;
}

# 메인 백엔드 API
location /api/ {
    proxy_pass http://main-backend:8000/;
}

# LLM 에이전트
location /llm/ {
    proxy_pass http://llm-agent:8001/;
}

# MCP 서버
location /mcp/ {
    proxy_pass http://mcp-server:8002/;
}
```

### 2. SSL 설정 (선택사항)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # 기존 location 블록들...
}
```

## 환경 변수

### PostgreSQL 설정

```bash
POSTGRES_DB=basechat
POSTGRES_USER=basechat_user
POSTGRES_PASSWORD=basechat_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://basechat_user:basechat_password@postgres:5432/basechat
```

### Redis 설정

```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://redis:6379/0
```

### Nginx 설정

```bash
NGINX_PORT=80
NGINX_SSL_PORT=443
```

## 백업 및 복구

### PostgreSQL 백업

```bash
# 데이터베이스 백업
docker-compose exec postgres pg_dump -U basechat_user basechat > backup.sql

# 데이터베이스 복구
docker-compose exec -T postgres psql -U basechat_user basechat < backup.sql
```

### Redis 백업

```bash
# Redis 데이터 백업
docker-compose exec redis redis-cli BGSAVE

# 백업 파일 복사
docker cp basechat_redis:/data/dump.rdb ./redis_backup.rdb
```

## 모니터링

### 1. 서비스 상태 확인

```bash
# PostgreSQL 상태
docker-compose exec postgres pg_isready -U basechat_user

# Redis 상태
docker-compose exec redis redis-cli ping

# Nginx 상태
curl -I http://localhost/health
```

### 2. 로그 모니터링

```bash
# 실시간 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f nginx
```

### 3. 성능 메트릭

```bash
# PostgreSQL 성능
docker-compose exec postgres psql -U basechat_user -c "SELECT * FROM pg_stat_database;"

# Redis 성능
docker-compose exec redis redis-cli INFO
```

## 문제 해결

### PostgreSQL 문제

```bash
# 연결 문제 확인
docker-compose exec postgres pg_isready

# 로그 확인
docker-compose logs postgres

# 데이터베이스 재시작
docker-compose restart postgres
```

### Redis 문제

```bash
# 연결 문제 확인
docker-compose exec redis redis-cli ping

# 메모리 문제 확인
docker-compose exec redis redis-cli INFO memory

# Redis 재시작
docker-compose restart redis
```

### Nginx 문제

```bash
# 설정 파일 검증
docker-compose exec nginx nginx -t

# Nginx 재시작
docker-compose restart nginx
```

## 개발 환경

### 로컬 개발용 설정

```bash
# 개발용 환경 변수
cp env.example .env.dev

# 개발용 서비스 시작
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 테스트 환경

```bash
# 테스트용 데이터베이스
docker-compose -f docker-compose.test.yml up -d postgres redis
```

## 보안 고려사항

### 1. 데이터베이스 보안

- 강력한 비밀번호 사용
- 네트워크 접근 제한
- 정기적인 백업
- SSL 연결 사용

### 2. Redis 보안

- 인증 설정
- 네트워크 접근 제한
- 민감한 데이터 암호화
- 정기적인 키 순환

### 3. Nginx 보안

- SSL/TLS 설정
- 보안 헤더 설정
- 요청 제한 설정
- 로그 모니터링

## 확장성

### 1. 수평 확장

```bash
# Redis 클러스터 설정
docker-compose -f docker-compose.cluster.yml up -d

# PostgreSQL 복제 설정
docker-compose -f docker-compose.replica.yml up -d
```

### 2. 수직 확장

```bash
# 리소스 제한 설정
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## 라이선스

MIT License 