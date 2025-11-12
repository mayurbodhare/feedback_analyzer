# celery_worker.py
import celery
import logging
import os
import pandas as pd
import time

# Configure Celery
celery_app = celery.Celery(
    "spreadsheet_processor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"  # Optional: for result storage
)

# Optional: configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="process_spreadsheet_task")
def process_spreadsheet_task(self, file_path: str, email: str):
    """
    Background task to process the uploaded spreadsheet.
    """
    try:
        logger.info(f"Processing file: {file_path} for email: {email}")
        
        # 🔧 YOUR ACTUAL PROCESSING LOGIC GOES HERE
        # e.g., read CSV, validate rows, send email, store in DB, etc.

        # TODO: Remove this delay
        # this make it slow
        time.sleep(10)

        # Example: just log for now
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.csv':
            df = pd.read_csv(file_path)
        elif file_extension == '.tsv':
            df = pd.read_csv(file_path, sep='\t')
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_extension == '.ods':
            df = pd.read_excel(file_path, engine='odf')
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        line_count = len(df)
        logger.info(f"File {file_path} has {line_count} lines.")

        # ⚠️ Consider deleting the file after processing (or archive it)
        # os.remove(file_path)

        return {"status": "success", "email": email, "lines_processed": line_count}

    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        # Optionally retry or alert
        raise self.retry(exc=e, countdown=60, max_retries=3)