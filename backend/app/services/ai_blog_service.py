import json
import re
import logging
from typing import Optional, Dict, Any, List
import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.blog_schemas import AIBlogGenerateRequest, AIBlogGenerateResponse, generate_slug

logger = logging.getLogger(__name__)


class AIBlogGeneratorService:
    @staticmethod
    def _clean_json_text(text: str) -> str:
        """Strips markdown code fences if LLM wrapped JSON in ```json ... ```."""
        cleaned = text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    @staticmethod
    def _generate_fallback_blog(topic: str, tone: str, audience: str, model_name: str) -> AIBlogGenerateResponse:
        """High-quality fallback generator when OPENAI_API_KEY is not yet configured."""
        clean_topic = topic.strip().capitalize()
        title = f"{clean_topic}: Complete Real Estate Market Analysis & Investment Guide"
        slug = generate_slug(title)

        content_html = f"""<h2>Overview of {clean_topic}</h2>
<p>In recent years, the real estate landscape across Rajasthan and the National Capital Region (NCR) has experienced remarkable development. <strong>{clean_topic}</strong> has emerged as a focal point for forward-thinking property buyers, investors, and developers seeking consistent capital appreciation and rental yield.</p>

<h3>Key Drivers Behind Market Growth</h3>
<p>Several catalytic factors contribute to the strategic importance of this sector:</p>
<ul>
  <li><strong>Infrastructure & Expressways:</strong> Seamless highway connectivity, dedicated freight corridors, and proximity to major commercial nodes have drastically cut transit times.</li>
  <li><strong>Industrial & Commercial Expansion:</strong> Growth in RIICO industrial zones, logistics hubs, and manufacturing parks generates sustained housing demand.</li>
  <li><strong>Affordable Entry Valuations:</strong> Compared to saturated tier-1 metros, land and gated township plots offer significantly higher appreciation potential over a 3-5 year horizon.</li>
</ul>

<blockquote>"Investing in emerging corridors before major infrastructure milestones are fully commissioned delivers the highest alpha for long-term real estate portfolios."</blockquote>

<h3>Investment Recommendations & Best Practices</h3>
<p>When evaluating listings or residential plots related to {clean_topic.lower()}, buyers should prioritize:</p>
<ol>
  <li><strong>Title Verification:</strong> Always verify registry records, conversion status (e.g., 90A approvals), and master plan land-use zoning.</li>
  <li><strong>Developer Track Record:</strong> Partner with established builders possessing a proven delivery history in the Alwar, Bhiwadi, and Jaipur belt.</li>
  <li><strong>Basic Amenities:</strong> Confirm proximity to electricity grids, water lines, and wide arterial access roads.</li>
</ol>

<h2>Conclusion</h2>
<p>Whether you are a first-time homebuyer or an institutional investor, {clean_topic.lower()} represents an extraordinary growth avenue. Contact our Propira Omshiv advisory desk for verified site visits and personalized inventory matching.</p>"""

        short_desc = f"An in-depth market outlook on {clean_topic.lower()}, examining upcoming infrastructure catalysts, price trends, and investment opportunities for {audience.lower()}."
        meta_title = f"{clean_topic[:40]} Guide | Propira"
        meta_keyword = f"{clean_topic.lower()}, real estate investment, property in alwar, rajasthan plots, ncr growth"
        meta_desc = f"Explore complete property market insights, capital appreciation trends, and verified investment opportunities for {clean_topic.lower()}."

        return AIBlogGenerateResponse(
            blog_title=title,
            slug=slug,
            short_description=short_desc,
            description=content_html,
            meta_title=meta_title[:60],
            meta_keyword=meta_keyword,
            meta_description=meta_desc[:160],
            suggested_tags=["Market Insights", "Investment Guide", "Infrastructure", "Alwar NCR"],
            suggested_category="Market Insights & Trends",
            model_used=f"{model_name} (Simulation/Fallback - add OPENAI_API_KEY for live LLM)",
            tokens_used=650,
        )

    @classmethod
    async def generate_blog(cls, req: AIBlogGenerateRequest) -> AIBlogGenerateResponse:
        """Calls OpenAI Chat Completion API with structured output instructions."""
        api_key = req.api_key or settings.OPENAI_API_KEY
        model_name = req.model or settings.OPENAI_MODEL or "gpt-4o"
        base_url = settings.OPENAI_BASE_URL.rstrip("/")

        # If no API key is configured, provide graceful realistic fallback
        if not api_key or not api_key.strip():
            logger.info("OPENAI_API_KEY not set. Using AI Generator simulation fallback.")
            return cls._generate_fallback_blog(
                topic=req.topic,
                tone=req.tone or "Professional",
                audience=req.target_audience or "Investors",
                model_name=model_name,
            )

        system_prompt = (
            "You are an elite Real Estate Editorial Director & SEO Strategist for Propira Omshiv Real Estate, "
            "the premier property consultancy in Rajasthan, Alwar, Bhiwadi, Neemrana, NCR, and Jaipur corridors.\n"
            "Your task is to generate a comprehensive, highly persuasive, search-optimized real estate blog article based on the given topic.\n\n"
            "You MUST respond ONLY with a valid JSON object conforming to this exact schema:\n"
            "{\n"
            '  "blog_title": "Catchy, professional headline (max 90 chars)",\n'
            '  "slug": "clean-kebab-case-url-slug",\n'
            '  "short_description": "2-3 sentence compelling excerpt summarizing key takeaways",\n'
            '  "description": "Comprehensive full article content written in clean, modern HTML with <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <hr>. Do not include <html> or <body> tags.",\n'
            '  "meta_title": "SEO title under 60 chars",\n'
            '  "meta_keyword": "5-8 comma-separated high-volume search keywords",\n'
            '  "meta_description": "Compelling meta description under 160 chars",\n'
            '  "suggested_tags": ["Tag1", "Tag2", "Tag3"],\n'
            '  "suggested_category": "Market Insights & Trends"\n'
            "}"
        )

        user_content = (
            f"Topic: {req.topic}\n"
            f"Editorial Tone: {req.tone or 'Professional Real Estate Analysis'}\n"
            f"Target Audience: {req.target_audience or 'Property Buyers & NRI Investors'}\n"
            f"Additional Instructions: {req.custom_instructions or 'Highlight market infrastructure, connectivity, and investment yield.'}"
        )

        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)

            if res.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OpenAI API Key provided. Please verify OPENAI_API_KEY in your .env file.",
                )
            if res.status_code != 200:
                logger.error(f"OpenAI API error {res.status_code}: {res.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"OpenAI API error ({res.status_code}): {res.text[:200]}",
                )

            data = res.json()
            raw_content = data["choices"][0]["message"]["content"]
            cleaned_json = cls._clean_json_text(raw_content)
            parsed = json.loads(cleaned_json)

            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            return AIBlogGenerateResponse(
                blog_title=parsed.get("blog_title") or f"{req.topic} Insights",
                slug=parsed.get("slug") or generate_slug(parsed.get("blog_title", req.topic)),
                short_description=parsed.get("short_description") or "",
                description=parsed.get("description") or "",
                meta_title=(parsed.get("meta_title") or "")[:60],
                meta_keyword=parsed.get("meta_keyword") or "",
                meta_description=(parsed.get("meta_description") or "")[:160],
                suggested_tags=parsed.get("suggested_tags") or ["Real Estate", "Investment"],
                suggested_category=parsed.get("suggested_category") or "Market Insights & Trends",
                model_used=model_name,
                tokens_used=tokens_used,
            )

        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse OpenAI JSON output: {jde}")
            return cls._generate_fallback_blog(req.topic, req.tone or "", req.target_audience or "", model_name)
        except httpx.RequestError as req_err:
            logger.error(f"Network error communicating with OpenAI: {req_err}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Network error connecting to OpenAI endpoint: {req_err}",
            )
