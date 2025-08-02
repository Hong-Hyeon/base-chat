import asyncpg
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.utils.logger import get_logger
import json
import uuid
import re


class VectorStoreService:
    """Service for storing and retrieving vectors using pgvector."""

    def __init__(self):
        self.logger = get_logger("vector_store_service")
        self.db_url = settings.embedding_database_url
        self.pool = None

    async def _get_pool(self):
        """Get database connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20
            )
        return self.pool

    async def initialize_database(self):
        """Initialize database tables and extensions with optimized indexes."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Enable pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Create embeddings table with optimized structure
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        document_id VARCHAR(255) UNIQUE NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # Create optimized indexes for better performance
                # 1. HNSW index for fast approximate nearest neighbor search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_hnsw_idx
                    ON embeddings
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)

                # 2. IVFFlat index as fallback for exact search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_ivfflat_idx
                    ON embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)

                # 3. B-tree index on document_id for fast lookups
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_document_id_idx
                    ON embeddings (document_id)
                """)

                # 4. GIN index on metadata for fast JSONB queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_metadata_gin_idx
                    ON embeddings USING GIN (metadata)
                """)

                # 5. B-tree index on created_at for time-based queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_created_at_idx
                    ON embeddings (created_at)
                """)

                # Create table metadata table for managing multiple embedding tables
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS table_metadata (
                        id SERIAL PRIMARY KEY,
                        table_id VARCHAR(255) UNIQUE NOT NULL,
                        table_name VARCHAR(255) UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # Insert default embeddings table metadata if not exists
                await conn.execute("""
                    INSERT INTO table_metadata (table_id, table_name, description, created_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (table_name) DO NOTHING
                """, str(uuid.uuid4()), "embeddings", "Default embeddings table")

                self.logger.info("Database initialized successfully with optimized indexes and table metadata")

        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise

    async def store_embedding(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store an embedding in the database."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Convert metadata to JSON string if not None
                metadata_json = json.dumps(metadata) if metadata is not None else None
                
                # Convert embedding list to string for pgvector
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                await conn.execute("""
                    INSERT INTO embeddings (document_id, content, embedding, metadata)
                    VALUES ($1, $2, $3::vector, $4::jsonb)
                    ON CONFLICT (document_id)
                    DO UPDATE SET
                        content = $2,
                        embedding = $3::vector,
                        metadata = $4::jsonb,
                        updated_at = NOW()
                """, document_id, content, embedding_str, metadata_json)

                self.logger.info(f"Embedding stored for document: {document_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error storing embedding: {str(e)}")
            raise

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings using optimized cosine similarity."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Convert query embedding to string for pgvector
                query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                # Build filter conditions
                filter_conditions = []
                filter_params = [query_embedding_str, similarity_threshold, top_k]
                param_count = 3

                if filters:
                    for key, value in filters.items():
                        param_count += 1
                        filter_conditions.append(f"metadata->>'{key}' = ${param_count}")
                        filter_params.append(value)

                filter_sql = " AND " + " AND ".join(filter_conditions) if filter_conditions else ""

                # Use HNSW index for fast approximate search
                query = f"""
                    SELECT
                        document_id,
                        content,
                        metadata,
                        1 - (embedding <=> $1::vector) as similarity_score
                    FROM embeddings
                    WHERE 1 - (embedding <=> $1::vector) > $2{filter_sql}
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                """

                rows = await conn.fetch(query, *filter_params)

                results = []
                for row in rows:
                    # Handle metadata - it might be a string from JSONB
                    metadata = row["metadata"]
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except (json.JSONDecodeError, TypeError):
                            metadata = None
                    
                    results.append({
                        "document_id": row["document_id"],
                        "content": row["content"],
                        "metadata": metadata,
                        "similarity_score": float(row["similarity_score"])
                    })

                self.logger.info(f"Found {len(results)} similar documents")
                return results

        except Exception as e:
            self.logger.error(f"Error searching similar embeddings: {str(e)}")
            raise

    async def batch_store_embeddings(
        self,
        embeddings_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store multiple embeddings in batch for better performance."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Use transaction for batch operations
                async with conn.transaction():
                    for data in embeddings_data:
                        document_id = data["document_id"]
                        content = data["content"]
                        embedding = data["embedding"]
                        metadata = data.get("metadata")
                        
                        metadata_json = json.dumps(metadata) if metadata is not None else None
                        embedding_str = f"[{','.join(map(str, embedding))}]"
                        
                        await conn.execute("""
                            INSERT INTO embeddings (document_id, content, embedding, metadata)
                            VALUES ($1, $2, $3::vector, $4::jsonb)
                            ON CONFLICT (document_id)
                            DO UPDATE SET
                                content = $2,
                                embedding = $3::vector,
                                metadata = $4::jsonb,
                                updated_at = NOW()
                        """, document_id, content, embedding_str, metadata_json)

                self.logger.info(f"Batch stored {len(embeddings_data)} embeddings")
                return {"success": True, "count": len(embeddings_data)}

        except Exception as e:
            self.logger.error(f"Error in batch store: {str(e)}")
            raise

    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Get total count
                total_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
                
                # Get average embedding dimension (using vector_dims function for pgvector)
                avg_dimension = await conn.fetchval("""
                    SELECT AVG(vector_dims(embedding)) 
                    FROM embeddings 
                    WHERE embedding IS NOT NULL
                """)
                
                # Get metadata statistics
                metadata_stats = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM embeddings 
                    WHERE metadata IS NOT NULL AND metadata != '{}'::jsonb
                """)
                
                # Get recent activity
                recent_count = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM embeddings 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)

                return {
                    "total_documents": total_count,
                    "avg_embedding_dimension": avg_dimension,
                    "documents_with_metadata": metadata_stats,
                    "recent_documents_24h": recent_count
                }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {str(e)}")
            return {"error": str(e)}

    async def cleanup_old_embeddings(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old embeddings to maintain performance."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM embeddings 
                    WHERE created_at < NOW() - INTERVAL '$1 days'
                """, days_old)
                
                deleted_count = int(result.split()[-1])
                self.logger.info(f"Cleaned up {deleted_count} old embeddings")
                
                return {"success": True, "deleted_count": deleted_count}

        except Exception as e:
            self.logger.error(f"Error cleaning up old embeddings: {str(e)}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check database health with detailed information."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Test connection
                await conn.fetchval("SELECT 1")

                # Get basic statistics
                stats = await self.get_statistics()
                
                # Check index usage
                index_info = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE tablename = 'embeddings'
                """)

                return {
                    "status": "healthy",
                    "connection": "ok",
                    "statistics": stats,
                    "index_usage": [dict(row) for row in index_info]
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }

    def _validate_table_name(self, table_name: str) -> bool:
        """Validate table name for SQL injection prevention."""
        # Check for valid table name pattern
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            return False
        
        # Check for reserved words
        reserved_words = {
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'table', 'index', 'view', 'schema', 'database', 'user', 'admin',
            'root', 'system', 'information_schema', 'pg_'
        }
        
        if table_name.lower() in reserved_words:
            return False
            
        return True

    async def create_embedding_table(self, table_name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new embedding table with the specified name."""
        try:
            # Validate table name
            if not self._validate_table_name(table_name):
                raise ValueError(f"Invalid table name: {table_name}")
            
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Check if table already exists
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = $1
                    )
                """, table_name)
                
                if exists:
                    raise ValueError(f"Table '{table_name}' already exists")
                
                # Create the embedding table
                await conn.execute(f"""
                    CREATE TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        document_id VARCHAR(255) UNIQUE NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create indexes for the new table
                await conn.execute(f"""
                    CREATE INDEX {table_name}_embedding_hnsw_idx
                    ON {table_name}
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)
                
                await conn.execute(f"""
                    CREATE INDEX {table_name}_document_id_idx
                    ON {table_name} (document_id)
                """)
                
                await conn.execute(f"""
                    CREATE INDEX {table_name}_metadata_gin_idx
                    ON {table_name} USING GIN (metadata)
                """)
                
                await conn.execute(f"""
                    CREATE INDEX {table_name}_created_at_idx
                    ON {table_name} (created_at)
                """)
                
                # Store table metadata
                table_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO table_metadata (table_id, table_name, description, created_at)
                    VALUES ($1, $2, $3, NOW())
                """, table_id, table_name, description)
                
                self.logger.info(f"Created embedding table: {table_name}")
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "table_id": table_id,
                    "schema": {
                        "columns": [
                            {"name": "id", "type": "SERIAL PRIMARY KEY"},
                            {"name": "document_id", "type": "VARCHAR(255) UNIQUE NOT NULL"},
                            {"name": "content", "type": "TEXT NOT NULL"},
                            {"name": "embedding", "type": "vector(1536)"},
                            {"name": "metadata", "type": "JSONB"},
                            {"name": "created_at", "type": "TIMESTAMP WITH TIME ZONE"},
                            {"name": "updated_at", "type": "TIMESTAMP WITH TIME ZONE"}
                        ],
                        "indexes": [
                            f"{table_name}_embedding_hnsw_idx (HNSW)",
                            f"{table_name}_document_id_idx (B-tree)",
                            f"{table_name}_metadata_gin_idx (GIN)",
                            f"{table_name}_created_at_idx (B-tree)"
                        ]
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error creating embedding table {table_name}: {str(e)}")
            raise

    async def list_embedding_tables(self) -> List[Dict[str, Any]]:
        """List all embedding tables."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Get table metadata
                rows = await conn.fetch("""
                    SELECT table_id, table_name, description, created_at
                    FROM table_metadata
                    ORDER BY created_at DESC
                """)
                
                tables = []
                for row in rows:
                    table_name = row["table_name"]
                    
                    # Get document count for each table
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    
                    # Get last update time
                    last_updated = await conn.fetchval(f"""
                        SELECT MAX(updated_at) FROM {table_name}
                    """)
                    
                    tables.append({
                        "table_name": table_name,
                        "description": row["description"],
                        "document_count": count or 0,
                        "created_at": row["created_at"],
                        "last_updated": last_updated or row["created_at"]
                    })
                
                return tables
                
        except Exception as e:
            self.logger.error(f"Error listing embedding tables: {str(e)}")
            raise

    async def delete_embedding_table(self, table_name: str) -> Dict[str, Any]:
        """Delete an embedding table."""
        try:
            # Validate table name
            if not self._validate_table_name(table_name):
                raise ValueError(f"Invalid table name: {table_name}")
            
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Check if table exists
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = $1
                    )
                """, table_name)
                
                if not exists:
                    raise ValueError(f"Table '{table_name}' does not exist")
                
                # Delete the table
                await conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Remove table metadata
                await conn.execute("""
                    DELETE FROM table_metadata WHERE table_name = $1
                """, table_name)
                
                self.logger.info(f"Deleted embedding table: {table_name}")
                
                return {
                    "success": True,
                    "table_name": table_name
                }
                
        except Exception as e:
            self.logger.error(f"Error deleting embedding table {table_name}: {str(e)}")
            raise

    async def switch_table(self, table_name: str) -> Dict[str, Any]:
        """Switch to a different embedding table."""
        try:
            # Validate table name
            if not self._validate_table_name(table_name):
                raise ValueError(f"Invalid table name: {table_name}")
            
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Check if table exists
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = $1
                    )
                """, table_name)
                
                if not exists:
                    raise ValueError(f"Table '{table_name}' does not exist")
                
                # Store current active table
                current_table = getattr(self, 'current_table', 'embeddings')
                
                # Switch to new table
                self.current_table = table_name
                
                self.logger.info(f"Switched to embedding table: {table_name}")
                
                return {
                    "success": True,
                    "previous_table": current_table,
                    "current_table": table_name
                }
                
        except Exception as e:
            self.logger.error(f"Error switching to table {table_name}: {str(e)}")
            raise
