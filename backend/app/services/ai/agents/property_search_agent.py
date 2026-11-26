from __future__ import annotations
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.llm_client import AIClientService
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.tools import AIToolRegistry
from app.services.ai.prompts import PROPERTY_SEARCH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _format_price_indian(amount: Optional[float]) -> str:
    """Formats numeric price into conversational Indian denominations (Lakh / Crore)."""
    if amount is None or amount <= 0:
        return "Price on Request"
    if amount >= 10_000_000:
        cr = amount / 10_000_000
        formatted = f"{cr:.2f}".rstrip("0").rstrip(".")
        return f"₹{formatted} Cr"
    if amount >= 100_000:
        lakh = amount / 100_000
        formatted = f"{lakh:.2f}".rstrip("0").rstrip(".")
        return f"₹{formatted} Lakh"
    return f"₹{int(amount):,}"


class PropertySearchAgent:
    """Agent 1: Conversational AI Property Search Agent.
    
    Translates natural language buyer inquiries (in English, Hindi, or Hinglish) into structured
    database filters, executes real-time catalog queries on verified, live listings, applies safety
    guardrails/feature flags, formats natural language citations, and logs audit execution records.
    """

    def __init__(
        self,
        db: AsyncSession,
        ai_client: Optional[AIClientService] = None,
        guardrails: Optional[SafetyGuardrailsService] = None,
        tools: Optional[AIToolRegistry] = None,
    ):
        self.db = db
        self.ai_client = ai_client or AIClientService()
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.tools = tools or AIToolRegistry(db)
        self.agent_name = "property_search"

    def _build_response_text(
        self,
        properties: List[Dict[str, Any]],
        filters: Dict[str, Any],
        language: str = "en",
    ) -> str:
        """Constructs conversational response in English or Hindi citing found properties."""
        is_hindi = language.lower() in ("hi", "hindi")
        count = len(properties)

        city = filters.get("city") or "Rajasthan / NCR"
        locality = filters.get("locality")
        loc_str = f", {locality}" if locality else ""
        bhk_val = filters.get("bhk")
        bhk_str = f" {bhk_val} BHK" if bhk_val else ""

        if count == 0:
            if is_hindi:
                return (
                    f"नमस्ते! हमें आपके मापदंडों ({city}{loc_str}{bhk_str}) के अनुसार फिलहाल कोई लाइव प्रॉपर्टी नहीं मिली। "
                    "कृपया अपना बजट या पसंदीदा क्षेत्र बदलकर पुनः प्रयास करें या हमारे प्रॉपर्टी सलाहकार से संपर्क करें।"
                )
            return (
                f"Hello! We currently could not find any live listings matching your criteria ({city}{loc_str}{bhk_str}). "
                "Please try adjusting your budget or locality, or connect with our property advisor for off-market options."
            )

        citations = []
        for idx, p in enumerate(properties[:5], start=1):
            price_str = _format_price_indian(p.get("expected_price"))
            title = p.get("title") or "Residential Property"
            pid = p.get("property_id") or ""
            p_loc = p.get("locality") or p.get("city") or ""
            citations.append(f"{idx}. {title} [{pid}] - {p_loc} ({price_str})")

        listing_bullets = "\n".join(citations)

        if is_hindi:
            return (
                f"नमस्ते! हमें {city}{loc_str} में आपकी खोज के अनुसार {count} प्रॉपर्टी मिली हैं:\n\n"
                f"{listing_bullets}\n\n"
                "क्या आप इनमें से किसी प्रॉपर्टी का विवरण देखना चाहते हैं या साइट विजिट बुक करना चाहते हैं?"
            )

        return (
            f"Hello! We found {count} matching properties in {city}{loc_str}:\n\n"
            f"{listing_bullets}\n\n"
            "Would you like more details or to schedule a site visit for any of these options?"
        )

    async def search_properties_conversational(
        self,
        query: str,
        session_context: Optional[Dict[str, Any]] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Executes conversational property search pipeline:
        
        1. Feature Flag & Safety Guardrail Check.
        2. Query Intent Parsing into structured search filters via AIClientService.
        3. Real-time DB catalog querying via AIToolRegistry.
        4. Response formatting in customer's preferred language.
        5. Execution audit logging.
        """
        session_context = session_context or {}
        lead_id = session_context.get("lead_id")
        channel = session_context.get("channel", "WEB")

        # 1. Feature Flag Verification
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="CONVERSATIONAL_SEARCH",
                input_summary=query,
                output_response="Property search agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "success": False,
                "error": "Property search agent is disabled by configuration.",
                "query": query,
                "parsed_filters": {},
                "properties": [],
                "response_text": "Property search assistant is currently unavailable.",
                "total_found": 0,
            }

        try:
            # 2. Parse query using structured LLM output
            user_prompt = f"Customer Query: {query}\nTarget Language: {language}"
            if session_context:
                context_hints = {k: v for k, v in session_context.items() if k not in ("lead_id", "channel")}
                if context_hints:
                    user_prompt += f"\nSession Context: {context_hints}"

            parsed = await self.ai_client.chat_completion_json(
                system_prompt=PROPERTY_SEARCH_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                fallback_data={
                    "city": None,
                    "locality": None,
                    "bhk": None,
                    "property_type": None,
                    "min_price": None,
                    "max_price": None,
                },
            )

            # Map parsed fields to search filters
            filters: Dict[str, Any] = {}
            if parsed.get("city"):
                filters["city"] = str(parsed["city"]).strip()
            if parsed.get("locality"):
                filters["locality"] = str(parsed["locality"]).strip()
            if parsed.get("bhk") is not None:
                try:
                    filters["bhk"] = int(parsed["bhk"])
                except (ValueError, TypeError):
                    pass
            if parsed.get("min_price") is not None:
                try:
                    filters["min_price"] = float(parsed["min_price"])
                except (ValueError, TypeError):
                    pass
            if parsed.get("max_price") is not None:
                try:
                    filters["max_price"] = float(parsed["max_price"])
                except (ValueError, TypeError):
                    pass
            if parsed.get("category_code") is not None:
                try:
                    filters["category_code"] = int(parsed["category_code"])
                except (ValueError, TypeError):
                    pass
            elif parsed.get("property_type"):
                pt = str(parsed["property_type"]).upper()
                if pt in ("FLAT", "VILLA", "HOUSE", "RESIDENTIAL"):
                    filters["category_code"] = 1
                elif pt in ("COMMERCIAL", "SHOP", "OFFICE"):
                    filters["category_code"] = 2
                elif pt in ("AGRICULTURAL", "FARMHOUSE", "LAND"):
                    filters["category_code"] = 3
                elif pt in ("INDUSTRIAL", "RIICO"):
                    filters["category_code"] = 4

            if parsed.get("sub_category_code") is not None:
                try:
                    filters["sub_category_code"] = int(parsed["sub_category_code"])
                except (ValueError, TypeError):
                    pass
            if parsed.get("listing_type") is not None:
                try:
                    filters["listing_type"] = int(parsed["listing_type"])
                except (ValueError, TypeError):
                    pass

            # 3. Query DB via tools
            properties = await self.tools.search_properties(filters=filters, db=self.db)

            # 4. Format conversational response
            response_text = self._build_response_text(
                properties=properties,
                filters=filters,
                language=language,
            )

            # 5. Record Execution Log
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="CONVERSATIONAL_SEARCH",
                input_summary=query,
                output_response=response_text,
                tools_called=[{
                    "tool": "search_properties",
                    "filters": filters,
                    "results_count": len(properties),
                }],
                status="SUCCESS",
            )

            return {
                "success": True,
                "query": query,
                "parsed_filters": filters,
                "properties": properties,
                "response_text": response_text,
                "total_found": len(properties),
            }

        except Exception as exc:
            logger.exception("Error executing conversational property search: %s", exc)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="CONVERSATIONAL_SEARCH",
                input_summary=query,
                output_response=None,
                status="ERROR",
                error_message=str(exc),
            )
            return {
                "success": False,
                "error": str(exc),
                "query": query,
                "parsed_filters": {},
                "properties": [],
                "response_text": "An error occurred while processing your property search. Please try again.",
                "total_found": 0,
            }

    # Compatibility alias for callers using search_properties
    search_properties = search_properties_conversational
