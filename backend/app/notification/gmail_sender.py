import os
import smtplib
from email.mime.text import MIMEText


class GmailSender:
    def __init__(self):
        self.gmail_account = os.getenv("GMAIL_ACCOUNT")
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
        self.gmail_host = os.getenv("GMAIL_HOST", "smtp.gmail.com")
        self.gmail_port = int(os.getenv("GMAIL_PORT", "587"))
        self.gmail_from = os.getenv("GMAIL_FROM", self.gmail_account)

        if not self.gmail_account or not self.gmail_app_password:
            raise ValueError("GMAIL_ACCOUNT and GMAIL_APP_PASSWORD must be set")

    def send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.gmail_from
            msg["To"] = recipient_email

            with smtplib.SMTP(self.gmail_host, self.gmail_port, timeout=20) as server:
                server.starttls()
                server.login(self.gmail_account, self.gmail_app_password)
                server.send_message(msg)
            return True
        except Exception as e:
            raise Exception(f"Failed to send email to {recipient_email}: {e}")
        return False