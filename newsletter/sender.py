import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


class NewsletterSender:
    """Envia uma newsletter em HTML por e-mail usando SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_address: Optional[str] = None,
        to_addresses: Optional[List[str]] = None,
        use_tls: bool = True,
        env_path: Optional[str | Path] = None,
    ) -> None:
        env_path = env_path or Path(__file__).resolve().parents[1] / "variaveis.env"
        load_dotenv(env_path, override=False)

        self.smtp_host = (smtp_host or os.getenv("SMTP_HOST") or "").strip()
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT") or 587)
        self.smtp_username = (smtp_username or os.getenv("SMTP_USERNAME") or "").strip()
        self.smtp_password = (smtp_password or os.getenv("SMTP_PASSWORD") or "").strip()
        self.from_address = (from_address or os.getenv("SMTP_FROM") or "").strip()
        self.to_addresses = self._normalize_recipients(
            to_addresses or os.getenv("SMTP_TO") or ""
        )
        self.use_tls = use_tls

    def _normalize_recipients(self, value: Any) -> List[str]:
        if not value:
            return []

        if isinstance(value, str):
            parts = [item.strip() for item in value.replace(";", ",").split(",")]
            return [item for item in parts if item]

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        return [str(value).strip()]

    def build_message(
        self,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
    ) -> EmailMessage:
        if not subject:
            raise ValueError("Assunto é obrigatório.")

        if not html_content:
            raise ValueError("Conteúdo HTML é obrigatório.")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.from_address or "newsletter@local"
        message["To"] = ", ".join(self.to_addresses) if self.to_addresses else self.from_address
        message.set_content(plain_text or "Veja a newsletter em anexo/HTML.")
        message.add_alternative(html_content, subtype="html")
        return message

    def send_newsletter_html(
        self,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.smtp_host:
            raise RuntimeError("SMTP_HOST não configurado.")

        if not self.from_address:
            raise RuntimeError("SMTP_FROM não configurado.")

        if not self.to_addresses:
            raise RuntimeError("SMTP_TO não configurado.")

        message = self.build_message(subject, html_content, plain_text=plain_text)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.send_message(message)

        return {
            "status": "sent",
            "subject": subject,
            "recipients": self.to_addresses,
            "from": self.from_address,
        }
