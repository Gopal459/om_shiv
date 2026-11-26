import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog
from app.services.ai.agents.document_processing_agent import DocumentProcessingAgent
from app.services.ai.ocr_service import extract_text_from_file_buffer
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_extract_registry_document_from_text():
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "doc_type": "REGISTRY",
        "khasra_number": "412",
        "plot_number": "12-B",
        "colony_name": "Vaishali Nagar",
        "locality": "Vaishali Nagar",
        "city": "Jaipur",
        "plot_area": "250 Sq Yards",
        "area_unit": "Sq Yards",
        "owner_name": "Ram Lal Sharma",
        "seller_name": "Mohan Lal",
        "registry_date": "2024-03-15",
        "dlc_rate": 35000,
        "registered_value": 8750000,
        "is_missing_required_fields": False,
        "missing_fields": [],
        "red_flags": [],
    })
    agent = DocumentProcessingAgent(ai_client=mock_ai)
    sample_text = "Registry Deed: Khasra No 412, Plot No 12-B, Area 250 Sq Yards, Locality Vaishali Nagar, Owner Ram Lal Sharma, Seller Mohan Lal."
    res = await agent.extract_property_document(sample_text)
    assert res["success"] is True
    assert res["khasra_number"] == "412"
    assert res["plot_number"] == "12-B"
    assert res["owner_name"] == "Ram Lal Sharma"
    assert res["seller_name"] == "Mohan Lal"
    assert res["is_missing_required_fields"] is False


@pytest.mark.asyncio
async def test_pdf_buffer_text_extraction():
    # Test OCR / PDF text extraction pipeline
    dummy_text = b"%PDF-1.4 ... Dummy PDF Content for Khasra 550 Vaishali Nagar ..."
    text = await extract_text_from_file_buffer(dummy_text, "test.pdf")
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.asyncio
async def test_extract_from_pdf_bytes():
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "doc_type": "REGISTRY",
        "khasra_number": "789",
        "plot_number": "Plot-45",
        "colony_name": "Mansarovar",
        "city": "Jaipur",
        "plot_area": "200",
        "area_unit": "Sq Yards",
        "owner_name": "Suresh Patel",
        "seller_name": "Devi Lal",
        "is_missing_required_fields": False,
        "missing_fields": [],
        "red_flags": [],
    })
    agent = DocumentProcessingAgent(ai_client=mock_ai)
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Length 50 >>\nstream\nBT /F1 12 Tf (Khasra 789 Plot 45 Mansarovar) Tj ET\nendstream\nendobj"
    res = await agent.extract_from_pdf_bytes(pdf_bytes, "registry_deed.pdf")
    assert res["success"] is True
    assert res["khasra_number"] == "789"
    assert res["owner_name"] == "Suresh Patel"
    assert res["filename"] == "registry_deed.pdf"


@pytest.mark.asyncio
async def test_extract_from_image_bytes():
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "doc_type": "PATTA",
        "khasra_number": "101",
        "plot_number": "Patta-90A",
        "colony_name": "Jagatpura",
        "city": "Jaipur",
        "plot_area": "180",
        "area_unit": "Sq Yards",
        "owner_name": "Anita Meena",
        "is_missing_required_fields": False,
        "missing_fields": [],
        "red_flags": [],
    })
    agent = DocumentProcessingAgent(ai_client=mock_ai)
    dummy_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    res = await agent.extract_from_image_bytes(dummy_img, "patta_scan.png")
    assert res["success"] is True
    assert res["khasra_number"] == "101"
    assert res["owner_name"] == "Anita Meena"
    assert res["filename"] == "patta_scan.png"


@pytest.mark.asyncio
async def test_document_processing_guardrail_disabled(db_session: AsyncSession):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("document_processing", "DISABLED")

    mock_ai = MockAIClientService()
    agent = DocumentProcessingAgent(db=db_session, ai_client=mock_ai, guardrails=guardrails)
    res = await agent.extract_property_document("Some deed text content", doc_type="REGISTRY")

    assert res["success"] is False
    assert "disabled" in res["error"].lower()

    # Verify audit log was recorded
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "document_processing",
        AIAgentExecutionLog.status == "BLOCKED_FLAG",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None
    assert log.agent_name == "document_processing"


@pytest.mark.asyncio
async def test_document_processing_audit_log_success(db_session: AsyncSession):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("document_processing", "LIVE")

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "doc_type": "REGISTRY",
        "khasra_number": "333",
        "plot_number": "A-12",
        "owner_name": "Vikram Singh",
        "is_missing_required_fields": False,
        "missing_fields": [],
        "red_flags": [],
    })
    agent = DocumentProcessingAgent(db=db_session, ai_client=mock_ai, guardrails=guardrails)
    res = await agent.extract_property_document("Registry text for Khasra 333", doc_type="REGISTRY")
    assert res["success"] is True
    assert res["khasra_number"] == "333"

    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "document_processing",
        AIAgentExecutionLog.status == "SUCCESS",
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_document_processing_missing_fields_and_red_flags():
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "doc_type": "REGISTRY",
        "khasra_number": None,
        "plot_number": None,
        "plot_area": None,
        "owner_name": None,
        "is_missing_required_fields": True,
        "missing_fields": ["khasra_number", "plot_number", "plot_area", "owner_name"],
        "red_flags": ["Missing Sub-Registrar stamp seal", "Seller name mismatch with Jamabandi"],
    })
    agent = DocumentProcessingAgent(ai_client=mock_ai)
    res = await agent.extract_property_document("Incomplete torn registry snippet without seals.")
    assert res["success"] is True
    assert res["is_missing_required_fields"] is True
    assert "khasra_number" in res["missing_fields"]
    assert len(res["red_flags"]) >= 1


@pytest.mark.asyncio
async def test_ocr_service_file_fallbacks():
    # Corrupt or empty buffer handling
    empty_res = await extract_text_from_file_buffer(b"", "empty.pdf")
    assert isinstance(empty_res, str)

    corrupt_res = await extract_text_from_file_buffer(b"Random corrupt bytes \x00\xff\xfe", "corrupted.pdf")
    assert isinstance(corrupt_res, str)
    assert len(corrupt_res) > 0

    image_res = await extract_text_from_file_buffer(b"\xff\xd8\xff\xe0...jpeg dummy", "scan.jpg")
    assert isinstance(image_res, str)
    assert len(image_res) > 0
