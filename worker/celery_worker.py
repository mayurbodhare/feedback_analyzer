# celery_worker.py
import celery
import logging
import os
import asyncio 
import pandas as pd
import time
# from logger import setup_logging
from utils.file_utils import read_file, save_file
from email_sender import send_confirmation_email
from utils.intent import process_intent
from utils.sentiment import process_sentiment
from utils.translation import process_translate
from utils.donut_chart import process_distribution_charts
from utils.db import update_task_stage, get_task_from_db, mark_task_failed
from db import TaskStage, TaskStatus, AsyncSessionLocal, Task
from sqlalchemy import select


# Configure Celery
celery_app = celery.Celery(
    "spreadsheet_processor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",  # Optional: for result storage
)

# Optional: configure logging
logging.basicConfig(level=logging.INFO)

# setup_logging()
# logger = logging.get# logger(__name__)


@celery_app.task(bind=True, name="process_spreadsheet_task")
def process_spreadsheet_task(self, file_path: str, email: str):  # <-- def, not async def

    task_id = self.request.id

    try:
        # logger.info(f"Processing file: {file_path} for email: {email}")

        df = read_file(file_path)

        # logger.info(f"Successfully read file: {file_path} with {len(df)} rows")

        if "intent" in df.columns:
            # logger.info("Column 'Intent' found. Sending confirmation email.")
            asyncio.run(process_distribution_charts(df, file_path, email, task_id))
        elif "sentiment" in df.columns:
            # logger.info("Column 'Sentiment' found. Processing intent.")
            asyncio.run(process_intent(df, file_path, email, task_id))
        elif "translated_text" in df.columns:
            # logger.info("Column 'translated_text' found. Processing sentiment.")
            asyncio.run(process_sentiment(df, file_path, email, task_id))
        else:
            # logger.info("No known processing column found. Starting translation.")
            asyncio.run(process_translate(df, file_path, email, task_id))

        # logger.info(f"Finished processing file: {file_path}")
        return {"status": "success", "email": email}

    except Exception as e:
        # logger.error(f"Error processing {file_path}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)



# Add a periodic task to check for stuck tasks
@celery_app.task(name="check_stuck_tasks")
def check_stuck_tasks():
    """
    Periodic task to check for tasks that have been in IN_PROGRESS status for too long
    """
    async def check():
        from datetime import datetime, timedelta
        
        async with AsyncSessionLocal() as db:
            # Find tasks that have been in progress for more than 1 hour
            stuck_threshold = datetime.now(datetime.timezone.utc) - timedelta(hours=1)
            
            result = await db.execute(
                select(Task).where(
                    Task.status == TaskStatus.IN_PROGRESS,
                    Task.updated_at < stuck_threshold
                )
            )
            stuck_tasks = result.scalars().all()
            
            for task in stuck_tasks:
                # logger.warning(f"Found stuck task: {task.job_id}, stage: {task.stage.value}")
                # Optionally: retry or mark as failed
                task.mark_failed("Task stuck in processing - timeout")
                await db.commit()
    
    try:
        asyncio.run(check())
    except Exception as e:
        # logger.error(f"Error checking stuck tasks: {str(e)}")
        raise


# Configure periodic tasks 
celery_app.conf.beat_schedule = {
    'check-stuck-tasks-every-30-minutes': {
        'task': 'check_stuck_tasks',
        'schedule': 1800.0,  # 30 minutes in seconds
    },
}