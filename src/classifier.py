"""Classify customer messages into supported response personas."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from google import genai
from google.genai import types

from src.config import (
    ALLOWED_PERSONAS,
    CLASSIFICATION_MAX_OUTPUT_TOKENS,
    CLASSIFICATION_TEMPERATURE,
    PERSONA_MODEL_FALLBACKS,
    require_gemini_api_key,
)
from src.retry import call_with_backoff


@dataclass(frozen=True)
class PersonaResult:
    """Normalized persona classification returned by the LLM."""

    persona: str
    confidence: float
    reasoning: str
    interaction_type: str = "support_request"
    assistant_reply: str = ""


def classify_persona(user_message: str, client: genai.Client | None = None) -> PersonaResult:
    """Classify a customer message with Gemini and validate the JSON result."""
    active_client = client or genai.Client(api_key=require_gemini_api_key())
    prompt = _classification_prompt(user_message)
    errors: list[str] = []
    for model_name in PERSONA_MODEL_FALLBACKS:
        try:
            response = call_with_backoff(
                lambda: active_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=CLASSIFICATION_MAX_OUTPUT_TOKENS,
                        temperature=CLASSIFICATION_TEMPERATURE,
                    ),
                )
            )
            text = getattr(response, "text", "") or ""
            return validate_persona_output(text)
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")
    raise RuntimeError("Gemini persona classification failed for configured models. Attempts: " + " | ".join(errors))


def validate_persona_output(raw_text: str) -> PersonaResult:
    """Parse and constrain model output to the application's supported schema."""
    try:
        parsed = json.loads(_extract_json(raw_text))
        persona = str(parsed.get("persona", "")).strip()
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = str(parsed.get("reasoning", "")).strip()
        interaction_type = str(parsed.get("interaction_type", "support_request")).strip()
        assistant_reply = str(parsed.get("assistant_reply", "")).strip()
        if persona not in ALLOWED_PERSONAS:
            raise ValueError("Persona outside allowed list.")
        if interaction_type not in {"greeting", "clarification_needed", "support_request", "sensitive_request"}:
            interaction_type = "support_request"
        return PersonaResult(
            persona=persona,
            confidence=max(0.0, min(1.0, confidence)),
            reasoning=reasoning or "Gemini selected the closest supported persona.",
            interaction_type=interaction_type,
            assistant_reply=assistant_reply,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return PersonaResult(
            persona="Frustrated User",
            confidence=0.0,
            reasoning="Gemini returned invalid classification JSON; routed conservatively.",
            interaction_type="support_request",
        )


def _extract_json(raw_text: str) -> str:
    """Extract a JSON object even if the model wraps it in Markdown fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if match:
            return match.group(1)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return match.group(0) if match else text


def _classification_prompt(user_message: str) -> str:
    """Build the compact classifier prompt used before retrieval."""
    personas = ", ".join(ALLOWED_PERSONAS)
    return f"""
Understand the customer message and classify it for a persona-aware support assistant.

Allowed personas:
- Technical Expert: API terminology, auth terms, error codes, logs, configuration, integration details.
- Frustrated User: anger, urgency, complaint, emotional wording, repeated failures, dissatisfaction.
- Business Executive: operational impact, revenue impact, customer impact, SLA, timeline, business risk.

Allowed interaction_type values:
- greeting: simple greeting or small talk without a support issue.
- clarification_needed: user indicates a problem but gives too little detail to retrieve support knowledge safely.
- support_request: concrete support question that should use RAG before answering.
- sensitive_request: billing, refund, legal, account modification, or other request likely needing escalation.

Return compact valid JSON only using this schema:
{{
  "interaction_type": "support_request",
  "persona": "Technical Expert",
  "confidence": 0.91,
  "reasoning": "The message uses API and authentication terminology.",
  "assistant_reply": ""
}}

The persona value must be exactly one of: {personas}.
For greeting, set assistant_reply to a brief friendly reply asking how to help with API issues, password reset, billing, refunds, or account access.
For clarification_needed, set assistant_reply to one concise clarifying question. Do not invent an answer.
For support_request or sensitive_request, assistant_reply must be an empty string.
Do not return markdown.

Customer message:
{user_message}
""".strip()
