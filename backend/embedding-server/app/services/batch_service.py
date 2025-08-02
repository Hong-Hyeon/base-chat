import redis.asyncio as aioredis
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import json

from app.celery_app import celery_app
from app.core.config import settings
from app.utils.logger import get_logger
from app.tasks.batch_tasks import process_document_batch

logger = get_logger("batch_service")


class BatchService:
    """배치 작업 관리 서비스"""
    
    def __init__(self):
        self.redis_client = aioredis.from_url(settings.redis_url)
    
    async def create_batch_job(self, documents: List[Dict[str, Any]]) -> str:
        """배치 작업 생성"""
        batch_id = str(uuid.uuid4())
        
        # 작업 정보 저장
        job_info = {
            "id": batch_id,
            "status": "pending",
            "total_documents": len(documents),
            "processed": 0,
            "failed": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.hset(
            f"batch_job:{batch_id}",
            mapping=job_info
        )
        
        # Celery 태스크 실행
        task = process_document_batch.delay(documents, batch_id)
        
        # 태스크 ID 저장
        await self.redis_client.hset(
            f"batch_job:{batch_id}",
            "celery_task_id",
            task.id
        )
        
        logger.info(f"Created batch job {batch_id} with {len(documents)} documents")
        return batch_id
    
    async def get_job_status(self, batch_id: str) -> Dict[str, Any]:
        """작업 상태 조회"""
        job_info_bytes = await self.redis_client.hgetall(f"batch_job:{batch_id}")
        
        if not job_info_bytes:
            raise ValueError(f"Job {batch_id} not found")
        
        # Decode bytes to strings
        job_info = {}
        for k, v in job_info_bytes.items():
            key = k.decode('utf-8') if isinstance(k, bytes) else k
            value = v.decode('utf-8') if isinstance(v, bytes) else v
            job_info[key] = value
        
        # Celery 태스크 상태 확인
        celery_task_id = job_info.get("celery_task_id")
        if celery_task_id:
            task_result = celery_app.AsyncResult(celery_task_id)
            job_info["celery_status"] = task_result.status
            
            # Get task result if available
            if task_result.ready():
                try:
                    result = task_result.result
                    if isinstance(result, dict):
                        job_info.update(result)
                except Exception as e:
                    job_info["celery_error"] = str(e)
        
        return job_info
    
    async def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """작업 목록 조회"""
        pattern = "batch_job:*"
        keys = await self.redis_client.keys(pattern)
        
        jobs = []
        for key in keys[:limit]:
            job_id = key.decode('utf-8').split(':')[1]
            try:
                job_info = await self.get_job_status(job_id)
                jobs.append(job_info)
            except Exception as e:
                logger.error(f"Error getting job {job_id}: {str(e)}")
                continue
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jobs
    
    async def cancel_job(self, batch_id: str) -> bool:
        """작업 취소"""
        try:
            job_info = await self.get_job_status(batch_id)
            celery_task_id = job_info.get("celery_task_id")
            
            if celery_task_id:
                celery_app.control.revoke(celery_task_id, terminate=True)
            
            # Update job status
            await self.redis_client.hset(
                f"batch_job:{batch_id}",
                "status",
                "cancelled"
            )
            
            logger.info(f"Cancelled batch job {batch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling job {batch_id}: {str(e)}")
            return False
