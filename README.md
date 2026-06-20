# Persona-Aware Customer Support Agent

A Streamlit-based customer support assistant that classifies a user's communication persona, retrieves relevant knowledge base context with RAG, generates grounded Gemini responses, and escalates sensitive or low-confidence cases to a human handoff JSON.

## Project Objective

The goal of this project is to demonstrate a practical AI support workflow that is safer than a normal chatbot:

1. Understand the user's intent and communication style.
2. Retrieve factual support context from local documents.
3. Generate a persona-adaptive answer using only retrieved context.
4. Show source attribution for every grounded answer.
5. Escalate cases that should not be fully automated.

The assistant supports exactly three personas:

- Technical Expert
- Frustrated User
- Business Executive

## Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11+ |
| UI | Streamlit |
| LLM and embeddings | Google Gemini via `google-genai` |
| Vector database | ChromaDB |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| PDF parsing | pypdf |
| Environment variables | python-dotenv |

Only the required stack is used.

## System Architecture

```text
User Message
    |
    v
Streamlit Chat UI
    |
    v
Gemini Persona Classifier
    |
    v
Gemini Query Embedding
    |
    v
ChromaDB Cosine Similarity Search
    |
    v
Top 3 Retrieved Knowledge Chunks
    |
    v
Escalation Policy Check
    |
    +--> Escalated: Human Handoff JSON
    |
    +--> Not Escalated: Gemini Grounded Response
    |
    v
Assistant Response + Persona + Confidence + Sources + Escalation Status
```

## How The Application Works

### 1. Persona Classification

The user message is sent to Gemini and classified into exactly one persona:

- `Technical Expert`: API terms, logs, auth headers, status codes, integrations, configuration.
- `Frustrated User`: urgency, complaints, emotional wording, repeated failures.
- `Business Executive`: operational impact, timelines, SLA, revenue, business risk.

The classifier returns:

- persona
- confidence
- reasoning
- interaction type

Simple greetings are handled conversationally so the app does not force unnecessary RAG output for messages like `hi`.

### 2. Knowledge Base Loading

The RAG pipeline loads supported files from `data/`:

- Markdown files: `.md`
- Plain text files: `.txt`
- PDF files: `.pdf`

PDF text is extracted page by page using `pypdf`, preserving page metadata where available.

### 3. Chunking

Documents are split with LangChain:

```text
Chunk size: 500 characters
Chunk overlap: 50 characters
```

This keeps chunks focused while reducing the chance that important context is split across boundaries.

### 4. Embeddings And ChromaDB

The app uses Gemini embeddings to convert document chunks and user queries into vectors.

Primary embedding model:

```text
gemini-embedding-001
```

ChromaDB stores:

- chunk text
- embedding vectors
- source file metadata
- page/chunk metadata

The vector store is persistent under:

```text
chroma_db/
```

The ChromaDB collection is:

```text
support_kb
```

The collection uses cosine similarity:

```python
metadata={"hnsw:space": "cosine"}
```

### 5. Retrieval

For each support request, the app embeds the user query and retrieves the top 3 most relevant chunks from ChromaDB.

```text
Top K: 3
```

The retrieval score is used as a confidence signal. Low-confidence retrieval triggers escalation.

### 6. Response Generation

For non-escalated requests, Gemini generates a customer-facing response using only the retrieved chunks.

The generator is instructed to:

- avoid hallucinations
- answer only from retrieved context
- adapt tone to the detected persona
- include source attribution using file names

### 7. Escalation And Human Handoff

The app escalates when automation is unsafe or insufficient.

Escalation triggers:

- retrieval confidence below `0.45`
- billing issues
- refund requests
- legal concerns
- account modification requests
- repeated frustrated messages

When escalated, the app does not generate a final support answer. It returns a short customer-facing escalation message and displays human handoff JSON.

The handoff JSON includes:

- ticket ID
- persona
- persona confidence
- retrieval confidence
- escalation reasons
- customer message
- issue summary
- conversation summary
- retrieved sources
- recommended human action

## Model Choices

### Text Models

