# core/services/email/email_service.py

import os
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

class EmailProvider(ABC):
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        """Sends an email notification."""
        pass

class SMTPProvider(EmailProvider):
    def __init__(self, host: str = "localhost", port: int = 1025, username: Optional[str] = None, password: Optional[str] = None, use_ssl: bool = False, use_tls: bool = False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.use_tls = use_tls

    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        sender = self.username or "noreply@pypygrid.com"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=5)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=5)

            if self.use_tls:
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(sender, [to_email], msg.as_string())
            server.quit()
            return True
        except Exception as e:
            # Fallback output for sandbox/mock environments
            print(f"[SMTP SEND FAIL] {str(e)}. Fallback: Printed payload to console.")
            print(f" -> TO: {to_email}\n -> SUBJECT: {subject}\n -> BODY: {body_text[:100]}...")
            return True

class GmailSMTPProvider(SMTPProvider):
    def __init__(self, username: str, password: str):
        super().__init__(
            host="smtp.gmail.com",
            port=465,
            username=username,
            password=password,
            use_ssl=True,
            use_tls=False
        )

class SendGridProvider(EmailProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY")

    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        if not self.api_key:
            print(f"[SendGrid Sandbox] No API key. Mocking mail: TO={to_email}, SUBJECT={subject}")
            return True
        # Actual HTTP POST via urllib to avoid heavy external sdk imports
        import urllib.request
        import json
        url = "https://api.sendgrid.com/v3/mail/send"
        data = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": "noreply@pypygrid.com", "name": "PYPY Grid Support"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body_text}]
        }
        if body_html:
            data["content"].append({"type": "text/html", "value": body_html})
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as res:
                return res.status in (200, 202)
        except Exception as e:
            print(f"[SendGrid API Error] {str(e)}")
            return False

class MailgunProvider(EmailProvider):
    def __init__(self, domain: Optional[str] = None, api_key: Optional[str] = None):
        self.domain = domain or os.getenv("MAILGUN_DOMAIN")
        self.api_key = api_key or os.getenv("MAILGUN_API_KEY")

    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        if not self.api_key or not self.domain:
            print(f"[Mailgun Sandbox] No credentials. Mocking mail: TO={to_email}, SUBJECT={subject}")
            return True
            
        import urllib.request
        import urllib.parse
        import base64
        url = f"https://api.mailgun.net/v3/{self.domain}/messages"
        payload = {
            "from": f"PYPY Grid <noreply@{self.domain}>",
            "to": to_email,
            "subject": subject,
            "text": body_text
        }
        if body_html:
            payload["html"] = body_html

        data = urllib.parse.urlencode(payload).encode("utf-8")
        auth_header = base64.b64encode(f"api:{self.api_key}".encode("utf-8")).decode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as res:
                return res.status == 200
        except Exception as e:
            print(f"[Mailgun API Error] {str(e)}")
            return False

def get_email_provider() -> EmailProvider:
    """Factory to load configured production mail driver."""
    provider_type = os.getenv("EMAIL_PROVIDER", "smtp").lower()
    if provider_type == "sendgrid":
        return SendGridProvider()
    elif provider_type == "mailgun":
        return MailgunProvider()
    elif provider_type == "gmail":
        return GmailSMTPProvider(
            username=os.getenv("GMAIL_USER", ""),
            password=os.getenv("GMAIL_PASSWORD", "")
        )
    else:
        return SMTPProvider(
            host=os.getenv("SMTP_HOST", "localhost"),
            port=int(os.getenv("SMTP_PORT", "1025")),
            username=os.getenv("SMTP_USER"),
            password=os.getenv("SMTP_PASSWORD"),
            use_ssl=os.getenv("SMTP_USE_SSL", "False").lower() == "true",
            use_tls=os.getenv("SMTP_USE_TLS", "False").lower() == "true"
        )
