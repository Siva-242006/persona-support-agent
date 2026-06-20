"""Escalation policy and structured human handoff creation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from src.classifier import PersonaResult
from src.config import LOW_CONFIDENCE_THRESHOLD


@dataclass(frozen=True)
class EscalationResult:
    """Decision object returned after evaluating escalation rules."""

    escalated: bool
    escalation_reasons: list[str]
    recommended_action: str

    @property
    def escalation_reason(self) -> str:
        return ", ".join(self.escalation_reasons)


BILLING_TERMS = (
    "billing",
    "bill",
    "charge",
    "charged",
    "invoice",
    "payment",
    "subscription",
    "duplicate charge",
)

REFUND_TERMS = (
    "refund",
    "money back",
    "reimbursement",
    "compensate",
    "compensation",
)

LEGAL_TERMS = (
    "legal",
    "lawsuit",
    "lawyer",
    "attorney",
    "court",
    "compliance",
    "sue",
)

ACCOUNT_MODIFICATION_TERMS = (
    "delete account",
    "close account",
    "transfer ownership",
    "change owner",
    "account merge",
    "merge account",
    "change email",
    "change account access",
    "remove user",
    "add admin",
)


def detect_escalation(
    user_message: str,
    retrieval_confidence: float,
    persona: str,
    persona_history: list[str],
) -> EscalationResult:
    """Evaluate confidence, sensitive topics, and repeated frustration."""
    normalized = user_message.lower()
    reasons: list[str] = []

    if retrieval_confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append("Low Confidence")
    if _contains_any(normalized, BILLING_TERMS):
        reasons.append("Billing Issue")
    if _contains_any(normalized, REFUND_TERMS):
        reasons.append("Refund Request")
    if _contains_any(normalized, LEGAL_TERMS):
        reasons.append("Legal Concern")
    if _contains_any(normalized, ACCOUNT_MODIFICATION_TERMS):
        reasons.append("Account Modification Request")
    if _is_repeated_frustration(persona, persona_history):
        reasons.append("Repeated Frustration")

    return EscalationResult(
        escalated=bool(reasons),
        escalation_reasons=reasons,
        recommended_action=_recommended_action(reasons),
    )


def generate_handoff_json(
    user_message: str,
    persona_result: PersonaResult,
    retrieval_confidence: float,
    escalation_result: EscalationResult,
    retrieved_sources: list[str],
) -> dict[str, object]:
    """Create the structured payload a human support agent can act on."""
    now = datetime.now()
    return {
        "ticket_id": now.strftime("TICKET-%Y%m%d-%H%M%S"),
        "persona": persona_result.persona,
        "persona_confidence": persona_result.confidence,
        "retrieval_confidence": retrieval_confidence,
        "escalation_reasons": escalation_result.escalation_reasons,
        "customer_message": user_message,
        "issue_summary": _issue_summary(user_message, escalation_result.escalation_reasons),
        "conversation_summary": (
            f"The user is classified as {persona_result.persona}. "
            f"Escalation was triggered for: {escalation_result.escalation_reason}."
        ),
        "retrieved_sources": retrieved_sources,
        "recommended_human_action": escalation_result.recommended_action,
    }


def _contains_any(message: str, terms: tuple[str, ...]) -> bool:
    """Match phrase terms directly and single-word terms on word boundaries."""
    for term in terms:
        if " " in term and term in message:
            return True
        if " " not in term and re.search(rf"\b{re.escape(term)}\b", message):
            return True
    return False


def _is_repeated_frustration(persona: str, persona_history: list[str]) -> bool:
    """Escalate when the last three detected turns are all frustrated."""
    if persona != "Frustrated User":
        return False
    recent = (persona_history + [persona])[-3:]
    return len(recent) == 3 and all(item == "Frustrated User" for item in recent)


def _recommended_action(reasons: list[str]) -> str:
    """Map escalation reasons to the most appropriate support queue."""
    if not reasons:
        return "No human escalation required."
    if "Legal Concern" in reasons:
        return "Route to legal or compliance support for manual review."
    if "Refund Request" in reasons or "Billing Issue" in reasons:
        return "Route to billing support for manual review."
    if "Account Modification Request" in reasons:
        return "Route to account support for identity and permission verification."
    if "Repeated Frustration" in reasons:
        return "Route to a human support specialist for immediate assistance."
    return "Route to human support for manual review."


def _issue_summary(user_message: str, reasons: list[str]) -> str:
    """Summarize the customer issue while keeping the handoff compact."""
    reason_text = ", ".join(reasons) if reasons else "No escalation"
    compact_message = " ".join(user_message.split())
    if len(compact_message) > 180:
        compact_message = compact_message[:177] + "..."
    return f"Customer message matched escalation reason(s): {reason_text}. Message: {compact_message}"
