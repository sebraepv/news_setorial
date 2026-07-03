import unittest
from pathlib import Path
from unittest.mock import patch

from newsletter.sender import NewsletterSender


class NewsletterSenderTests(unittest.TestCase):
    def test_send_newsletter_html_uses_smtp_and_keeps_html_content(self):
        sender = NewsletterSender(
            smtp_host="smtp.test",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
            from_address="from@test.com",
            to_addresses=["to@test.com"],
            use_tls=True,
            env_path=Path("variaveis.env"),
        )

        with patch("newsletter.sender.smtplib.SMTP") as smtp_cls:
            result = sender.send_newsletter_html(
                subject="Newsletter teste",
                html_content="<h1>Olá</h1>",
            )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["recipients"], ["to@test.com"])
        smtp_cls.assert_called_once_with("smtp.test", 587)
        smtp_cls.return_value.__enter__.return_value.starttls.assert_called_once()
        smtp_cls.return_value.__enter__.return_value.login.assert_called_once_with(
            "user",
            "pass",
        )


if __name__ == "__main__":
    unittest.main()
