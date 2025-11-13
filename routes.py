from pathlib import Path
from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from pydantic import EmailStr
import os
import logging
from celery_worker import process_spreadsheet_task
from email_sender import send_task_email

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed MIME types and extensions
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/tab-separated-values",
}

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx", ".ods", ".tsv"}

# Map MIME types to expected extensions (for extra validation)
MIME_TO_EXTS = {
    "text/csv": {".csv"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "application/vnd.oasis.opendocument.spreadsheet": {".ods"},
    "text/tab-separated-values": {".tsv"},
}


@router.post("/upload")
async def upload_spreadsheet(file: UploadFile = File(...), email: EmailStr = Form(...)):
    """
    Upload a spreadsheet file (.csv, .tsv, .xls, .xlsx, .ods) and provide a valid email.
    """
    logger.info(f"Upload request received - filename: {file.filename}, email: {email}")

    if file.size == 0:
        logger.warning(
            f"Empty file upload attempted - filename: {file.filename}, email: {email}"
        )
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 1. Detect real MIME type using magic
    try:
        detected_mime = file.content_type
        logger.debug(f"Detected MIME type: {detected_mime} for file: {file.filename}")
    except Exception as e:
        logger.error(f"Failed to detect file type for {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Unable to detect file type: {str(e)}"
        )

    # print("Detected MIME type:", detected_mime)

    if detected_mime not in ALLOWED_MIME_TYPES:
        logger.warning(
            f"Invalid MIME type detected: {detected_mime} for file: {file.filename}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Detected: {detected_mime}. Only CSV and Excel files (.csv, .xls, .xlsx, .ods, .tsv) are allowed.",
        )

    # 2. Validate file extension
    ext = Path(file.filename).suffix.lower()
    logger.debug(f"File extension: {ext} for file: {file.filename}")
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file extension: {ext} for file: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension: {ext}. Only .ods, .tsv, .csv, .xls, and .xlsx are allowed.",
        )

    # 3. Ensure extension matches MIME type
    valid_exts_for_mime = MIME_TO_EXTS.get(detected_mime, set())
    if ext not in valid_exts_for_mime:
        logger.warning(
            f"Extension mismatch - ext: {ext}, MIME: {detected_mime} for file: {file.filename}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' does not match the actual file type '{detected_mime}'.",
        )

    # 4. Save the file
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    logger.info(f"Saving file to: {file_path}")
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"File saved successfully: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # 5. Enqueue processing task
    logger.info(f"Enqueueing processing task for file: {file.filename}")
    try:
        task = process_spreadsheet_task.delay(file_path, email)
        logger.info(
            f"Task enqueued successfully - task_id: {task.id}, file: {file.filename}"
        )
    except Exception as e:
        logger.error(f"Failed to enqueue task for file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to enqueue processing task."
        )

    # 6. Send Email to the User
    logger.info(f"Sending confirmation email to: {email}, task_id: {task.id}")
    try:
        await send_task_email(email_to=email, file_name=file.filename, task_id=task.id)
        logger.info(f"Confirmation email sent successfully to: {email}")
    except HTTPException:
        # Re-raise if it's already an HTTP exception
        logger.error(f"HTTP exception while sending email to {email}")
        raise
    except Exception as e:
        # Fallback for unexpected errors
        logger.error(f"Unexpected email error for {email}: {str(e)}")
        print(f"Unexpected email error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send confirmation email."
        )

    # 7. Return the Result
    logger.info(
        f"Upload process completed successfully - filename: {file.filename}, task_id: {task.id}, email: {email}"
    )
    return {
        "email": email,
        "filename": file.filename,
        "task_id": task.id,
        "message": "File uploaded and processing started. Check your email for the task ID.",
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a processing task."""
    task = process_spreadsheet_task.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
    }
