# celery_worker.py
import celery
import logging
import os
import asyncio 
import pandas as pd
import time
from logger import setup_logging
from utils.file_utils import read_file, save_file
from email_sender import send_confirmation_email
from utils.intent import process_intent
from utils.sentiment import process_sentiment
from utils.translation import process_translate

# Configure Celery
celery_app = celery.Celery(
    "spreadsheet_processor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",  # Optional: for result storage
)

# Optional: configure logging
logging.basicConfig(level=logging.INFO)

setup_logging()
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_spreadsheet_task")
def process_spreadsheet_task(self, file_path: str, email: str):  # <-- def, not async def
    try:
        logger.info(f"Processing file: {file_path} for email: {email}")

        df = read_file(file_path)
        logger.info(f"Successfully read file: {file_path} with {len(df)} rows")

        if "Intent" in df.columns:
            logger.info("Column 'Intent' found. Sending confirmation email.")
            asyncio.run(send_confirmation_email(file_path, email))
        elif "Sentiment" in df.columns:
            logger.info("Column 'Sentiment' found. Processing intent.")
            asyncio.run(process_intent(df, file_path, email))
        elif "translated_text" in df.columns:
            logger.info("Column 'translated_text' found. Processing sentiment.")
            asyncio.run(process_sentiment(df, file_path, email))
        else:
            logger.info("No known processing column found. Starting translation.")
            asyncio.run(process_translate(df, file_path, email))

        logger.info(f"Finished processing file: {file_path}")
        return {"status": "success", "email": email}

    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)