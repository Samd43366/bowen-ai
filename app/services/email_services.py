import aiosmtplib
from email.message import EmailMessage
from app.core.config import settings


async def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=True if settings.SMTP_PORT == 465 else False,
        start_tls=True if settings.SMTP_PORT == 587 else False,
        timeout=15
    )


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