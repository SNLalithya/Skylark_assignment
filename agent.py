"""
agent.py — Skylark Drones BI Agent
====================================
LangGraph-powered agent that answers business questions using
monday.com board data.

Architecture:
  User query
      │
      ▼
  Router (Groq / Llama 3.1 70B)
      │
      ├─── query_work_orders  ──► monday_client.get_work_orders()
      ├─── query_deals        ──► monday_client.get_deals()
      ├─── query_both         ──► both boards
      └─── answer_directly    ──► LLM-only (no data needed)
      │
      ▼
  Response Formatter
      │
      ▼
  Final answer with confidence score

Environment variables:
  GROQ_API_KEY  — Groq API key (free tier, Llama 3.1 70B)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

import monday_client as mc

load_dotenv()
logger = logging.getLogger(__name__)

# ── LLM setup ─────────────────────────────────────────────────────────────────

def _build_llm(temperature: float = 0.0) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        api_key=api_key,
        max_retries=3,
    )


# ── Agent state ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:        str
    route:           str           # "work_orders" | "deals" | "both" | "direct"
    work_order_data: dict | None
    deal_data:       dict | None
    answer:          str


# ── System prompts ────────────────────────────────────────────────────────────

ROUTER_SYSTEM = """You are a router for a business intelligence agent serving Skylark Drones.

Your job: classify the user's question into ONE of these routes:
  - "work_orders" — question is about work orders, service requests, field operations, engineers, sectors, job status, overdue tasks
  - "deals"       — question is about deals, sales pipeline, revenue, clients, deal stages, close dates, deal owners
  - "both"        — question requires data from BOTH work orders and deals
  - "direct"      — question is general and can be answered without fetching board data (e.g. greetings, definitions, how-to questions)

Respond with ONLY a JSON object: {"route": "<route>", "reason": "<one sentence>"}
No extra text."""

ANALYST_SYSTEM = """You are a senior business intelligence analyst for Skylark Drones — a drone services company.

Today's date: {today}

You have access to live data from the company's monday.com boards.
Answer the user's question clearly, using the data provided.

Rules:
1. Be concise and precise — founders want fast answers.
2. Use markdown tables for comparisons and lists.
3. Always mention the data source (board name) and item count.
4. End every answer with a confidence indicator:
   ✅ High confidence | ⚠️ Medium confidence | ❌ Low confidence
   (use the confidence value from the data payload)
