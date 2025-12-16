import logging
from db import  AsyncSessionLocal, Task, TaskStatus, TaskStage
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def update_task_stage(job_id: str, stage: TaskStage, status: TaskStatus = None):
    """Update task stage in database"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Task).where(Task.job_id == job_id))
            task = result.scalar_one_or_none()
            
            if task:
                task.stage = stage
                if status:
                    task.status = status
                await db.commit()
                logger.info(f"Updated task {job_id} to stage: {stage.value}")
            else:
                logger.warning(f"Task {job_id} not found in database")
    except Exception as e:
        logger.error(f"Failed to update task stage for {job_id}: {str(e)}")