The app uses `gemini-3.1-flash-lite-preview` first for persona classification and response generation because it provides the best available quota for this project environment.

Current text model order:

```python
(
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
)
```

Fallback models are included for reliability if the primary model is temporarily unavailable. Zero-quota models were removed to avoid unnecessary failed retries and slower responses.

### Embedding Model

The app uses:

```text
gemini-embedding-001
```

This model has usable embedding quota and was used to build the existing ChromaDB index. Keeping the embedding model stable is important because document vectors and query vectors should be generated with the same embedding model family. If the embedding model is changed, the vector database should be rebuilt.

## Rate Limit Handling

Gemini calls are wrapped with a small exponential backoff helper. If a transient API or rate-limit error occurs, the app retries briefly before surfacing the error.

This is used for:

- persona classification
- embeddings
- response generation

## Project Structure

```text
persona-support-agent/
|-- app.py
|-- requirements.txt
|-- README.md
|-- .env.example
|-- .gitignore
|-- data/
|   |-- account_recovery.md
|   |-- api_authentication.md
|   |-- api_error_codes.md
|   |-- api_troubleshooting.md
|   |-- billing_policy.txt
|   |-- browser_login_troubleshooting.md
|   |-- integration_best_practices.md
|   |-- invoice_and_payment_review.txt
|   |-- password_reset_guide.pdf
|   |-- refund_and_dispute_escalation.txt
|-- src/
|   |-- __init__.py
|   |-- config.py
|   |-- classifier.py
|   |-- rag_pipeline.py
|   |-- generator.py
|   |-- escalator.py
|   |-- retry.py
```

`chroma_db/` is generated locally and intentionally ignored by Git. Rebuild it from the knowledge base when needed.

## Knowledge Base

The `data/` directory contains 10 realistic help desk articles using Markdown, text, and PDF formats.

| File | Purpose |
| --- | --- |
| `account_recovery.md` | Account recovery and manual verification guidance |
| `api_authentication.md` | Bearer token authentication and authorization headers |
| `api_error_codes.md` | Common API status codes and debugging direction |
| `api_troubleshooting.md` | API failure investigation and support evidence |
| `billing_policy.txt` | Billing boundaries and human review requirements |
| `browser_login_troubleshooting.md` | Browser cache, cookies, extensions, and login loading issues |
| `integration_best_practices.md` | Integration diagnostics, logging, retries, and environment checks |
| `invoice_and_payment_review.txt` | Invoice, duplicate charge, and payment review guidance |
| `password_reset_guide.pdf` | Password reset and reset email troubleshooting |
| `refund_and_dispute_escalation.txt` | Refund, dispute, and duplicate charge escalation |

## Knowledge Base Source References

The knowledge base is paraphrased and structured as support documentation from public documentation concepts. Source references are listed here instead of inside `data/` so RAG retrieves only application-ready support guidance.

API and HTTP references:

- MDN Web Docs, Authorization header: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Authorization
- MDN Web Docs, 401 Unauthorized: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/401
- MDN Web Docs, HTTP response status codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status

Billing and payments references:

- Stripe Docs, Billing overview: https://docs.stripe.com/billing
- Stripe Docs, Invoicing overview: https://docs.stripe.com/invoicing/overview
- Stripe Docs, Subscriptions overview: https://docs.stripe.com/billing/subscriptions/overview
- Stripe Docs, Refunds: https://docs.stripe.com/refunds

Account and browser references:

- Google Account Help, Change or reset your password: https://support.google.com/accounts/answer/41078
- Google Account Help, Recover your account: https://support.google.com/accounts/answer/7682439
- Google Account Help, Clear cache and cookies: https://support.google.com/accounts/answer/32050

