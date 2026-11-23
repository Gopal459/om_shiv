import logging
import os
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSGateway:
    """SMS gateway adapter (Fast2SMS / MSG91 / Twilio) for high-availability OTP fallback."""

    def __init__(
        self,
        fast2sms_key: Optional[str] = None,
        msg91_key: Optional[str] = None,
    ):
        self.fast2sms_key = fast2sms_key or settings.FAST2SMS_API_KEY
        self.msg91_key = msg91_key or settings.MSG91_AUTH_KEY
        self.sent_messages: list = []

    async def send_otp(self, mobile: str, otp: str) -> bool:
        """Send 6-digit numeric OTP via SMS fallback gateway."""
        # Testing/Dev mock mode
        if (
            os.environ.get("PYTEST_CURRENT_TEST")
            or os.environ.get("TESTING", "").lower() in ("true", "1")
            or (not self.fast2sms_key and not self.msg91_key)
        ):
            logger.info("SMS Gateway [MOCK]: Dispatched fallback OTP to %s", mobile)
            self.sent_messages.append({"mobile": mobile, "otp": otp, "channel": "SMS_FALLBACK"})
            return True

        # Fast2SMS live dispatch
        if self.fast2sms_key:
            headers = {
                "authorization": self.fast2sms_key,
                "Content-Type": "application/json",
            }
            payload = {
                "route": "otp",
                "variables_values": otp,
                "numbers": mobile.replace("+91", "").strip(),
            }
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        "https://www.fast2sms.com/dev/bulkV2",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code == 200 and resp.json().get("return") is True:
                        logger.info("SMS fallback OTP sent to %s via Fast2SMS", mobile)
                        return True
            except Exception as exc:
                logger.error("Fast2SMS delivery failed: %s", exc)

        # MSG91 fallback if Fast2SMS fails or unconfigured
        if self.msg91_key:
            headers = {"authkey": self.msg91_key}
            params = {
                "mobile": mobile.replace("+91", "").strip(),
                "otp": otp,
            }
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.msg91.com/api/v5/otp",
                        params=params,
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        logger.info("SMS fallback OTP sent to %s via MSG91", mobile)
                        return True
            except Exception as exc:
                logger.error("MSG91 delivery failed: %s", exc)

        return False


sms_gateway = SMSGateway()
