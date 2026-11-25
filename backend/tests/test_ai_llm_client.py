import pytest
from app.services.ai.llm_client import AIClientService
from app.services.ai.prompts import (
    PROPERTY_SEARCH_SYSTEM_PROMPT,
    LEAD_QUALIFICATION_SYSTEM_PROMPT,
    CUSTOMER_SUPPORT_SYSTEM_PROMPT,
    SALES_ASSISTANT_SYSTEM_PROMPT,
    DOCUMENT_EXTRACTION_SYSTEM_PROMPT,
    WHATSAPP_AGENT_SYSTEM_PROMPT,
    VOICE_CALLING_SYSTEM_PROMPT,
    get_system_prompt,
)
from tests.ai_mocks import MockAIClientService, MockTelephonyClient, mock_ai_service, mock_telephony_client


@pytest.mark.asyncio
async def test_llm_deterministic_mock():
    mock_client = MockAIClientService()
    mock_client.set_canned_response({"location": "Jaipur", "bhk": 3, "budget_max": 8000000})
    res = await mock_client.chat_completion_json("sys", "user", {})
    assert res["location"] == "Jaipur"
    assert res["bhk"] == 3
    assert len(mock_client.call_history) == 1
    assert mock_client.call_history[0]["system_prompt"] == "sys"
    assert mock_client.call_history[0]["user_prompt"] == "user"


@pytest.mark.asyncio
async def test_mock_ai_client_sequential_responses():
    mock_client = MockAIClientService()
    resp1 = {"stage": "FIRST", "score": 40}
    resp2 = {"stage": "SECOND", "score": 85}
    mock_client.set_canned_responses([resp1, resp2])

    r1 = await mock_client.chat_completion_json("sys", "user 1")
    r2 = await mock_client.chat_completion_json("sys", "user 2")

    assert r1["stage"] == "FIRST"
    assert r1["score"] == 40
    assert r2["stage"] == "SECOND"
    assert r2["score"] == 85
    assert len(mock_client.call_history) == 2


@pytest.mark.asyncio
async def test_mock_ai_service_fixture(mock_ai_service):
    assert isinstance(mock_ai_service, MockAIClientService)
    mock_ai_service.set_canned_response({"status": "ok"})
    res = await mock_ai_service.chat_completion_json("prompt", "query")
    assert res["status"] == "ok"


@pytest.mark.asyncio
async def test_mock_telephony_client(mock_telephony_client):
    assert isinstance(mock_telephony_client, MockTelephonyClient)
    assert mock_telephony_client.calls_dispatched == 0

    call_res = await mock_telephony_client.dispatch_call(
        to_mobile="9829012345",
        script="Namaste, this is Propira Omshiv.",
    )
    assert mock_telephony_client.calls_dispatched == 1
    assert call_res["status"] == "QUEUED"
    assert len(mock_telephony_client.dispatched_calls) == 1
    assert mock_telephony_client.dispatched_calls[0]["to_mobile"] == "9829012345"


def test_ai_client_clean_json_text():
    # Markdown fence with json tag
    fence_json = "```json\n{\"city\": \"Jaipur\", \"price\": 5000000}\n```"
    assert AIClientService.clean_json_text(fence_json) == '{"city": "Jaipur", "price": 5000000}'

    # Markdown fence without json tag
    fence_plain = "```\n{\"bhk\": 2}\n```"
    assert AIClientService.clean_json_text(fence_plain) == '{"bhk": 2}'

    # Leading / trailing conversational text around markdown code block
    chatty = "Sure, here is the result you requested:\n```json\n{\"verified\": true}\n```\nLet me know if you need anything else!"
    cleaned = AIClientService.clean_json_text(chatty)
    assert cleaned == '{"verified": true}'

    # Plain JSON string without fences
    plain = '{"status": "ok"}'
    assert AIClientService.clean_json_text(plain) == '{"status": "ok"}'


@pytest.mark.asyncio
async def test_ai_client_fallback_when_no_api_key():
    client = AIClientService(api_key="")
    fallback = {"location": "Alwar", "bhk": 2, "budget_max": 3500000}
    res = await client.chat_completion_json(
        system_prompt="Test sys",
        user_prompt="Need flat in Alwar under 35 lakh",
        fallback_data=fallback,
    )
    assert res == fallback
    assert client.last_latency_ms >= 0.0
    assert client.last_usage["total_tokens"] > 0


def test_ai_client_token_estimation():
    client = AIClientService(api_key="")
    text = "Find 3 BHK flat in Vaishali Nagar Jaipur under 80 Lakh"
    est = client.estimate_tokens(text)
    assert est > 5
    assert est < 50


def test_prompt_registry_templates():
    assert "Jaipur" in PROPERTY_SEARCH_SYSTEM_PROMPT or "Rajasthan" in PROPERTY_SEARCH_SYSTEM_PROMPT
    assert "Hindi" in PROPERTY_SEARCH_SYSTEM_PROMPT or "Hinglish" in PROPERTY_SEARCH_SYSTEM_PROMPT

    assert "lead" in LEAD_QUALIFICATION_SYSTEM_PROMPT.lower()
    assert "support" in CUSTOMER_SUPPORT_SYSTEM_PROMPT.lower()
    assert "sales" in SALES_ASSISTANT_SYSTEM_PROMPT.lower()
    assert "document" in DOCUMENT_EXTRACTION_SYSTEM_PROMPT.lower()
    assert "whatsapp" in WHATSAPP_AGENT_SYSTEM_PROMPT.lower()
    assert "voice" in VOICE_CALLING_SYSTEM_PROMPT.lower()

    # Helper function retrieval
    prompt = get_system_prompt("property_search")
    assert prompt == PROPERTY_SEARCH_SYSTEM_PROMPT

    with pytest.raises(KeyError):
        get_system_prompt("non_existent_agent")
