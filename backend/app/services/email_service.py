import aiosmtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from app.core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL


async def send_otp_email(to_email: str, otp_code: str):
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # If SMTP settings are missing, log OTP code for development
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"({timestamp_str}) SMTP credentials not set. DEV MODE Verification OTP for {to_email}: [{otp_code}]")
        return

    message = EmailMessage()
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = f"Kode Verifikasi OTP Anda: {otp_code}"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #09090b; color: #f4f4f5; padding: 20px;">
        <div style="max-width: 480px; margin: 0 auto; background-color: #18181b; padding: 24px; border-radius: 12px; border: 1px solid #27272a;">
          <h2 style="color: #38bdf8; margin-top: 0;">Verifikasi Akun AI Resume</h2>
          <p>Gunakan kode OTP 6-digit di bawah ini untuk memverifikasi akun Anda :</p>
          <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #ffffff; text-align: center; margin: 24px 0; background-color: #27272a; padding: 12px; border-radius: 8px;">
            {otp_code}
          </div>
          <p style="font-size: 12px; color: #a1a1aa;">Kode ini berlaku selama 10 menit. Jangan bagikan kode ini kepada siapapun.</p>
        </div>
      </body>
    </html>
    """
    message.add_alternative(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"({timestamp_str}) Successfully sent OTP email to {to_email}")
    except Exception as exc:
        print(f"({timestamp_str}) Failed to send OTP email to {to_email}: {exc}")
        print(f"({timestamp_str}) DEV FALLBACK OTP Code for {to_email}: [{otp_code}]")
