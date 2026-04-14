import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, body: str):
    if not settings.BREVO_API_KEY:
        logger.warning(f"BREVO API KEY not set. Simulating email to {to_email}.")
        print(f"\n--- EMAIL SIMULATOR ---\nTo: {to_email}\nSubject: {subject}\n{body}\n-----------------------\n")
        return

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {
            "name": settings.EMAIL_FROM_NAME,
            "email": settings.EMAIL_FROM
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            logger.info(f"Email sent successfully to {to_email} via Brevo HTTP API")
        except Exception as e:
            logger.error(f"Failed to send email via Brevo: {str(e)}")
            raise Exception(f"Failed to send email via Brevo: {str(e)}")


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