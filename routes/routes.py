from pathlib import Path
from fastapi import APIRouter, UploadFile, HTTPException, File, Form, Depends, Request
from pydantic import EmailStr
import uuid
import os
import logging
from worker.celery_worker import process_spreadsheet_task
from email_sender import send_task_email
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_db
from db import Task, TaskStatus, TaskStage
from utils.column_validator import validate_columns, rename_columns_to_standard
from utils.file_utils import read_file

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()


# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

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

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """
    Serve the file upload page
    """
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


@router.post("/upload")
async def upload_spreadsheet(file: UploadFile = File(...), email: EmailStr = Form(...), db: AsyncSession = Depends(get_db)):
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
    temp_file_path = f"uploads/{file.filename}"
    logger.info(f"Saving file to: {temp_file_path}")
    try:
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"File saved successfully: {temp_file_path}")
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")
    
     # 5. Validate columns in the file
    logger.info(f"Validating columns in file: {file.filename}")
    try:
        df = read_file(temp_file_path)
        logger.debug(f"File read successfully, shape: {df.shape}")
        logger.debug(f"Original columns: {list(df.columns)}")
        
        # Validate columns with fuzzy matching (threshold: 0.8)
        is_valid, validation_result = validate_columns(df, threshold=0.8)
        
        if not is_valid:
            logger.warning(f"Column validation failed for file: {file.filename}")
            logger.warning(f"Missing columns: {validation_result['missing_columns']}")
            logger.warning(f"Found columns: {validation_result['found_columns']}")
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            # Build detailed error message
            error_message = "Required columns are missing or incorrectly named.\n\n"
            error_message += f"Missing columns: {', '.join(validation_result['missing_columns'])}\n\n"
            
            if validation_result['suggestions']:
                error_message += "Suggestions:\n"
                for missing_col, suggestion in validation_result['suggestions'].items():
                    error_message += f"  - '{missing_col}' might be '{suggestion['suggested_column']}' (similarity: {suggestion['similarity']}%)\n"
            
            error_message += "\nRequired columns (case-insensitive, spaces normalized):\n"
            error_message += "  - depute geography\n"
            error_message += "  - depute country\n"
            error_message += "  - depute branch\n"
            error_message += "  - depute datacenter\n"
            error_message += "  - question\n"
            error_message += "  - answer\n"
            
            raise HTTPException(status_code=400, detail=error_message)
        
        logger.info(f"Column validation passed for file: {file.filename}")
        logger.info(f"Column mapping: {validation_result['found_columns']}")
        
        # Rename columns to standard names
        df_renamed, success, _ = rename_columns_to_standard(df, threshold=0.8)
        
        if not success:
            logger.error(f"Failed to rename columns for file: {file.filename}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(status_code=500, detail="Failed to process file columns.")
        
        # Save the file with renamed columns
        
        random_filename = f"{uuid.uuid4().hex}"
        random_filename_with_extension = f"{random_filename}{ext}" 
        final_file_path = f"uploads/{random_filename_with_extension}"
        logger.info(f"Saving file with renamed columns to: {final_file_path}")

        # Determine file format and save appropriately
        if ext == '.csv':
            df_renamed.to_csv(final_file_path, index=False)
        elif ext in ['.xlsx', '.xls']:
            df_renamed.to_excel(final_file_path, index=False, engine='openpyxl' if ext == '.xlsx' else 'xlwt')
        elif ext == '.ods':
            df_renamed.to_excel(final_file_path, index=False, engine='odf')
        else:
            # Fallback to CSV
            df_renamed.to_csv(final_file_path, index=False)
        
        logger.info(f"File saved with standardized columns: {final_file_path}")
        
        # Remove temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.debug(f"Removed temporary file: {temp_file_path}")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error validating/processing file {file.filename}: {str(e)}", exc_info=True)
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to validate file structure: {str(e)}"
        )


    # 6. Enqueue processing task
    logger.info(f"Enqueueing processing task for file: {file.filename}")
    try:
        task = process_spreadsheet_task.delay(final_file_path, email)
        logger.info(
            f"Task enqueued successfully - task_id: {task.id}, file: {file.filename}"
        )
    except Exception as e:
        logger.error(f"Failed to enqueue task for file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to enqueue processing task."
        )
    
    # 7. Create task record in database
    logger.info(f"Creating database record for task_id: {task.id}")
    try:
        db_task = Task(
            job_id=task.id,
            file_id=random_filename,
            file_path=final_file_path,
            email=email,
            status=TaskStatus.PENDING,
            stage=TaskStage.QUEUE
        )
        db.add(db_task)
        await db.commit()
        await db.refresh(db_task)
        logger.info(f"Database record created successfully for task_id: {task.id}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create database record for task {task.id}: {str(e)}")
        # Don't fail the request - task is already queued
        logger.warning("Continuing despite database error - task is already queued")


    # 8. Send Email to the User
    # logger.info(f"Sending confirmation email to: {email}, task_id: {task.id}")
    # try:
    #     await send_task_email(email_to=email, file_name=file.filename, task_id=task.id)
    #     logger.info(f"Confirmation email sent successfully to: {email}")
    # except HTTPException:
    #     # Re-raise if it's already an HTTP exception
    #     logger.error(f"HTTP exception while sending email to {email}")
    #     raise
    # except Exception as e:
    #     # Fallback for unexpected errors
    #     logger.error(f"Unexpected email error for {email}: {str(e)}")
    #     print(f"Unexpected email error: {e}")
    #     raise HTTPException(
    #         status_code=500, detail="Failed to send confirmation email."
    #     )

    # 9. Return the Result
    logger.info(
        f"Upload process completed successfully - filename: {file.filename}, task_id: {task.id}, email: {email}"
    )
    return {
        "email": email,
        "filename": random_filename_with_extension,
        "task_id": task.id,
        "message": "File uploaded and processing started. Check your email for the task ID.",
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get the status of a processing task from both Celery and database."""
    logger.info(f"Status check requested for task_id: {task_id}")

    # Get Celery task status
    celery_task = process_spreadsheet_task.AsyncResult(task_id)
    celery_status = celery_task.status

    # Get database task status
    try:
        result = await db.execute(select(Task).where(Task.job_id == task_id))
        db_task = result.scalar_one_or_none()

        if db_task:
            logger.info(
                f"Task found in database: {task_id}, status: {db_task.status.value}, stage: {db_task.stage.value}"
            )
            return {
                "task_id": task_id,
                "celery_status": celery_status,
                "status": db_task.status.value,
                "stage": db_task.stage.value,
                "email": db_task.email,
                "created_at": (
                    db_task.created_at.isoformat() if db_task.created_at else None
                ),
                "updated_at": (
                    db_task.updated_at.isoformat() if db_task.updated_at else None
                ),
                "results": (
                    {
                        "distribution_chart": db_task.distribution_chart,
                        "wordcloud": db_task.wordcloud,
                        "treemap": db_task.treemap,
                        "sunburst": db_task.sunburst,
                        "summary": db_task.summary,
                    }
                    if db_task.status == TaskStatus.COMPLETED
                    else None
                ),
                "error_message": (
                    db_task.error_message
                    if hasattr(db_task, "error_message")
                    and db_task.status == TaskStatus.FAILED
                    else None
                ),
            }
        else:
            logger.warning(f"Task not found in database: {task_id}")
            return {
                "task_id": task_id,
                "celery_status": celery_status,
                "status": "not_found",
                "message": "Task not found in database. It may not have been created yet.",
            }
    except Exception as e:
        logger.error(f"Error retrieving task status from database: {str(e)}")
        # Return Celery status even if database query fails
        return {
            "task_id": task_id,
            "celery_status": celery_status,
            "status": "database_error",
            "message": "Could not retrieve task from database.",
        }


@router.get("/tasks/user/{email}")
async def get_user_tasks(email: EmailStr, db: AsyncSession = Depends(get_db)):
    """Get all tasks for a specific user email."""
    logger.info(f"Retrieving all tasks for email: {email}")

    try:
        result = await db.execute(
            select(Task).where(Task.email == email).order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()

        logger.info(f"Found {len(tasks)} tasks for email: {email}")
        return {
            "email": email,
            "count": len(tasks),
            "tasks": [
                {
                    "task_id": task.job_id,
                    "status": task.status.value,
                    "stage": task.stage.value,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                    "updated_at": (
                        task.updated_at.isoformat() if task.updated_at else None
                    ),
                    "has_results": task.status == TaskStatus.COMPLETED,
                }
                for task in tasks
            ],
        }
    except Exception as e:
        logger.error(f"Error retrieving tasks for email {email}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve tasks from database."
        )


@router.get("/results/{task_id}")
async def get_task_results(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed results for a completed task."""
    logger.info(f"Results requested for task_id: {task_id}")

    try:
        result = await db.execute(select(Task).where(Task.job_id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status != TaskStatus.COMPLETED:
            logger.warning(
                f"Task not completed yet: {task_id}, current status: {task.status.value}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed yet. Current status: {task.status.value}",
            )

        logger.info(f"Returning results for task_id: {task_id}")
        return {
            "task_id": task.job_id,
            "email": task.email,
            "status": task.status.value,
            "distribution_chart": task.distribution_chart,
            "wordcloud": task.wordcloud,
            "treemap": task.treemap,
            "sunburst": task.sunburst,
            "summary": task.summary,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.updated_at.isoformat() if task.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task results.")
