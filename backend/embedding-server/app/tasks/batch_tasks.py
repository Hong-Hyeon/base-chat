from celery import current_task
from typing import List, Dict, Any
import uuid
import time
import asyncio
from datetime import datetime

from app.celery_app import celery_app
from app.services.gpt_embedding_service import GPTEmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.utils.logger import get_logger

logger = get_logger("batch_tasks")


@celery_app.task(bind=True)
def process_document_batch(self, documents: List[Dict[str, Any]], batch_id: str):
    """문서 배치 임베딩 처리"""
    try:
        logger.info(f"Starting batch processing for batch_id: {batch_id}")
        
        # Run async operations in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(_process_documents_async(self, documents, batch_id))
        finally:
            loop.close()
        
    except Exception as exc:
        logger.error(f"Batch processing failed: {str(exc)}")
        self.update_state(
            state="FAILURE",
            meta={
                "batch_id": batch_id,
                "error": str(exc),
                "failed_at": datetime.utcnow().isoformat()
            }
        )
        raise


async def _process_documents_async(self, documents: List[Dict[str, Any]], batch_id: str):
    """Async implementation of document processing"""
    # Initialize services
    embedding_service = GPTEmbeddingService()
    vector_store_service = VectorStoreService()
    
    # Initialize database connection
    await vector_store_service.initialize_database()
    
    # 진행률 업데이트
    self.update_state(
        state="PROGRESS",
        meta={
            "batch_id": batch_id,
            "current": 0,
            "total": len(documents),
            "status": "Processing...",
            "started_at": datetime.utcnow().isoformat()
        }
    )
    
    processed_count = 0
    failed_count = 0
    errors = []
    
    for i, doc in enumerate(documents):
        try:
            # Extract document data
            content = doc.get("content", "")
            document_id = doc.get("id", str(uuid.uuid4()))
            metadata = doc.get("metadata", {})
            
            if not content:
                logger.warning(f"Empty content for document {document_id}")
                failed_count += 1
                continue
            
            # Create embedding
            embedding = await embedding_service.create_embedding(content)
            
            # Store in vector database
            await vector_store_service.store_embedding(
                document_id=document_id,
                content=content,
                embedding=embedding,
                metadata=metadata
            )
            
            processed_count += 1
            logger.info(f"Processed document {i+1}/{len(documents)}: {document_id}")
            
            # Update progress
            progress = (i + 1) / len(documents) * 100
            self.update_state(
                state="PROGRESS",
                meta={
                    "batch_id": batch_id,
                    "current": i + 1,
                    "total": len(documents),
                    "processed": processed_count,
                    "failed": failed_count,
                    "progress": progress,
                    "status": f"Processed {i + 1}/{len(documents)} documents"
                }
            )
            
        except Exception as e:
            error_msg = f"Error processing document {i+1}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            failed_count += 1
            continue
    
    # Final status update
    completion_time = datetime.utcnow().isoformat()
    result = {
        "batch_id": batch_id,
        "status": "completed",
        "total_documents": len(documents),
        "processed": processed_count,
        "failed": failed_count,
        "errors": errors,
        "completion_time": completion_time
    }
    
    logger.info(f"Batch processing completed: {result}")
    return result


@celery_app.task
def cleanup_old_embeddings(days_old: int = 30):
    """오래된 임베딩 정리"""
    try:
        logger.info(f"Starting cleanup of embeddings older than {days_old} days")
        
        # Run async operations in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(_cleanup_async(days_old))
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise


async def _cleanup_async(days_old: int):
    """Async implementation of cleanup"""
    vector_store_service = VectorStoreService()
    await vector_store_service.initialize_database()
    
    # This would implement cleanup logic
    # For now, just log the task
    logger.info("Cleanup task completed")
    
    return {"status": "completed", "cleaned_count": 0}
