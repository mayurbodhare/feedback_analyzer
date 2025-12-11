from fastapi import APIRouter, Depends
import logging
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from logger import setup_logging

from db import get_db
from db import Task, TaskStatus, TaskStage

setup_logging()
logger = logging.getLogger(__name__)

router = APIRouter()
# ========== TEST ENDPOINTS FOR DATABASE CRUD OPERATIONS ==========

@router.post("/test/tasks")
async def create_test_task(
    job_id: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    CREATE: Create a new task
    Example: POST /test/tasks?job_id=test123&email=user@example.com
    """
    try:
        task = Task(job_id=job_id, email=email)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Task created: {task.job_id}")
        return {
            "message": "Task created successfully",
            "task": {
                "id": task.id,
                "job_id": task.job_id,
                "email": task.email,
                "status": task.status.value,
                "stage": task.stage.value,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating task: {str(e)}")
        raise


@router.get("/test/tasks")
async def get_all_test_tasks(db: AsyncSession = Depends(get_db)):
    """
    READ: Get all tasks
    Example: GET /test/tasks
    """
    try:
        result = await db.execute(select(Task).order_by(Task.created_at.desc()))
        tasks = result.scalars().all()
        
        logger.info(f"Retrieved {len(tasks)} tasks")
        return {
            "message": "Tasks retrieved successfully",
            "count": len(tasks),
            "tasks": [
                {
                    "id": task.id,
                    "job_id": task.job_id,
                    "email": task.email,
                    "status": task.status.value,
                    "stage": task.stage.value,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                }
                for task in tasks
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving tasks: {str(e)}")
        raise


@router.get("/test/tasks/{job_id}")
async def get_test_task(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    READ: Get a specific task by job_id
    Example: GET /test/tasks/test123
    """
    try:
        result = await db.execute(select(Task).where(Task.job_id == job_id))
        task = result.scalar_one_or_none()
        
        if not task:
            return JSONResponse(
                status_code=404,
                content={"message": "Task not found", "job_id": job_id}
            )
        
        logger.info(f"Retrieved task: {task.job_id}")
        return {
            "message": "Task retrieved successfully",
            "task": {
                "id": task.id,
                "job_id": task.job_id,
                "email": task.email,
                "status": task.status.value,
                "stage": task.stage.value,
                "error_message": task.error_message if hasattr(task, 'error_message') else None,
                "retry_count": task.retry_count if hasattr(task, 'retry_count') else 0,
                "distribution_chart": task.distribution_chart,
                "wordcloud": task.wordcloud,
                "treemap": task.treemap,
                "sunburst": task.sunburst,
                "summary": task.summary,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving task: {str(e)}")
        raise


@router.put("/test/tasks/{job_id}")
async def update_test_task(
    job_id: str,
    status: str = None,
    stage: str = None,
    summary: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    UPDATE: Update a task
    Example: PUT /test/tasks/test123?status=in_progress&stage=translation
    """
    try:
        result = await db.execute(select(Task).where(Task.job_id == job_id))
        task = result.scalar_one_or_none()
        
        if not task:
            return JSONResponse(
                status_code=404,
                content={"message": "Task not found", "job_id": job_id}
            )
        
        # Update fields if provided
        if status:
            task.status = TaskStatus(status)
        if stage:
            task.stage = TaskStage(stage)
        if summary:
            task.summary = summary
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Task updated: {task.job_id}")
        return {
            "message": "Task updated successfully",
            "task": {
                "id": task.id,
                "job_id": task.job_id,
                "status": task.status.value,
                "stage": task.stage.value,
                "summary": task.summary,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"message": f"Invalid enum value: {str(e)}"}
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating task: {str(e)}")
        raise


@router.delete("/test/tasks/{job_id}")
async def delete_test_task(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    DELETE: Delete a task
    Example: DELETE /test/tasks/test123
    """
    try:
        result = await db.execute(select(Task).where(Task.job_id == job_id))
        task = result.scalar_one_or_none()
        
        if not task:
            return JSONResponse(
                status_code=404,
                content={"message": "Task not found", "job_id": job_id}
            )
        
        await db.delete(task)
        await db.commit()
        
        logger.info(f"Task deleted: {job_id}")
        return {
            "message": "Task deleted successfully",
            "job_id": job_id
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting task: {str(e)}")
        raise


@router.get("/test/tasks/email/{email}")
async def get_tasks_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """
    READ: Get all tasks for a specific email
    Example: GET /test/tasks/email/user@example.com
    """
    try:
        result = await db.execute(
            select(Task)
            .where(Task.email == email)
            .order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        
        logger.info(f"Retrieved {len(tasks)} tasks for email: {email}")
        return {
            "message": "Tasks retrieved successfully",
            "email": email,
            "count": len(tasks),
            "tasks": [
                {
                    "id": task.id,
                    "job_id": task.job_id,
                    "status": task.status.value,
                    "stage": task.stage.value,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving tasks by email: {str(e)}")
        raise