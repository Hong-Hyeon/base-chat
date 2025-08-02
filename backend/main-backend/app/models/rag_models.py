"""
Pydantic models for RAG (Retrieval-Augmented Generation) API
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


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


class RAGEmbeddingRequest(BaseModel):
    """Request model for creating embeddings."""
    text: str = Field(..., description="Text to embed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class RAGEmbeddingResponse(BaseModel):
    """Response model for embedding creation."""
    success: bool = Field(..., description="Success status")
    document_id: Optional[str] = Field(default=None, description="Document ID")
    model: Optional[str] = Field(default=None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(default=None, description="Embedding dimension")
    text: Optional[str] = Field(default=None, description="Original text")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RAGBatchRequest(BaseModel):
    """Request model for batch embedding creation."""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to embed")


class RAGBatchResponse(BaseModel):
    """Response model for batch embedding creation."""
    success: bool = Field(..., description="Success status")
    job_id: Optional[str] = Field(default=None, description="Job ID for tracking")
    total_documents: Optional[int] = Field(default=None, description="Total number of documents")
    status: Optional[str] = Field(default=None, description="Job status")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RAGBatchStatusResponse(BaseModel):
    """Response model for batch job status."""
    success: bool = Field(..., description="Success status")
    job_id: Optional[str] = Field(default=None, description="Job ID")
    status: Optional[str] = Field(default=None, description="Job status")
    total_documents: Optional[int] = Field(default=None, description="Total number of documents")
    processed_documents: Optional[int] = Field(default=None, description="Number of processed documents")
    failed_documents: Optional[int] = Field(default=None, description="Number of failed documents")
    progress: Optional[float] = Field(default=None, description="Progress percentage")
    errors: Optional[List[str]] = Field(default=None, description="Error messages")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
