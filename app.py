"""Streamlit chat interface for the persona-aware support workflow."""

from __future__ import annotations

import json

import streamlit as st

from src.classifier import classify_persona
from src.escalator import detect_escalation, generate_handoff_json
from src.generator import generate_response
from src.rag_pipeline import index_documents, retrieve, unique_sources


PAGE_TITLE = "Persona-Aware Customer Support Agent"


def main() -> None:
    """Render the chat app and process new user messages."""
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    _apply_page_styles()
    st.title(PAGE_TITLE)
    st.caption("Persona-adaptive support using Gemini, RAG, ChromaDB, and human escalation.")

    _initialize_session_state()
    _render_chat()

    user_message = st.chat_input("Ask a support question")
    if user_message and user_message.strip():
        _handle_message_with_status(user_message.strip())
        st.rerun()


def _initialize_session_state() -> None:
    """Initialize state that must survive Streamlit script reruns."""
    if "persona_history" not in st.session_state:
        st.session_state.persona_history = []
    if "latest_result" not in st.session_state:
        st.session_state.latest_result = None
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "kb_indexed" not in st.session_state:
        st.session_state.kb_indexed = False


def _handle_message_with_status(user_message: str) -> None:
    """Display the user turn immediately and show progress while processing."""
    st.session_state.chat_messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.write(user_message)
    with st.chat_message("assistant"):
        with st.status("Analyzing and retrieving support context...", expanded=False):
            _handle_message(user_message)


def _handle_message(user_message: str) -> None:
    """Run one customer message through classification, retrieval, and response logic."""
    try:
        # Chroma is persistent; this call only inserts chunks that are not indexed yet.
        if not st.session_state.kb_indexed:
            index_documents()
            st.session_state.kb_indexed = True

        persona_result = classify_persona(user_message)

        # Greetings stay conversational and do not require support metadata.
        if persona_result.interaction_type == "greeting":
            answer = persona_result.assistant_reply or (
                "Hi! How can I help you today? You can ask about API issues, "
                "password reset, billing, refunds, or account access."
            )
            result = {
                "user_message": user_message,
                "answer": answer,
                "persona": persona_result.persona,
                "persona_confidence": persona_result.confidence,
                "classification_reasoning": persona_result.reasoning,
                "interaction_type": persona_result.interaction_type,
                "retrieval_confidence": None,
                "sources": [],
                "escalated": False,
                "escalation_reasons": [],
                "handoff_json": None,
                "support_pipeline_used": False,
            }
            st.session_state.latest_result = result
            _append_assistant_turn(answer, result)
            return

        # Support requests retrieve context before any answer or escalation decision.
        retrieved_chunks, retrieval_confidence = retrieve(user_message)
        sources = unique_sources(retrieved_chunks)
        escalation_result = detect_escalation(
            user_message=user_message,
            retrieval_confidence=retrieval_confidence,
            persona=persona_result.persona,
            persona_history=st.session_state.persona_history,
        )
        st.session_state.persona_history.append(persona_result.persona)
        st.session_state.persona_history = st.session_state.persona_history[-3:]

        handoff_json = None
        if escalation_result.escalated:
            # Escalated cases stop before final answer generation and prepare handoff data.
            answer = _escalation_chat_answer(escalation_result.escalation_reasons)
            handoff_json = generate_handoff_json(
                user_message=user_message,
                persona_result=persona_result,
                retrieval_confidence=retrieval_confidence,
                escalation_result=escalation_result,
                retrieved_sources=sources,
            )
        else:
            # Non-escalated responses are generated from retrieved knowledge only.
            response_result = generate_response(
                user_message=user_message,
                persona=persona_result.persona,
                retrieved_chunks=retrieved_chunks,
                retrieval_confidence=retrieval_confidence,
                escalation_status=escalation_result.escalated,
            )
            answer = response_result.answer

        result = {
            "user_message": user_message,
            "answer": answer,
            "persona": persona_result.persona,
            "persona_confidence": persona_result.confidence,
            "classification_reasoning": persona_result.reasoning,
            "interaction_type": persona_result.interaction_type,
            "retrieval_confidence": retrieval_confidence,
            "sources": sources,
            "escalated": escalation_result.escalated,
            "escalation_reasons": escalation_result.escalation_reasons,
            "handoff_json": handoff_json,
            "support_pipeline_used": True,
        }
        st.session_state.latest_result = result
        _append_assistant_turn(answer, result)
    except Exception as exc:
        result = {
            "error": str(exc),
            "user_message": user_message,
        }
        st.session_state.latest_result = result
        _append_assistant_turn(f"Error: {exc}", result)


def _render_chat() -> None:
    """Replay the stored conversation on each Streamlit rerun."""
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant" and message.get("metadata"):
                _render_assistant_metadata(message["metadata"])


def _render_assistant_metadata(result: dict[str, object]) -> None:
    """Render required trace details below an assistant answer."""
    if "error" in result:
        return
    if not result.get("support_pipeline_used"):
        return

    with st.expander("Persona"):
        st.write(f"Detected persona: {result['persona']}")
        st.write(f"Persona confidence: {result['persona_confidence']:.2f}")
        st.write(f"Classification reasoning: {result['classification_reasoning']}")

    with st.expander("Retrieval and Sources"):
        st.write(f"Retrieval confidence: {result['retrieval_confidence']:.2f}")
        st.write("Sources:")
        if result["sources"]:
            for source in result["sources"]:
                st.write(f"- {source}")
        else:
            st.write("- No reliable sources retrieved")

    with st.expander("Escalation"):
        st.write(f"Escalated: {'Yes' if result['escalated'] else 'No'}")
        if result["escalation_reasons"]:
            for reason in result["escalation_reasons"]:
                st.write(f"- {reason}")

    if result["handoff_json"]:
        with st.expander("Handoff JSON"):
            st.json(json.loads(json.dumps(result["handoff_json"])))


def _append_assistant_turn(answer: str, metadata: dict[str, object]) -> None:
    """Store the assistant response and its diagnostic metadata."""
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": answer, "metadata": metadata}
    )


def _escalation_chat_answer(reasons: list[str]) -> str:
    """Return the short user-facing message for escalated requests."""
    if "Low Confidence" in reasons and len(reasons) == 1:
        return (
            "I do not have enough detail to provide a grounded support answer yet. "
            "Please share the issue type, error message, or account area so a human support specialist can review it."
        )
    return (
        "This request needs human support review before a final support answer is provided. "
        "I prepared the escalation details for a support specialist."
    )


def _apply_page_styles() -> None:
    """Apply compact layout styles without changing Streamlit components."""
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1120px;
            padding-top: 0.9rem;
            padding-bottom: 5rem;
        }
        h1 {
            font-size: 1.65rem;
            margin-bottom: 0.1rem;
            line-height: 1.2;
        }
        [data-testid="stCaptionContainer"] {
            font-size: 0.9rem;
        }
        [data-testid="stChatMessage"] {
            padding: 0.45rem 0;
        }
        [data-testid="stChatMessage"] p {
            font-size: 0.95rem;
            line-height: 1.45;
            margin-bottom: 0.35rem;
        }
        [data-testid="stExpander"] {
            border-radius: 8px;
            margin-top: 0.35rem;
        }
        [data-testid="stExpander"] summary {
            font-size: 0.9rem;
            font-weight: 600;
        }
        [data-testid="stExpander"] p,
        [data-testid="stExpander"] li {
            font-size: 0.9rem;
            line-height: 1.35;
        }
        [data-testid="stStatusWidget"] {
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
