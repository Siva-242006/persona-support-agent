"""Generate grounded support answers from retrieved knowledge base chunks."""

from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types

from src.config import (
    GENERATION_TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    RESPONSE_MODEL_FALLBACKS,
    require_gemini_api_key,
)
from src.rag_pipeline import RetrievedChunk, unique_sources
from src.retry import call_with_backoff


@dataclass(frozen=True)
class ResponseResult:
    """Customer-facing answer with the metadata needed by the UI."""

    answer: str
    persona: str
    sources: list[str]
    retrieval_confidence: float
    escalated: bool


def generate_response(
    user_message: str,
    persona: str,
    retrieved_chunks: list[RetrievedChunk],
    retrieval_confidence: float,
    escalation_status: bool,
    client: genai.Client | None = None,
) -> ResponseResult:
    """Generate a persona-aware answer using only retrieved context."""
    sources = unique_sources(retrieved_chunks)
    if not retrieved_chunks:
        return ResponseResult(
            answer="This request needs human support review because no knowledge base context was retrieved.",
            persona=persona,
            sources=sources,
            retrieval_confidence=retrieval_confidence,
            escalated=escalation_status,
        )

    active_client = client or genai.Client(api_key=require_gemini_api_key())
    prompt = _response_prompt(user_message, persona, retrieved_chunks, sources, escalation_status)
    response = None
    errors: list[str] = []
    for model_name in RESPONSE_MODEL_FALLBACKS:
        try:
            response = call_with_backoff(
                lambda: active_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                        temperature=GENERATION_TEMPERATURE,
                    ),
                )
            )
            break
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")
    if response is None:
        raise RuntimeError("Gemini response generation failed for configured models. Attempts: " + " | ".join(errors))
    answer = (getattr(response, "text", "") or "").strip()
    if not answer:
        answer = "I could not generate a grounded answer from the retrieved context."
    return ResponseResult(
        answer=answer,
        persona=persona,
        sources=sources,
        retrieval_confidence=retrieval_confidence,
        escalated=escalation_status,
    )


def _response_prompt(
    user_message: str,
    persona: str,
    retrieved_chunks: list[RetrievedChunk],
    sources: list[str],
    escalation_status: bool,
) -> str:
    """Assemble the grounded prompt sent to Gemini for answer generation."""
    context = "\n\n".join(
        f"Source: {chunk.source}\nContent:\n{chunk.text}" for chunk in retrieved_chunks
    )
    return f"""
You are the Persona-Aware Customer Support Agent.

Use only the retrieved context below. Do not guess. Do not invent policy. If the context does not support a detail, say that the available support documents do not state it. Keep the answer concise for support testing while still satisfying the persona rules.

Detected persona: {persona}
Escalation status: {escalation_status}

Persona response rules:
{_persona_rules(persona)}

Customer message:
{user_message}

Retrieved context:
{context}

Required source attribution:
Sources:
{_format_sources_for_prompt(sources)}

Write the customer-facing answer in a chat-friendly format. Include source attribution at the end using exactly the source file names above.
""".strip()


def _persona_rules(persona: str) -> str:
    """Return response-shaping instructions for the selected persona."""
    if persona == "Technical Expert":
        return (
            "- Be precise.\n"
            "- Use technical structure.\n"
            "- Include root-cause reasoning when supported by sources.\n"
            "- Include configuration or troubleshooting steps when supported by sources.\n"
            "- Avoid oversimplified wording."
        )
    if persona == "Business Executive":
        return (
            "- Be concise.\n"
            "- Focus on impact.\n"
            "- Mention resolution direction when supported by sources.\n"
            "- Avoid unnecessary technical detail.\n"
            "- Use professional language."
        )
    return (
        "- Start with empathy.\n"
        "- Acknowledge inconvenience.\n"
        "- Use simple instructions.\n"
        "- Avoid unnecessary technical jargon.\n"
        "- Provide clear next steps.\n"
        "- Do not blame the user."
    )


def _format_sources_for_prompt(sources: list[str]) -> str:
    """Format source names so the model can cite only retrieved files."""
    if not sources:
        return "- No retrieved source"
    return "\n".join(f"- {source}" for source in sources)
