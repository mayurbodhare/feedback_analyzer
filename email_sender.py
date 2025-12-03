import base64
import os
import httpx
import logging
from fastapi import HTTPException
from config import settings

logger = logging.getLogger(__name__)


async def _send_brevo_email(
    to_email: str,
    subject: str,
    body: str,
    sender_email: str,
    api_key: str,
    attachment_path: str | None = None,
) -> None:
    """
    Internal helper to send an email via Brevo API, optionally with one attachment.
    attachment_path: path to file on disk to attach (must exist).
    """
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    data = {
        "sender": {"email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    # Add attachment if provided
    if attachment_path:
        if not os.path.isfile(attachment_path):
            logger.error(f"Attachment file not found: {attachment_path}")
            raise HTTPException(status_code=400, detail="Attachment file not found.")

        try:
            with open(attachment_path, "rb") as f:
                file_content = f.read()
                encoded_content = base64.b64encode(file_content).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read/encode attachment {attachment_path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to process attachment.")

        data["attachment"] = [
            {
                "name": os.path.basename(attachment_path),
                "content": encoded_content,
            }
        ]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers=headers,
                json=data,
                timeout=30.0,  # Slightly longer timeout for attachments
            )
            response.raise_for_status()
        logger.info(f"Email with attachment sent successfully to {to_email}")
    except httpx.RequestError as e:
        logger.error(f"Network error sending email to {to_email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to send email due to network error."
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Brevo API error ({e.response.status_code}): {e.response.text} "
            f"for email to {to_email}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Email service rejected the request."
        )


async def send_task_email(email_to: str, file_name: str, task_id: str) -> None:
    """Sends initial task ID email (no attachment)."""
    if not settings.BREVO_API_KEY:
        logger.error("Brevo API key is missing.")
        raise RuntimeError("Brevo API key not configured.")

    subject = "Your Spreadsheet Processing Task ID"
    body = (
        f"Your file: {file_name} has been uploaded successfully. Your task ID is:\n\n{task_id}\n\n"
        "You can use this ID to check the status of your processing job."
    )

    logger.info(f"Sending task email to {email_to} for task {task_id}")
    await _send_brevo_email(
        to_email=email_to,
        subject=subject,
        body=body,
        sender_email=settings.SENDER_EMAIL,
        api_key=settings.BREVO_API_KEY,
        attachment_path=None,
    )


async def send_confirmation_email(file_path: str, email: str) -> None:
    """
    Sends a confirmation email with the processed file attached.
    `file_path` must be the full path to the processed output file.
    """
    if not settings.BREVO_API_KEY:
        logger.error("Brevo API key is missing.")
        raise RuntimeError("Brevo API key not configured.")

    subject = "✅ Your Processed Spreadsheet Is Ready!"
    body = (
        f"Great news! Your file has been successfully processed.\n\n"
        f"Please find the result attached: {os.path.basename(file_path)}\n\n"
        "Thank you for using our service!"
    )

    logger.info(f"Sending confirmation email with attachment to {email}")
    await _send_brevo_email(
        to_email=email,
        subject=subject,
        body=body,
        sender_email=settings.SENDER_EMAIL,
        api_key=settings.BREVO_API_KEY,
        attachment_path=file_path,
    )
    

# import httpx
# import logging
# from fastapi import HTTPException
# from config import settings

# logger = logging.getLogger(__name__)


# async def send_task_email(email_to: str, file_name: str, task_id: str):
#     """
#     Sends a simple email with the task ID using Brevo (Sendinblue) API (async).
#     Ensure Brevo API key is configured in settings.BREVO_API_KEY.
#     """
#     BREVO_API_KEY = settings.BREVO_API_KEY
#     SENDER_EMAIL = settings.SENDER_EMAIL

#     if not BREVO_API_KEY:
#         logger.error("Brevo API key is missing in settings.")
#         raise RuntimeError("Brevo API key not configured in environment variables.")

#     subject = "Your Spreadsheet Processing Task ID"
#     body = (
#         f"Your file: {file_name} has been uploaded successfully. Your task ID is:\n\n{task_id}\n\n"
#         f"You can use this ID to check the status of your processing job."
#     )

#     headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}

#     data = {
#         "sender": {"email": SENDER_EMAIL},
#         "to": [{"email": email_to}],
#         "subject": subject,
#         "textContent": body,
#     }

#     logger.info(
#         f"Attempting to send email to {email_to} for task {task_id} (file: {file_name})"
#     )

#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 "https://api.brevo.com/v3/smtp/email",
#                 headers=headers,
#                 json=data,
#                 timeout=20.0,
#             )
#             response.raise_for_status()
#         logger.info(f"Email successfully sent to {email_to} for task {task_id}")
#     except httpx.RequestError as e:
#         # Network-level error (e.g., DNS failure, refused connection)
#         logger.error(
#             f"Network error while sending email to {email_to}: {e}", exc_info=True
#         )
#         raise HTTPException(
#             status_code=500, detail="Failed to send confirmation email."
#         )
#     except httpx.HTTPStatusError as e:
#         # HTTP error (e.g., 4xx, 5xx)
#         logger.error(
#             f"Brevo API returned error {e.response.status_code}: {e.response.text} "
#             f"for email to {email_to}, task {task_id}",
#             exc_info=True,
#         )
#         raise HTTPException(
#             status_code=500, detail="Failed to send confirmation email."
#         )



# def send_confitmation_email(file_path: str, email: str):
#     pass
   
