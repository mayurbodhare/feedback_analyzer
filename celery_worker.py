# celery_worker.py
import celery
import logging

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

        # Example: just log for now
        with open(file_path, 'r') as f:
            line_count = sum(1 for _ in f)
        logger.info(f"File {file_path} has {line_count} lines.")

        # ⚠️ Consider deleting the file after processing (or archive it)
        # os.remove(file_path)

        return {"status": "success", "email": email, "lines_processed": line_count}

    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        # Optionally retry or alert
        raise self.retry(exc=e, countdown=60, max_retries=3)