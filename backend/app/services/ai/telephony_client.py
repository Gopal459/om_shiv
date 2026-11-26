"""Exotel Telephony Client.

Integrates with Exotel Outbound Voice Calling API with mock fallback for local testing and CI/CD.
Contract:
- Outbound Call API: POST https://{api_key}:{api_token}@api.exotel.com/v1/Accounts/{sid}/Calls/connect.json
- Payload: From={agent_flow_number}, To={customer_mobile}, CallerId={virtual_number}, StatusCallback={webhook_url}, CustomField={custom_field}
"""

from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ExotelTelephonyClient:
    """Telephony Client for Exotel outbound calling and voice agent dispatch."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_token: Optional[str] = None,
        account_sid: Optional[str] = None,
        caller_id: Optional[str] = None,
        flow_number: Optional[str] = None,
        status_callback_url: Optional[str] = None,
        mock: Optional[bool] = None,
    ):
        self.api_key = api_key or os.environ.get("EXOTEL_API_KEY", getattr(settings, "EXOTEL_API_KEY", ""))
        self.api_token = api_token or os.environ.get("EXOTEL_API_TOKEN", getattr(settings, "EXOTEL_API_TOKEN", ""))
        self.account_sid = account_sid or os.environ.get("EXOTEL_ACCOUNT_SID", getattr(settings, "EXOTEL_ACCOUNT_SID", ""))
        self.caller_id = caller_id or os.environ.get("EXOTEL_CALLER_ID", getattr(settings, "EXOTEL_CALLER_ID", ""))
        self.flow_number = flow_number or os.environ.get("EXOTEL_FLOW_NUMBER", getattr(settings, "EXOTEL_FLOW_NUMBER", ""))
        self.status_callback_url = (
            status_callback_url
            or os.environ.get("EXOTEL_STATUS_CALLBACK_URL", getattr(settings, "EXOTEL_STATUS_CALLBACK_URL", ""))
        )

        if mock is not None:
            self.mock = mock
        else:
            self.mock = bool(
                os.environ.get("PYTEST_CURRENT_TEST")
                or os.environ.get("TESTING", "").lower() in ("true", "1")
                or not (self.api_key and self.api_token and self.account_sid)
            )

        self.calls_dispatched: int = 0
        self.dispatched_calls: List[Dict[str, Any]] = []

    async def dispatch_call(
        self,
        to_mobile: str,
        custom_field: Optional[str] = None,
        callback_url: Optional[str] = None,
        flow_number: Optional[str] = None,
        caller_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Dispatches an outbound call to customer mobile via Exotel API.

        Args:
            to_mobile: Destination phone number.
            custom_field: Optional tracking identifier (e.g. lead_id).
            callback_url: Optional webhook URL for call events.
            flow_number: Optional flow/app number overriding default.
            caller_id: Optional caller ID virtual number.
            **kwargs: Extra parameters.

        Returns:
            Dictionary containing call_sid, status, and metadata.
        """
        self.calls_dispatched += 1
        norm_mobile = to_mobile.strip()
        if not norm_mobile.startswith("+") and not norm_mobile.startswith("0") and len(norm_mobile) == 10:
            formatted_mobile = f"0{norm_mobile}"
        else:
            formatted_mobile = norm_mobile

        record = {
            "to_mobile": to_mobile,
            "custom_field": custom_field,
            "callback_url": callback_url or self.status_callback_url,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self.dispatched_calls.append(record)

        if self.mock:
            call_sid = f"mock-exotel-{uuid.uuid4().hex[:12]}"
            logger.info("Exotel Telephony [MOCK]: Dispatched call to %s (custom_field=%s)", to_mobile, custom_field)
            return {
                "success": True,
                "call_sid": call_sid,
                "status": "QUEUED",
                "to_mobile": to_mobile,
                "custom_field": custom_field,
                "dispatched_at": record["dispatched_at"],
                "mock": True,
            }

        url = f"https://api.exotel.com/v1/Accounts/{self.account_sid}/Calls/connect.json"
        auth = (self.api_key, self.api_token)
        payload = {
            "From": flow_number or self.flow_number,
            "To": formatted_mobile,
            "CallerId": caller_id or self.caller_id,
            "StatusCallback": callback_url or self.status_callback_url,
        }
        if custom_field:
            payload["CustomField"] = custom_field

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, auth=auth, data=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    call_info = data.get("Call", {})
                    call_sid = call_info.get("Sid") or data.get("Sid")
                    call_status = call_info.get("Status", "QUEUED")
                    logger.info("Exotel call successfully queued: %s for %s", call_sid, to_mobile)
                    return {
                        "success": True,
                        "call_sid": call_sid,
                        "status": call_status,
                        "raw": data,
                    }
                else:
                    logger.error(
                        "Exotel call failed to %s: HTTP %s - %s",
                        to_mobile,
                        resp.status_code,
                        resp.text,
                    )
                    return {
                        "success": False,
                        "call_sid": None,
                        "status": "FAILED",
                        "error": f"Exotel HTTP {resp.status_code}: {resp.text}",
                    }
        except Exception as exc:
            logger.exception("Exotel API exception during call dispatch to %s: %s", to_mobile, exc)
            return {
                "success": False,
                "call_sid": None,
                "status": "ERROR",
                "error": str(exc),
            }

    # Aliases
    initiate_call = dispatch_call
    trigger_call = dispatch_call
