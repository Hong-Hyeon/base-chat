"""
RAG (Retrieval-Augmented Generation) Client Service
Provides integration with the embedding server for semantic search and document retrieval
"""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.utils.logger import get_logger

logger = get_logger("rag_client")


class RAGSearchRequest(BaseModel):
    """Request model for RAG search."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")
    similarity_threshold: float = Field(default=0.5, description="Similarity threshold")


class RAGSearchResult(BaseModel):
    """Model for RAG search result."""
    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata")


class RAGSearchResponse(BaseModel):
    """Response model for RAG search."""
    query: str = Field(..., description="Original query")
    results: List[RAGSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_time: float = Field(..., description="Search execution time")


class RAGClient:
    """RAG Client for semantic search and document retrieval."""
    
    def __init__(self, embedding_server_url: str = "http://embedding-server:8003"):
        self.embedding_server_url = embedding_server_url
        self.logger = get_logger("rag_client")
    
    async def search_documents(self, query: str, top_k: int = 5, similarity_threshold: float = 0.5) -> RAGSearchResponse:
        """
        Search for documents using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Search results with documents and metadata
        """
        try:
            self.logger.info(f"Searching documents for query: {query}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.embedding_server_url}/embed/search",
                    json={
                        "query": query,
                        "top_k": top_k,
                        "similarity_threshold": similarity_threshold
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Convert to our response format
                    results = []
                    for result in data.get("results", []):
                        results.append(RAGSearchResult(
                            document_id=result["document_id"],
                            content=result["content"],
                            similarity_score=result["similarity_score"],
                            metadata=result.get("metadata")
                        ))
                    
                    response_data = RAGSearchResponse(
                        query=data["query"],
                        results=results,
                        total_results=data["total_results"],
                        search_time=data["search_time"]
                    )
                    
                    self.logger.info(f"Found {len(results)} documents for query: {query}")
                    return response_data
                    
                else:
                    error_msg = f"Embedding server error: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            error_msg = f"Error searching documents: {str(e)}"
            self.logger.error(error_msg)
            raise
    
    async def create_embedding(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an embedding for a text and store it in the vector database.
        
        Args:
            text: Text to embed
            metadata: Optional metadata for the document
            
        Returns:
            Embedding creation result
        """
        try:
            self.logger.info(f"Creating embedding for text: {text[:50]}...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.embedding_server_url}/embed/",
                    json={
                        "text": text,
                        "metadata": metadata or {}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info("Embedding created successfully")
                    return {
                        "success": True,
                        "document_id": data.get("document_id"),
                        "model": data.get("model"),
                        "embedding_dimension": len(data.get("embedding", [])),
                        "text": data.get("text")
                    }
                else:
                    error_msg = f"Embedding server error: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except Exception as e:
            error_msg = f"Error creating embedding: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def batch_create_embeddings(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create embeddings for multiple documents in batch.
        
        Args:
            documents: List of documents with 'content', 'id', and optional 'metadata'
            
        Returns:
            Batch job result
        """
        try:
            self.logger.info(f"Creating batch embeddings for {len(documents)} documents")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.embedding_server_url}/batch/embed",
                    json={
                        "documents": documents
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(f"Batch job created: {data.get('job_id')}")
                    return {
                        "success": True,
                        "job_id": data.get("job_id"),
                        "total_documents": data.get("total_documents"),
                        "status": data.get("status")
                    }
                else:
                    error_msg = f"Embedding server error: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except Exception as e:
            error_msg = f"Error creating batch embeddings: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_batch_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a batch embedding job.
        
        Args:
            job_id: Batch job ID
            
        Returns:
            Job status information
        """
        try:
            self.logger.info(f"Getting batch job status: {job_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.embedding_server_url}/batch/status/{job_id}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "job_id": data.get("job_id"),
                        "status": data.get("status"),
                        "total_documents": data.get("total_documents"),
                        "processed_documents": data.get("processed_documents"),
                        "failed_documents": data.get("failed_documents"),
                        "progress": data.get("progress"),
                        "errors": data.get("errors")
                    }
                else:
                    error_msg = f"Embedding server error: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except Exception as e:
            error_msg = f"Error getting batch status: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check RAG service health."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.embedding_server_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "healthy",
                        "embedding_server": data.get("status", "unknown"),
                        "embedding_service": data.get("embedding_service", "unknown"),
                        "vector_store": data.get("vector_store", "unknown"),
                        "celery": data.get("celery", "unknown")
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
