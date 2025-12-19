from typing import Any, Optional
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

async def get_task_from_db(task_id: str):
    """Get task from database"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.job_id == task_id))
        task = result.scalar_one_or_none()
        return task

async def mark_task_failed(task_id: str, error_message: str):
    """Mark task as failed in database"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Task).where(Task.job_id == task_id))
            task = result.scalar_one_or_none()
            
            if task:
                task.mark_failed(error_message)
                await db.commit()
                logger.info(f"Marked task {task_id} as failed")
            else:
                logger.warning(f"Task {task_id} not found in database")
    except Exception as e:
        logger.error(f"Failed to mark task {task_id} as failed: {str(e)}")


async def save_task_attribute(job_id: str, attribute_name: Any, value: Any):
    """
    Generic function to update a single attribute of a Task in the database.
    
    Args:
        job_id (str): The unique job ID of the task.
        attribute_name (str): The name of the Task model attribute to update.
        value (Any): The new value to assign.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Task).where(Task.job_id == job_id))
            task = result.scalar_one_or_none()
            
            if task:
                if not hasattr(task, attribute_name):
                    logger.error(f"Task model has no attribute '{attribute_name}'")
                    return
                
                setattr(task, attribute_name, value)
                session.add(task)
                await session.commit()
                logger.info(f"Updated task {job_id}: {attribute_name} = {value}")
            else:
                logger.warning(f"Task {job_id} not found in database")
    except Exception as e:
        logger.error(f"Failed to update task {job_id} attribute '{attribute_name}': {str(e)}")