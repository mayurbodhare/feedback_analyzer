import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from config import settings

def send_task_email(email_to: str, task_id: str):
    """
    Sends a simple email with the task ID.
    Configure SMTP settings below.
    """
    SMTP_SERVER = "smtp.gmail.com"  # e.g., for Gmail
    SMTP_PORT = 587
    SMTP_USERNAME = settings.SMTP_USERNAME  # e.g., your_email@gmail.com
    SMTP_PASSWORD = settings.SMTP_PASSWORD  # app password if using Gmail

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError("SMTP credentials not configured in environment variables.")

    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = email_to
    msg["Subject"] = "Your Spreadsheet Processing Task ID"

    body = f"Your file has been uploaded successfully. Your task ID is:\n\n{task_id}\n\nYou can use this ID to check the status of your processing job."
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable security
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        # Log error in production; don't expose to user
        print(f"Failed to send email to {email_to}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send confirmation email.")
    