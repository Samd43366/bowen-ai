import logging
from app.core.config import settings
import aiosmtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, body: str):
    if settings.SMTP_SERVER == "localhost":
        logger.info(f"Using local SMTP mode. Check your local SMTP server for email to {to_email}.")
        print(f"\n--- LOCAL SMTP EMAIL ---\nTo: {to_email}\nSubject: {subject}\n{body}\n-----------------------\n")
    elif not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(f"SMTP credentials not set. Simulating email to {to_email}.")
        print(f"\n--- EMAIL SIMULATOR ---\nTo: {to_email}\nSubject: {subject}\n{body}\n-----------------------\n")
        return

    message = EmailMessage()
    message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        if settings.SMTP_SERVER == "localhost":
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_SERVER,
                port=settings.SMTP_PORT
            )
        else:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_SERVER,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT == 465),
                start_tls=(settings.SMTP_PORT == 587)
            )
        logger.info(f"SMTP Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {str(e)}")
        raise Exception(f"Failed to send email via SMTP: {str(e)}")


async def send_otp_email(to_email: str, otp_code: str):
    subject = "Your Bowen AI Verification Code"
    body = f"""
Hello,

Your Bowen AI verification code is: {otp_code}

This code will expire in 1 minute.

If you did not request this, please ignore this email.
"""
    await send_email(to_email, subject, body)
    
    
async def send_welcome_email(to_email: str, full_name: str, role: str):
    subject = "Welcome to Bowen AI!"
    role_text = "Administrator" if role in ["admin", "superadmin"] else "User"
    body = f"""
Hello {full_name},

Welcome to Bowen AI! Your account as a {role_text} has been successfully verified.

We are thrilled to have you on board. You can now access all the features of the platform.

Best regards,
The Bowen AI Team
"""
    await send_email(to_email, subject, body)