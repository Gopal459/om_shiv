"""Deterministic test mocks and fixtures for AI agents and telephony services.

Used across all AI agent test suites to ensure 100% deterministic, zero-cost,
offline testing without invoking external APIs.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest


class MockAIClientService:
    """Deterministic mock for AIClientService.
    
    Allows test cases to queue single or sequence responses and inspect all prompt arguments.
    """

    def __init__(self):
        self.canned_response: Optional[Dict[str, Any]] = None
        self.canned_responses: List[Dict[str, Any]] = []
        self.call_history: List[Dict[str, Any]] = []
        self.last_latency_ms: float = 5.0
        self.last_usage: Dict[str, int] = {
            "prompt_tokens": 20,
            "completion_tokens": 30,
            "total_tokens": 50,
        }

    def set_canned_response(self, response: Dict[str, Any]) -> None:
        """Sets a single canned response returned for all future calls."""
        self.canned_response = response

    def set_canned_responses(self, responses: List[Dict[str, Any]]) -> None:
        """Sets a FIFO queue of canned responses for sequential multi-turn calls."""
        self.canned_responses = list(responses)

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        fallback_data: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Records call history and returns the queued canned response or fallback."""
        self.call_history.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "schema": schema,
            "fallback_data": fallback_data,
            "model": model,
            "kwargs": kwargs,
        })

        if self.canned_responses:
            return self.canned_responses.pop(0)
        if self.canned_response is not None:
            return dict(self.canned_response)
        if fallback_data is not None:
            return fallback_data
        return {}

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Simple deterministic token estimation."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def reset(self) -> None:
        """Clears canned responses and recorded call history."""
        self.canned_response = None
        self.canned_responses.clear()
        self.call_history.clear()


class MockTelephonyClient:
    """Deterministic mock for outbound and inbound AI Telephony integrations."""

    def __init__(self):
        self.calls_dispatched: int = 0
        self.dispatched_calls: List[Dict[str, Any]] = []
        self.canned_call_result: Optional[Dict[str, Any]] = None

    def set_canned_call_result(self, result: Dict[str, Any]) -> None:
        """Sets the result returned by dispatch_call."""
        self.canned_call_result = result

    async def dispatch_call(
        self,
        to_mobile: str,
        script: Optional[str] = None,
        agent_name: Optional[str] = None,
        lead_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Records call dispatch and returns mock call metadata."""
        self.calls_dispatched += 1
        record = {
            "to_mobile": to_mobile,
            "script": script,
            "agent_name": agent_name,
            "lead_id": lead_id,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self.dispatched_calls.append(record)

        if self.canned_call_result is not None:
            return dict(self.canned_call_result)
        return {
            "call_sid": f"mock-call-{self.calls_dispatched}",
            "status": "QUEUED",
            "to_mobile": to_mobile,
        }

    # Common aliases used across different caller conventions
    trigger_call = dispatch_call
    initiate_call = dispatch_call
    make_call = dispatch_call

    def reset(self) -> None:
        """Resets call counter and history."""
        self.calls_dispatched = 0
        self.dispatched_calls.clear()
        self.canned_call_result = None


@pytest.fixture
def mock_ai_service() -> MockAIClientService:
    """Pytest fixture providing a fresh MockAIClientService instance."""
    return MockAIClientService()


@pytest.fixture
def mock_telephony_client() -> MockTelephonyClient:
    """Pytest fixture providing a fresh MockTelephonyClient instance."""
    return MockTelephonyClient()
