from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.models.embedding_models import (
    TableCreationRequest, TableCreationResponse,
    TableListResponse, TableDeletionResponse, TableSwitchResponse,
    TableInfo
)
from app.services.vector_store_service import VectorStoreService
from app.utils.logger import get_logger

router = APIRouter(prefix="/embed/tables", tags=["table-management"])
logger = get_logger("table_routes")

# Service instance (will be initialized in app factory)
vector_store_service: VectorStoreService = None

def set_vector_store_service(service: VectorStoreService):
    global vector_store_service
    vector_store_service = service

def get_vector_store_service() -> VectorStoreService:
    if vector_store_service is None:
        raise HTTPException(status_code=500, detail="Vector store service not initialized")
    return vector_store_service

@router.post("/create", response_model=TableCreationResponse)
async def create_embedding_table(
    request: TableCreationRequest,
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Create a new embedding table."""
    try:
        result = await vector_svc.create_embedding_table(
            table_name=request.table_name,
            description=request.description
        )
        
        logger.info(f"Created embedding table: {request.table_name}")
        
        return TableCreationResponse(
            success=result["success"],
            table_name=result["table_name"],
            table_id=result["table_id"],
            table_schema=result["schema"]
        )
        
    except ValueError as e:
        logger.error(f"Validation error creating table {request.table_name}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating table {request.table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")

@router.get("/", response_model=TableListResponse)
async def list_embedding_tables(
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """List all embedding tables."""
    try:
        tables_data = await vector_svc.list_embedding_tables()
        
        tables = []
        for table_data in tables_data:
            tables.append(TableInfo(
                table_name=table_data["table_name"],
                description=table_data["description"],
                document_count=table_data["document_count"],
                created_at=table_data["created_at"],
                last_updated=table_data["last_updated"]
            ))
        
        logger.info(f"Listed {len(tables)} embedding tables")
        
        return TableListResponse(
            tables=tables,
            total_count=len(tables)
        )
        
    except Exception as e:
        logger.error(f"Error listing embedding tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")

@router.delete("/{table_name}", response_model=TableDeletionResponse)
async def delete_embedding_table(
    table_name: str,
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Delete an embedding table."""
    try:
        result = await vector_svc.delete_embedding_table(table_name)
        
        logger.info(f"Deleted embedding table: {table_name}")
        
        return TableDeletionResponse(
            success=result["success"],
            table_name=result["table_name"]
        )
        
    except ValueError as e:
        logger.error(f"Validation error deleting table {table_name}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting table {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete table: {str(e)}")

@router.post("/{table_name}/switch", response_model=TableSwitchResponse)
async def switch_embedding_table(
    table_name: str,
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Switch to a different embedding table."""
    try:
        result = await vector_svc.switch_table(table_name)
        
        logger.info(f"Switched to embedding table: {table_name}")
        
        return TableSwitchResponse(
            success=result["success"],
            previous_table=result["previous_table"],
            current_table=result["current_table"]
        )
        
    except ValueError as e:
        logger.error(f"Validation error switching to table {table_name}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error switching to table {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to switch table: {str(e)}")

@router.get("/{table_name}/info")
async def get_table_info(
    table_name: str,
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Get detailed information about a specific table."""
    try:
        tables_data = await vector_svc.list_embedding_tables()
        
        for table_data in tables_data:
            if table_data["table_name"] == table_name:
                return {
                    "table_name": table_data["table_name"],
                    "description": table_data["description"],
                    "document_count": table_data["document_count"],
                    "created_at": table_data["created_at"],
                    "last_updated": table_data["last_updated"]
                }
        
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table info for {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get table info: {str(e)}")
