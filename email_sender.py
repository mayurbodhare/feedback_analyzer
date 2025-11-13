import httpx
import logging
from fastapi import HTTPException
from config import settings

logger = logging.getLogger(__name__)


async def send_task_email(email_to: str, file_name: str, task_id: str):
    """
    Sends a simple email with the task ID using Brevo (Sendinblue) API (async).
    Ensure Brevo API key is configured in settings.BREVO_API_KEY.
    """
    BREVO_API_KEY = settings.BREVO_API_KEY
    SENDER_EMAIL = settings.SENDER_EMAIL

    if not BREVO_API_KEY:
        logger.error("Brevo API key is missing in settings.")
        raise RuntimeError("Brevo API key not configured in environment variables.")

    subject = "Your Spreadsheet Processing Task ID"
    body = (
        f"Your file: {file_name} has been uploaded successfully. Your task ID is:\n\n{task_id}\n\n"
        f"You can use this ID to check the status of your processing job."
    )

    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}

    data = {
        "sender": {"email": SENDER_EMAIL},
        "to": [{"email": email_to}],
        "subject": subject,
        "textContent": body,
    }

    logger.info(
        f"Attempting to send email to {email_to} for task {task_id} (file: {file_name})"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers=headers,
                json=data,
                timeout=20.0,
            )
            response.raise_for_status()
        logger.info(f"Email successfully sent to {email_to} for task {task_id}")
    except httpx.RequestError as e:
        # Network-level error (e.g., DNS failure, refused connection)
        logger.error(
            f"Network error while sending email to {email_to}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to send confirmation email."
        )
    except httpx.HTTPStatusError as e:
        # HTTP error (e.g., 4xx, 5xx)
        logger.error(
            f"Brevo API returned error {e.response.status_code}: {e.response.text} "
            f"for email to {email_to}, task {task_id}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to send confirmation email."
        )