5. If data is missing or ambiguous, say so — never make up numbers.
6. Format currency as $X,XXX (e.g. $4,820,000 → $4.82M).
7. For "overdue" checks, compare due dates against today ({today}).
"""


# ── Node: Router ──────────────────────────────────────────────────────────────

def route_question(state: AgentState) -> AgentState:
    """Use the LLM to classify the question and pick a data source."""
    llm = _build_llm(temperature=0.0)
    messages = [
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content=state["question"]),
    ]
    raw = llm.invoke(messages).content.strip()

    import re
    match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if match:
        parsed = json.loads(match.group())
        route  = parsed.get("route", "direct")
    else:
        route = "direct"

    logger.info(f"[Router] question='{state['question']}' → route='{route}'")
    return {**state, "route": route}


# ── Node: Fetch Work Orders ───────────────────────────────────────────────────

def fetch_work_orders(state: AgentState) -> AgentState:
    try:
        data = mc.get_work_orders()
        logger.info(f"[FetchWO] retrieved {data['count']} items, confidence={data['confidence']}")
    except Exception as exc:
        logger.error(f"[FetchWO] error: {exc}")
        data = {"board": "Work Order Tracker", "count": 0, "confidence": "Low",
                "items": [], "error": str(exc)}
    return {**state, "work_order_data": data}


# ── Node: Fetch Deals ─────────────────────────────────────────────────────────

def fetch_deals(state: AgentState) -> AgentState:
    try:
        data = mc.get_deals()
        logger.info(f"[FetchDeals] retrieved {data['count']} items, confidence={data['confidence']}")
    except Exception as exc:
        logger.error(f"[FetchDeals] error: {exc}")
        data = {"board": "Deal Tracker", "count": 0, "confidence": "Low",
                "items": [], "error": str(exc)}
    return {**state, "deal_data": data}


# ── Node: Fetch Both ──────────────────────────────────────────────────────────

def fetch_both(state: AgentState) -> AgentState:
    state = fetch_work_orders(state)
    state = fetch_deals(state)
    return state


# ── Node: Generate Answer ─────────────────────────────────────────────────────

def _summarize_items(items: list[dict], max_items: int = 200) -> list[dict]:
    trimmed = []
    for item in items[:max_items]:
        meta   = {k: v for k, v in item.items() if k.startswith("__")}
        fields = {k: v for k, v in item.items() if not k.startswith("__")}
        kept   = {k: v for k, v in list(fields.items())[:8] if v is not None}
        trimmed.append({**meta, **kept})
    return trimmed


def generate_answer(state: AgentState) -> AgentState:
    llm = _build_llm(temperature=0.2)
    context_parts: list[str] = []

    if state.get("work_order_data"):
        wo = state["work_order_data"]
        if wo.get("error"):
            context_parts.append(f"[Work Orders ERROR] {wo['error']}")
        else:
            summary = _summarize_items(wo["items"])
            context_parts.append(
                f"[Work Orders — {wo['board']}]\n"
                f"Total items: {wo['count']} | Confidence: {wo['confidence']}\n"
                f"Data (first {len(summary)} rows):\n"
                f"{json.dumps(summary, indent=2, default=str)}"
            )

    if state.get("deal_data"):
        dd = state["deal_data"]
        if dd.get("error"):
            context_parts.append(f"[Deals ERROR] {dd['error']}")
        else:
            summary = _summarize_items(dd["items"])
            context_parts.append(
                f"[Deals — {dd['board']}]\n"
                f"Total items: {dd['count']} | Confidence: {dd['confidence']}\n"
                f"Data (first {len(summary)} rows):\n"
                f"{json.dumps(summary, indent=2, default=str)}"
            )

    if context_parts:
        data_block   = "\n\n---\n\n".join(context_parts)
        user_content = (
            f"DATA FROM MONDAY.COM:\n\n{data_block}\n\n"
            f"USER QUESTION: {state['question']}"
        )
    else:
        user_content = state["question"]

    messages = [
        SystemMessage(content=ANALYST_SYSTEM.format(today=date.today().isoformat())),
        HumanMessage(content=user_content),
    ]

    answer = llm.invoke(messages).content.strip()
    return {**state, "answer": answer}


# ── Conditional routing edge ──────────────────────────────────────────────────

def _route_edge(state: AgentState) -> Literal[
    "fetch_work_orders", "fetch_deals", "fetch_both", "generate_answer"
]:
    r = state.get("route", "direct")
    if r == "work_orders":  return "fetch_work_orders"
    if r == "deals":        return "fetch_deals"
    if r == "both":         return "fetch_both"
    return "generate_answer"


# ── Graph builder ─────────────────────────────────────────────────────────────

def create_agent() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("route_question",    route_question)
    graph.add_node("fetch_work_orders", fetch_work_orders)
    graph.add_node("fetch_deals",       fetch_deals)
    graph.add_node("fetch_both",        fetch_both)
    graph.add_node("generate_answer",   generate_answer)

    graph.set_entry_point("route_question")
    graph.add_conditional_edges(
        "route_question", _route_edge,
        {
            "fetch_work_orders": "fetch_work_orders",
            "fetch_deals":       "fetch_deals",
            "fetch_both":        "fetch_both",
            "generate_answer":   "generate_answer",
        },
    )
    graph.add_edge("fetch_work_orders", "generate_answer")
    graph.add_edge("fetch_deals",       "generate_answer")
    graph.add_edge("fetch_both",        "generate_answer")
    graph.add_edge("generate_answer",   END)
    return graph.compile()


# ── Runner ────────────────────────────────────────────────────────────────────

def run_agent(agent: Any, question: str) -> str:
    initial: AgentState = {
        "question": question, "route": "",
        "work_order_data": None, "deal_data": None, "answer": "",
    }
    final = agent.invoke(initial)
    return final.get("answer", "I couldn't generate an answer. Please try again.")


# ── Quick local test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ag = create_agent()
    print(run_agent(ag, "What is the total deal value in the pipeline?"))

# Compatibility aliases required by app.py
_agent_instance = None

def _get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_agent()
    return _agent_instance

def run(question):
    return run_agent(_get_agent(), question)

def generate_leadership_brief_fn():
    prompt = (
        "Generate a concise executive leadership brief covering: "
        "(1) total open work orders and any overdue ones, "
        "(2) total pipeline deal value with breakdown by stage, "
        "(3) top 3 actionable insights for leadership today. "
        "Use bullet points."
    )
    return run_agent(_get_agent(), prompt)
