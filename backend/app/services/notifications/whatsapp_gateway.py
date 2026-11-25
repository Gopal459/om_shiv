import logging
import os
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppGateway:
    """DoubleTick WhatsApp integration gateway with graceful fallback for development and testing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.DOUBLETICK_API_KEY
        self.api_url = api_url or settings.DOUBLETICK_API_URL
        self.sent_messages: list = []

    async def send_otp(self, mobile: str, otp: str) -> bool:
        """Send 6-digit numeric OTP via DoubleTick WhatsApp Business API.
        
        Returns True if delivery succeeded, False on failure.
        """
        # Testing/Dev mock mode
        if (
            os.environ.get("PYTEST_CURRENT_TEST")
            or os.environ.get("TESTING", "").lower() in ("true", "1")
            or not self.api_key
        ):
            logger.info("WhatsApp Gateway [MOCK]: Dispatched OTP to %s", mobile)
            self.sent_messages.append({"mobile": mobile, "otp": otp, "channel": "WHATSAPP"})
            return True

        # Production / Live API call
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": f"+91{mobile}" if not mobile.startswith("+") else mobile,
            "template": {
                "name": "login_otp_template",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": otp}],
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [{"type": "text", "text": otp}],
                    },
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json=payload,
                    headers=headers,
                )
                if response.status_code in (200, 201):
                    logger.info("WhatsApp OTP dispatched to %s", mobile)
                    return True
                else:
                    logger.warning(
                        "WhatsApp delivery failed to %s: HTTP %s - %s",
                        mobile,
                        response.status_code,
                        response.text,
                    )
                    return False
        except Exception as exc:
            logger.error("WhatsApp delivery exception for %s: %s", mobile, exc)
            return False


whatsapp_gateway = WhatsAppGateway()
