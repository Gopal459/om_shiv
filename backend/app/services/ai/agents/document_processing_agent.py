from __future__ import annotations
import json
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.llm_client import AIClientService
from app.services.ai.ocr_service import extract_text_from_file_buffer
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.prompts import DOCUMENT_EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class DocumentProcessingAgent:
    """Agent 6: AI Document Processing Agent (OCR & Scanned PDF Pipeline).
    
    Parses complex Indian legal and title documents (Registry Deeds, Pattas,
    JDA Allotment Letters, 90A approvals, Jamabandi / Fard records) from
    scanned PDF buffers or image files.
    
    Extracts structured real estate metadata:
    - Khasra number, plot number, colony/scheme, locality, city
    - Plot area and area measurement unit (Sq Yards, Sq Feet, Bigha)
    - Owner/Buyer and Seller names
    - Registration date, DLC / circle rates, and registered transaction value
    - Verification flags: missing mandatory fields and red flags / title ambiguities
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        ai_client: Optional[AIClientService] = None,
        guardrails: Optional[SafetyGuardrailsService] = None,
    ):
        self.db = db
        self.ai_client = ai_client or AIClientService()
        self.guardrails = guardrails or (SafetyGuardrailsService(db) if db is not None else None)
        self.agent_name = "document_processing"

    async def extract_from_pdf_bytes(
        self,
        file_bytes: bytes,
        filename: str = "document.pdf",
    ) -> Dict[str, Any]:
        """Extracts structured real estate title data from PDF byte buffer."""
        text_content = await extract_text_from_file_buffer(file_bytes, filename)
        result = await self.extract_property_document(text_content, doc_type="REGISTRY")
        result["filename"] = filename
        result["file_type"] = "PDF"
        result["file_size_bytes"] = len(file_bytes) if file_bytes else 0
        return result

    async def extract_from_image_bytes(
        self,
        file_bytes: bytes,
        filename: str = "document.png",
    ) -> Dict[str, Any]:
        """Extracts structured real estate title data from Image byte buffer."""
        text_content = await extract_text_from_file_buffer(file_bytes, filename)
        doc_type = "PATTA" if "patta" in filename.lower() else "REGISTRY"
        result = await self.extract_property_document(text_content, doc_type=doc_type)
        result["filename"] = filename
        result["file_type"] = "IMAGE"
        result["file_size_bytes"] = len(file_bytes) if file_bytes else 0
        return result

    async def extract_property_document(
        self,
        text_content: str,
        doc_type: str = "REGISTRY",
    ) -> Dict[str, Any]:
        """Parses extracted OCR text into verified structured real estate document metadata.
        
        1. Checks feature flag ('document_processing').
        2. Calls AIClientService with DOCUMENT_EXTRACTION_SYSTEM_PROMPT.
        3. Normalizes and validates extracted attributes.
        4. Detects missing mandatory fields and title risk red flags.
        5. Records execution audit log.
        """
        # 1. Feature Flag Verification
        mode = "SHADOW"
        if self.guardrails:
            mode = await self.guardrails.get_agent_mode(self.agent_name)

        if mode == "DISABLED":
            if self.guardrails and self.guardrails.db is not None:
                await self.guardrails.record_execution_log(
                    agent_name=self.agent_name,
                    channel="DOCUMENT",
                    mode=mode,
                    trigger_event="EXTRACT_DOCUMENT",
                    input_summary=text_content[:300] if text_content else None,
                    output_response="Document processing agent is disabled by configuration.",
                    status="BLOCKED_FLAG",
                    error_message="Agent mode is configured to DISABLED",
                )
            return {
                "success": False,
                "error": "Document processing agent is disabled by configuration.",
                "doc_type": doc_type,
                "khasra_number": None,
                "plot_number": None,
                "colony_name": None,
                "locality": None,
                "city": None,
                "plot_area": None,
                "area_unit": None,
                "owner_name": None,
                "seller_name": None,
                "registry_date": None,
                "dlc_rate": None,
                "registered_value": None,
                "is_missing_required_fields": True,
                "missing_fields": [],
                "red_flags": ["AGENT_DISABLED"],
            }

        # 2. Invoke LLM with DOCUMENT_EXTRACTION_SYSTEM_PROMPT
        user_prompt = (
            f"Expected Document Type: {doc_type}\n\n"
            f"OCR Extracted Document Text:\n\"\"\"\n{text_content}\n\"\"\"\n\n"
            f"Extract all property title metadata into structured JSON."
        )

        llm_data = await self.ai_client.chat_completion_json(
            system_prompt=DOCUMENT_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # 3. Extract and normalize fields
        prop_details = llm_data.get("property_details") or {}
        seller_details = llm_data.get("seller_details") or {}
        buyer_details = llm_data.get("buyer_details") or {}
        financials = llm_data.get("financials") or {}

        resolved_doc_type = (
            llm_data.get("doc_type")
            or llm_data.get("document_type")
            or doc_type
        )
        khasra_number = (
            llm_data.get("khasra_number")
            or prop_details.get("khasra_no")
        )
        plot_number = (
            llm_data.get("plot_number")
            or prop_details.get("plot_no")
        )
        colony_name = (
            llm_data.get("colony_name")
            or prop_details.get("colony_scheme")
        )
        locality = (
            llm_data.get("locality")
            or colony_name
            or prop_details.get("tehsil")
        )
        city = (
            llm_data.get("city")
            or prop_details.get("district")
        )

        # Plot area resolution
        plot_area_raw = (
            llm_data.get("plot_area")
            or prop_details.get("area_sq_yards")
            or prop_details.get("area_sq_feet")
        )
        plot_area = str(plot_area_raw) if plot_area_raw is not None else None

        area_unit = (
            llm_data.get("area_unit")
            or ("Sq Yards" if prop_details.get("area_sq_yards") else ("Sq Feet" if prop_details.get("area_sq_feet") else "Sq Yards"))
        )

        owner_name = (
            llm_data.get("owner_name")
            or buyer_details.get("name")
        )
        seller_name = (
            llm_data.get("seller_name")
            or seller_details.get("name")
        )
        registry_date = (
            llm_data.get("registry_date")
            or llm_data.get("registration_date")
        )
        dlc_rate = (
            llm_data.get("dlc_rate")
            or financials.get("dlc_rate_valuation")
        )
        registered_value = (
            llm_data.get("registered_value")
            or financials.get("consideration_amount")
        )

        # Red flags
        red_flags: List[str] = list(llm_data.get("red_flags") or [])

        # Missing required fields calculation
        if "missing_fields" in llm_data and isinstance(llm_data["missing_fields"], list):
            missing_fields = list(llm_data["missing_fields"])
        else:
            missing_fields = []
            if not khasra_number:
                missing_fields.append("khasra_number")
            if not plot_number:
                missing_fields.append("plot_number")
            if not plot_area:
                missing_fields.append("plot_area")
            if not owner_name:
                missing_fields.append("owner_name")

        if "is_missing_required_fields" in llm_data and isinstance(llm_data["is_missing_required_fields"], bool):
            is_missing_required = llm_data["is_missing_required_fields"]
        else:
            is_missing_required = len(missing_fields) > 0

        # 4. Audit Log
        if self.guardrails and self.guardrails.db is not None:
            summary_info = f"DocType: {resolved_doc_type}, Khasra: {khasra_number}, Owner: {owner_name}"
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                channel="DOCUMENT",
                mode=mode,
                trigger_event="EXTRACT_DOCUMENT",
                input_summary=text_content[:300] if text_content else None,
                output_response=summary_info,
                tools_called={
                    "doc_type": resolved_doc_type,
                    "khasra_number": khasra_number,
                    "is_missing": is_missing_required,
                },
                status="SUCCESS",
            )

        return {
            "success": True,
            "doc_type": resolved_doc_type,
            "khasra_number": khasra_number,
            "plot_number": plot_number,
            "colony_name": colony_name,
            "locality": locality,
            "city": city,
            "plot_area": plot_area,
            "area_unit": area_unit,
            "owner_name": owner_name,
            "seller_name": seller_name,
            "registry_date": registry_date,
            "dlc_rate": dlc_rate,
            "registered_value": registered_value,
            "is_missing_required_fields": is_missing_required,
            "missing_fields": missing_fields,
            "red_flags": red_flags,
            "raw_extraction": llm_data,
        }
