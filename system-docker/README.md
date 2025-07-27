# System Docker Services

이 디렉토리는 StubiChat 시스템의 핵심 인프라 서비스들을 관리합니다.

## 서비스 구성

### 1. PostgreSQL with pgvector

**이미지**: `pgvector/pgvector:pg16`
**포트**: 5432
**기능**: 
- 벡터 검색을 위한 pgvector 확장
- 대화 히스토리 및 사용자 데이터 저장
- OpenAI 임베딩 벡터 저장 및 유사도 검색

**주요 테이블**:
- `users`: 사용자 정보
- `chats`: 채팅 세션
- `messages`: 메시지 내용
- `embeddings`: 메시지 임베딩 벡터

### 2. Redis

**이미지**: `redis:7-alpine`
**포트**: 6379
**기능**:
- 세션 관리
- 캐싱
- 실시간 데이터 저장
- 작업 큐

### 3. Nginx

**이미지**: `nginx:alpine`
**포트**: 80, 443
**기능**:
- 리버스 프록시
- 로드 밸런싱
- SSL 종료
- 정적 파일 서빙

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
docker-compose exec postgres psql -U stubichat_user -d stubichat

# 또는 외부에서 연결
psql -h localhost -p 5432 -U stubichat_user -d stubichat
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
-- 임베딩 벡터 저장
INSERT INTO embeddings (message_id, embedding, model_name) 
VALUES (1, '[0.1, 0.2, 0.3, ...]'::vector, 'text-embedding-ada-002');

-- 유사도 검색
SELECT m.content, e.embedding <=> '[0.1, 0.2, 0.3, ...]'::vector as distance
FROM embeddings e
JOIN messages m ON e.message_id = m.id
ORDER BY distance
LIMIT 5;
```

### 4. Python에서 사용 예제

```python
import psycopg2
import numpy as np
from psycopg2.extras import RealDictCursor

# 데이터베이스 연결
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="stubichat",
    user="stubichat_user",
    password="stubichat_secure_password_2024"
)

# 임베딩 벡터 저장
def save_embedding(message_id: int, embedding: list, model_name: str):
    with conn.cursor() as cur:
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        cur.execute(
            "INSERT INTO embeddings (message_id, embedding, model_name) VALUES (%s, %s::vector, %s)",
            (message_id, embedding_str, model_name)
        )
        conn.commit()

# 유사도 검색
def search_similar_messages(query_embedding: list, limit: int = 5):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        cur.execute("""
            SELECT m.content, e.embedding <=> %s::vector as distance
            FROM embeddings e
            JOIN messages m ON e.message_id = m.id
            ORDER BY distance
            LIMIT %s
        """, (embedding_str, limit))
        return cur.fetchall()
```

## Redis 사용법

### 1. Redis CLI 접속

```bash
# Redis 컨테이너에 접속
docker-compose exec redis redis-cli

# 또는 외부에서 연결
redis-cli -h localhost -p 6379
```

### 2. 기본 명령어

```bash
# 키-값 저장
SET user:123:session "session_data_here"
GET user:123:session

# 리스트 조작
LPUSH chat:456:messages "message1"
LPUSH chat:456:messages "message2"
LRANGE chat:456:messages 0 -1

# 해시 조작
HSET user:789:profile name "John" email "john@example.com"
HGETALL user:789:profile

# 만료 시간 설정
EXPIRE user:123:session 3600  # 1시간 후 만료
```

### 3. Python에서 사용 예제

```python
import redis
import json

# Redis 연결
r = redis.Redis(host='localhost', port=6379, db=0)

# 세션 저장
def save_session(user_id: str, session_data: dict):
    r.setex(f"user:{user_id}:session", 3600, json.dumps(session_data))

# 세션 조회
def get_session(user_id: str):
    data = r.get(f"user:{user_id}:session")
    return json.loads(data) if data else None

# 채팅 메시지 캐싱
def cache_message(chat_id: str, message: str):
    r.lpush(f"chat:{chat_id}:messages", message)
    r.ltrim(f"chat:{chat_id}:messages", 0, 99)  # 최근 100개만 유지
```

## Nginx 설정

### 1. 설정 파일 위치

- 메인 설정: `nginx/conf/nginx.conf`
- 사이트 설정: `nginx/conf.d/stubichat.conf`

### 2. 로그 확인

```bash
# 액세스 로그
docker-compose exec nginx tail -f /var/log/nginx/access.log

# 에러 로그
docker-compose exec nginx tail -f /var/log/nginx/error.log
```

### 3. 설정 리로드

```bash
# Nginx 설정 리로드
docker-compose exec nginx nginx -s reload
```

## 모니터링 및 유지보수

### 1. 데이터베이스 백업

```bash
# PostgreSQL 백업
docker-compose exec postgres pg_dump -U stubichat_user stubichat > backup.sql

# 복원
docker-compose exec -T postgres psql -U stubichat_user stubichat < backup.sql
```

### 2. Redis 백업

```bash
# Redis 백업
docker-compose exec redis redis-cli BGSAVE

# 백업 파일 복사
docker cp stubichat_redis:/data/dump.rdb ./redis_backup.rdb
```

### 3. 로그 관리

```bash
# 로그 파일 크기 확인
docker-compose exec nginx du -sh /var/log/nginx/

# 로그 로테이션 (필요시)
docker-compose exec nginx nginx -s reopen
```

### 4. 성능 모니터링

```bash
# PostgreSQL 성능 통계
docker-compose exec postgres psql -U stubichat_user -d stubichat -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public';
"

# Redis 메모리 사용량
docker-compose exec redis redis-cli INFO memory
```

## 문제 해결

### 1. PostgreSQL 연결 오류

```bash
# PostgreSQL 상태 확인
docker-compose exec postgres pg_isready -U stubichat_user

# 로그 확인
docker-compose logs postgres
```

### 2. Redis 연결 오류

```bash
# Redis 상태 확인
docker-compose exec redis redis-cli ping

# 로그 확인
docker-compose logs redis
```

### 3. Nginx 설정 오류

```bash
# 설정 파일 문법 검사
docker-compose exec nginx nginx -t

# 로그 확인
docker-compose logs nginx
```

## 보안 고려사항

1. **환경 변수**: 프로덕션에서는 강력한 비밀번호 사용
2. **네트워크**: 필요한 포트만 외부에 노출
3. **백업**: 정기적인 데이터베이스 백업 수행
4. **모니터링**: 로그 및 성능 지표 정기 확인
5. **업데이트**: 컨테이너 이미지 정기 업데이트 