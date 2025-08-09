import pytest
import asyncio

from app.services.vector_store_service import VectorStoreService


@pytest.mark.asyncio
async def test_active_table_persists_and_used(monkeypatch):
    svc = VectorStoreService()

    class DummyConn:
        def __init__(self):
            self.executed = []
            self.current_table = 'embeddings'
            self.existing_tables = {"embeddings"}

        async def execute(self, query, *args):
            self.executed.append((query, args))
            # Simulate creating a new table when CREATE TABLE ... is called
            if query.strip().startswith("CREATE TABLE"):
                # naive parse last word before '(' as table name
                name = query.split()[2]
                self.existing_tables.add(name)
            return "OK"

        async def fetchval(self, query, *args):
            # When reading active table, return current_table
            if "FROM active_table" in query:
                return self.current_table
            # EXISTS(table) checks
            if "information_schema.tables" in query:
                table_name = args[0]
                return table_name in self.existing_tables
            # COUNT(*) queries
            if "COUNT(*)" in query:
                return 0
            return None

        async def fetch(self, query, *args):
            return []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def transaction(self):
            class DummyTx:
                async def __aenter__(self_inner):
                    return self_inner
                async def __aexit__(self_inner, et, e, tb):
                    return False
            return DummyTx()

    class DummyPool:
        def __init__(self):
            self._conn = DummyConn()
        class AcquireCtx:
            def __init__(self, conn):
                self._conn = conn
            async def __aenter__(self_inner):
                return self_inner._conn
            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        def acquire(self):
            # Return an async context manager like asyncpg pool.acquire()
            return DummyPool.AcquireCtx(self._conn)

    # Use a single persistent pool across service calls
    persistent_pool = DummyPool()

    async def _get_pool_patch():
        return persistent_pool
    svc._get_pool = _get_pool_patch

    # Initialize DB (creates active_table and reads current_table)
    await svc.initialize_database()
    assert svc.current_table == 'embeddings'

    # Create a new table via service API
    await svc.create_embedding_table('my_table', description='test')

    # Switch table should update active_table and current_table
    await svc.switch_table('my_table')
    assert svc.current_table == 'my_table'

    # Store embedding should target current_table
    await svc.store_embedding('doc1', 'content', [0.1, 0.2], {"source": "test"})
    # If no exceptions, we consider success