## Setup

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Gemini API key

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=your_gemini_api_key_here
```

Do not commit `.env`.

## Build The RAG Index

Run this command after setting `GEMINI_API_KEY`:

```bash
python -m src.rag_pipeline
```

Expected output after the index already exists:

```text
Indexed 0 new chunk(s) into support_kb.
```

If documents are changed, the app can index missing chunks automatically, but running the indexing command explicitly is recommended before a demo.

## Run The App

```bash
streamlit run app.py
```

The UI displays:

- user message
- assistant response
- detected persona
- persona confidence
- classification reasoning
- retrieval confidence
- sources
- escalation status
- handoff JSON when escalated

## Manual Validation Scenarios

Use these prompts in the Streamlit UI to validate the complete workflow during review or demonstration. Start a fresh chat when validating a single expected behavior, because repeated frustrated messages intentionally trigger escalation.

### Greeting

```text
hi
```

Expected behavior:

- friendly short response
- no forced RAG metadata
- no escalation

### Technical Expert

```text
What are the header parameter requirements for your bearer token auth implementation?
```

Expected behavior:

- persona: Technical Expert
- retrieves API authentication documentation
- explains `Authorization: Bearer <access_token>`
- shows source attribution
- no escalation

### Frustrated User

```text
Where is the guide to clear cookies? It has been an hour and nothing is loading on your interface!
```

Expected behavior:

- persona: Frustrated User
- empathetic response
- simple troubleshooting steps
- browser/cache/cookie source attribution
- no escalation in a fresh chat unless repeated frustration has already occurred

### Business Executive

```text
Our operational uptime is decreasing. We need a timeline of when billing disputes are resolved.
```

Expected behavior:

- persona: Business Executive
- billing-sensitive topic detected
- escalation with handoff JSON

### Billing And Refund Escalation

```text
My billing statement has unexpected duplicate charges. I demand an immediate refund!
```

Expected behavior:

- persona: Frustrated User
- escalation reasons include Billing Issue and Refund Request
- handoff JSON is displayed

### Legal Escalation

```text
I will contact my lawyer and file a lawsuit if this is not fixed.
```

Expected behavior:

- escalation reason includes Legal Concern
- handoff JSON is displayed

### Account Modification Escalation

```text
Delete my account and transfer ownership to another person.
```

Expected behavior:

- escalation reason includes Account Modification Request
- handoff JSON is displayed

### Low Confidence Escalation

```text
Can you explain the weather forecast for next week?
```

Expected behavior:

- low retrieval confidence
- escalation reason includes Low Confidence
- no unsupported answer is generated

## Manual Verification Checklist

Before presenting or deploying the project, verify these points from the UI:

- The app starts with `streamlit run app.py`.
- A greeting receives a short conversational response.
- Technical API questions retrieve API sources and show source attribution.
- Browser or password recovery questions retrieve relevant help content.
- Billing, refund, legal, and account modification questions escalate.
- Escalated messages show structured handoff JSON.
- Low-confidence unrelated questions do not produce unsupported answers.
- Persona, confidence, retrieval confidence, sources, and escalation status appear under the assistant response.


## Project Capability Checklist

- Uses Python 3.11+
- Uses Google Gemini for persona classification
- Uses Google Gemini for response generation
- Uses Gemini embeddings for RAG retrieval
- Uses ChromaDB as the local vector database
- Configures ChromaDB for cosine similarity
- Uses LangChain `RecursiveCharacterTextSplitter`
- Loads Markdown, text, and PDF documents
- Includes at least one instructional PDF
- Contains 10 realistic help desk articles
- Covers password recovery, API authentication, and payment pathways
- Retrieves top 3 chunks
- Generates grounded responses using retrieved context
- Displays source attribution
- Supports Technical Expert, Frustrated User, and Business Executive personas
- Escalates low confidence, billing, refund, legal, account modification, and repeated frustration cases
- Generates structured human handoff JSON
- Provides Streamlit chat UI
- Includes manual validation scenarios
- Includes deployment instructions

## Limitations

- The app answers only from the local knowledge base.
- It does not connect to real billing systems, account systems, or ticketing platforms.
- It does not perform identity verification.
- It does not use web search at runtime.
- Gemini quota limits may affect live testing or deployment if the API key has limited free-tier usage.

## Security Notes

- Store API keys only in `.env` locally or deployment secrets in production.
- Do not commit private keys or real customer data.
- Redact tokens, request IDs, and customer identifiers before using logs in support prompts.
