from pathlib import Path
from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from pydantic import EmailStr
import os 
from celery_worker import process_spreadsheet_task 
from email_sender import send_task_email

router = APIRouter()

# Allowed MIME types and extensions
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",                      
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/tab-separated-values",
}

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx",  ".ods", ".tsv"}

# Map MIME types to expected extensions (for extra validation)
MIME_TO_EXTS = {
    "text/csv": {".csv"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "application/vnd.oasis.opendocument.spreadsheet": {".ods"},
    "text/tab-separated-values": {".tsv"},
}

@router.post("/upload")
async def upload_spreadsheet(
    file: UploadFile = File(...),
    email: EmailStr = Form(...)
    ):
        """
        Upload a spreadsheet file (.csv, .tsv, .xls, .xlsx, .ods) and provide a valid email.
        """

        if file.size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # 1. Detect real MIME type using magic
        try:
            detected_mime = file.content_type
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unable to detect file type: {str(e)}")

        # print("Detected MIME type:", detected_mime)

        if detected_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Detected: {detected_mime}. Only CSV and Excel files (.csv, .xls, .xlsx, .ods, .tsv) are allowed."
            )

        # 2. Validate file extension
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension: {ext}. Only .ods, .tsv, .csv, .xls, and .xlsx are allowed."
            )

        # 3. Ensure extension matches MIME type
        valid_exts_for_mime = MIME_TO_EXTS.get(detected_mime, set())
        if ext not in valid_exts_for_mime:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{ext}' does not match the actual file type '{detected_mime}'."
            )

        # 4. Save the file
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # 5. Enqueue processing task
        task = process_spreadsheet_task.delay(file_path, email)

        # 6. Send Email to the User
        try:
            send_task_email(email_to=email, task_id=task.id)
        except HTTPException:
            # Re-raise if it's already an HTTP exception
            raise
        
        except Exception as e:
            # Fallback for unexpected errors
            print(f"Unexpected email error: {e}")
            raise HTTPException(status_code=500, detail="Failed to send confirmation email.")

        # 7. Return the Result
        return {
            "email": email,                    
            "filename": file.filename,
            "extension": ext,
            "detected_mime": detected_mime,
            "file_size_bytes": file.size,
            "saved_at": file_path,
            "task_id": task.id, 
        }