from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime

from app.models.embedding_models import (
    BatchEmbeddingRequest, BatchEmbeddingResponse,
    JobStatusResponse
)
from app.services.batch_service import BatchService
from app.utils.logger import get_logger

router = APIRouter(prefix="/batch", tags=["batch"])
logger = get_logger("batch_routes")


# Global service instance
_batch_service: BatchService = None


def set_batch_service(batch_service: BatchService):
    """Set global batch service instance."""
    global _batch_service
    _batch_service = batch_service


def get_batch_service() -> BatchService:
    """Get batch service instance."""
    if _batch_service is None:
        raise HTTPException(status_code=500, detail="Batch service not initialized")
    return _batch_service


@router.post("/embed", response_model=BatchEmbeddingResponse)
async def create_batch_embedding(
    request: BatchEmbeddingRequest,
    batch_svc: BatchService = Depends(get_batch_service)
):
    """Create embeddings for multiple documents in batch."""
    try:
        logger.info(f"Creating batch embedding job for {len(request.documents)} documents")
        
        # Create batch job
        job_id = await batch_svc.create_batch_job(request.documents)
        
        return BatchEmbeddingResponse(
            job_id=job_id,
            total_documents=len(request.documents),
            status="processing"
        )
        
    except Exception as e:
        logger.error(f"Error creating batch job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create batch job: {str(e)}")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_batch_status(
    job_id: str,
    batch_svc: BatchService = Depends(get_batch_service)
):
    """Get status of a batch job."""
    try:
        job_info = await batch_svc.get_job_status(job_id)
        
        return JobStatusResponse(
            job_id=job_info["id"],
            status=job_info["status"],
            total_documents=int(job_info["total_documents"]),
            processed_documents=int(job_info.get("processed", 0)),
            failed_documents=int(job_info.get("failed", 0)),
            progress=float(job_info.get("progress", 0)),
            created_at=datetime.fromisoformat(job_info["created_at"]),
            updated_at=datetime.fromisoformat(job_info["updated_at"]),
            errors=job_info.get("errors")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_batch_jobs(
    limit: int = 50,
    batch_svc: BatchService = Depends(get_batch_service)
):
    """List all batch jobs."""
    try:
        jobs = await batch_svc.list_jobs(limit=limit)
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing batch jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list batch jobs: {str(e)}")


@router.delete("/cancel/{job_id}")
async def cancel_batch_job(
    job_id: str,
    batch_svc: BatchService = Depends(get_batch_service)
):
    """Cancel a batch job."""
    try:
        success = await batch_svc.cancel_job(job_id)
        
        if success:
            return {"message": f"Job {job_id} cancelled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel job")
            
    except Exception as e:
        logger.error(f"Error cancelling batch job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch job: {str(e)}")
