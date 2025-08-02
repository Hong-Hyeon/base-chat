"""
RAG (Retrieval-Augmented Generation) API endpoints
Provides semantic search and document retrieval capabilities
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.rag_models import (
    RAGSearchRequest, RAGSearchResponse,
    RAGEmbeddingRequest, RAGEmbeddingResponse,
    RAGBatchRequest, RAGBatchResponse,
    RAGBatchStatusResponse
)
from app.services.rag_client import RAGClient
from app.utils.logger import get_logger

router = APIRouter(prefix="/rag", tags=["rag"])
logger = get_logger("rag_api")


# Global RAG client instance
rag_client: RAGClient = None


def get_rag_client() -> RAGClient:
    """Get RAG client instance."""
    if rag_client is None:
        raise HTTPException(status_code=500, detail="RAG client not initialized")
    return rag_client


def set_rag_client(client: RAGClient):
    """Set global RAG client instance."""
    global rag_client
    rag_client = client


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    rag_svc: RAGClient = Depends(get_rag_client)
):
    """Search for documents using semantic similarity."""
    try:
        logger.info(f"RAG search request: {request.query}")
        
        # Perform search
        response = await rag_svc.search_documents(
            query=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        
        logger.info(f"RAG search completed: {len(response.results)} results")
        return response
        
    except Exception as e:
        logger.error(f"Error in RAG search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/embed", response_model=RAGEmbeddingResponse)
async def create_embedding(
    request: RAGEmbeddingRequest,
    rag_svc: RAGClient = Depends(get_rag_client)
):
    """Create an embedding for a text and store it in the vector database."""
    try:
        logger.info(f"Creating embedding for text: {request.text[:50]}...")
        
        # Create embedding
        result = await rag_svc.create_embedding(
            text=request.text,
            metadata=request.metadata
        )
        
        if result["success"]:
            logger.info("Embedding created successfully")
            return RAGEmbeddingResponse(
                success=True,
                document_id=result.get("document_id"),
                model=result.get("model"),
                embedding_dimension=result.get("embedding_dimension"),
                text=result.get("text"),
                created_at=datetime.utcnow()
            )
        else:
            logger.error(f"Embedding creation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error"))
        
    except Exception as e:
        logger.error(f"Error creating embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")


@router.post("/batch", response_model=RAGBatchResponse)
async def batch_create_embeddings(
    request: RAGBatchRequest,
    rag_svc: RAGClient = Depends(get_rag_client)
):
    """Create embeddings for multiple documents in batch."""
    try:
        logger.info(f"Creating batch embeddings for {len(request.documents)} documents")
        
        # Create batch embeddings
        result = await rag_svc.batch_create_embeddings(request.documents)
        
        if result["success"]:
            logger.info(f"Batch job created: {result.get('job_id')}")
            return RAGBatchResponse(
                success=True,
                job_id=result.get("job_id"),
                total_documents=result.get("total_documents"),
                status=result.get("status"),
                created_at=datetime.utcnow()
            )
        else:
            logger.error(f"Batch creation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error"))
        
    except Exception as e:
        logger.error(f"Error creating batch embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch creation failed: {str(e)}")


@router.get("/batch/{job_id}/status", response_model=RAGBatchStatusResponse)
async def get_batch_status(
    job_id: str,
    rag_svc: RAGClient = Depends(get_rag_client)
):
    """Get status of a batch embedding job."""
    try:
        logger.info(f"Getting batch job status: {job_id}")
        
        # Get batch status
        result = await rag_svc.get_batch_status(job_id)
        
        if result["success"]:
            return RAGBatchStatusResponse(
                success=True,
                job_id=result.get("job_id"),
                status=result.get("status"),
                total_documents=result.get("total_documents"),
                processed_documents=result.get("processed_documents"),
                failed_documents=result.get("failed_documents"),
                progress=result.get("progress"),
                errors=result.get("errors"),
                updated_at=datetime.utcnow()
            )
        else:
            logger.error(f"Batch status check failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error"))
        
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/health")
async def rag_health_check(rag_svc: RAGClient = Depends(get_rag_client)):
    """Check RAG service health."""
    try:
        health = await rag_svc.health_check()
        return health
        
    except Exception as e:
        logger.error(f"RAG health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
