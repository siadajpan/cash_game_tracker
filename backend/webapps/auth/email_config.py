import os
from pathlib import Path
from fastapi_mail import ConnectionConfig
from backend.core.config import TEMPLATES_DIR

conf = ConnectionConfig(
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_FROM=os.environ.get("MAIL_FROM"),
    MAIL_SERVER=os.environ.get("MAIL_SERVER"),
    # Convert port to int, default to 587 if not found
    MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
    # Standard AWS SES / STARTTLS Defaults
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=TEMPLATES_DIR / "email",
)
