# Decision Log — Skylark Drones BI Agent
**Author:** S.N Lalithya | **Date:** July 27, 2026 | **Version:** 1.0

---

## 1. Architecture Decisions

### 1.1 Three-Layer Architecture
**Decision:** Separate the system into three distinct layers — Data (monday.com boards), Agent Logic (LangGraph + Groq), and Interface (Chainlit).

**Rationale:** Clean separation of concerns allows each layer to evolve independently. The data layer can be swapped (e.g., adding a PostgreSQL cache) without touching the UI. The agent layer can be upgraded to a multi-agent graph without changing the interface.

**Trade-off:** Adds initial complexity vs. a single-file script, but pays off in maintainability and extensibility.

---

### 1.2 LangGraph over Plain LangChain
**Decision:** Use LangGraph's `StateGraph` for agent orchestration instead of a simple LangChain `AgentExecutor`.

**Rationale:** LangGraph provides explicit state management, conditional routing, and retry logic as first-class primitives. This is critical for a BI agent that must decide whether to query Work Orders, Deals, or both — and handle partial failures gracefully.

**Trade-off:** Steeper learning curve than `AgentExecutor`, but enables multi-step reasoning chains and future expansion to parallel tool calls.

---

### 1.3 Groq (Free Tier) over OpenAI
**Decision:** Replace `ChatOpenAI` (GPT-4o) with `ChatGroq` (Llama 3.1 70B) as the LLM backbone.

**Rationale:** The assignment requires a hosted, publicly accessible demo. OpenAI charges per token; Groq's free tier provides 14,400 requests/day at ~280 tokens/second — sufficient for a demo workload. Llama 3.1 70B performs comparably to GPT-3.5-turbo on structured data Q&A tasks.

**Trade-off:** Groq free tier has rate limits (6,000 tokens/min). For production, a paid tier or OpenAI would be preferred. Mitigation: added exponential back-off in `agent.py`.

---

### 1.4 monday.com REST API (Direct) over SDK
**Decision:** Use `requests` directly against the monday.com GraphQL API rather than an official SDK.

**Rationale:** No official Python SDK exists that supports the full GraphQL surface. Direct `requests` calls give full control over query shape, pagination cursors, and column-value parsing. The `monday_client.py` module encapsulates all API logic behind a clean interface.

**Trade-off:** More boilerplate than an SDK, but zero hidden abstractions that could mask errors.

---

### 1.5 Chainlit over Streamlit / Gradio
**Decision:** Use Chainlit as the chat interface framework.

**Rationale:** Chainlit is purpose-built for LLM chat apps — it provides streaming, step visualization, session management, and a production-ready UI out of the box. Streamlit requires manual state hacks for chat; Gradio's chat component lacks step-level introspection.

**Trade-off:** Chainlit is less mature than Streamlit (smaller community, fewer plugins). Mitigated by its active development and Railway-compatible deployment.

---

## 2. Data Quality Decisions

### 2.1 Auto-Normalization on Ingest
**Decision:** Normalize dates (ISO 8601), sector names (title-case), and owner names (strip whitespace) at the `monday_client.py` layer before returning data to the agent.

**Rationale:** monday.com boards contain user-entered data with inconsistent formatting. Normalizing at the client layer means the agent always receives clean data, reducing hallucination risk from malformed inputs.

**Trade-off:** Normalization adds ~5ms per API call. Acceptable for interactive BI queries.

### 2.2 Confidence Scoring
**Decision:** Attach a `data_quality` confidence score (High / Medium / Low) to every agent response based on completeness of the retrieved dataset.

**Rationale:** If a board query returns fewer items than expected (e.g., due to API pagination limits), the agent should caveat its answer rather than present incomplete data as fact.

---

## 3. Leadership Update Interpretation

The assignment brief states: *"Build a BI agent that a founder can use to get instant answers about their business."*

**Interpretation:** The primary user is a non-technical founder who needs:
1. **Speed** — answers in <3 seconds, not dashboards that take minutes to load.
2. **Plain English** — no SQL, no filters, no column IDs.
3. **Trust signals** — the agent must cite which board/column it used, so the founder can verify.
4. **Mobile-friendly** — founders check metrics on phones; the UI must be responsive.

This shaped every decision above: Groq for speed, Chainlit for conversational UX, normalization for trust, and the responsive CSS overhaul for mobile access.

---

## 4. Deployment Decision

**Decision:** Railway over Heroku / Render / Fly.io.

**Rationale:** Railway auto-detects Python projects, provides a free starter tier, and deploys from GitHub in <2 minutes. It natively supports the `PORT` environment variable that Chainlit respects (`--port $PORT`). Heroku's free tier was discontinued; Render has a cold-start delay; Fly.io requires Docker expertise.

**Trade-off:** Railway's free tier sleeps after 30 minutes of inactivity. For a demo, this is acceptable.

---

*End of Decision Log — 2 pages*
