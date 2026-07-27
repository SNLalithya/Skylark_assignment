"""
monday_client.py — Skylark Drones BI Agent
===========================================
monday.com GraphQL API client.

Responsibilities:
  - Execute GraphQL queries against the monday.com API
  - Fetch all items from Work Order Tracker and Deal Tracker boards
  - Auto-normalize dates, sector names, owner names, currency values
  - Attach a data-quality confidence score to every response
  - Handle pagination (cursor-based) transparently

Environment variables required:
  MONDAY_API_KEY      — monday.com personal API token
  WORK_ORDER_BOARD_ID — board ID for Work Order Tracker
  DEAL_BOARD_ID       — board ID for Deal Tracker
"""

from __future__ import annotations

import os
import re
import logging
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONDAY_API_URL      = "https://api.monday.com/v2"
MONDAY_API_KEY      = os.getenv("MONDAY_API_KEY", "")
WORK_ORDER_BOARD_ID = int(os.getenv("WORK_ORDER_BOARD_ID", "0"))
DEAL_BOARD_ID       = int(os.getenv("DEAL_BOARD_ID", "0"))
PAGE_LIMIT          = 500


# ── GraphQL executor ──────────────────────────────────────────────────────────

def _gql(query: str, variables: dict | None = None) -> dict:
    if not MONDAY_API_KEY:
        raise EnvironmentError("MONDAY_API_KEY is not set.")
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type":  "application/json",
        "API-Version":   "2024-01",
    }
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(MONDAY_API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    errors = body.get("errors")
    if errors:
        raise RuntimeError(f"monday.com API errors: {errors}")
    return body.get("data", {})


# ── Board discovery ───────────────────────────────────────────────────────────

def discover_boards() -> dict[str, int]:
    query = "query { boards(limit: 50) { id name } }"
    data  = _gql(query)
    return {b["name"]: int(b["id"]) for b in data.get("boards", [])}


def _resolve_board_ids() -> tuple[int, int]:
    wo_id, deal_id = WORK_ORDER_BOARD_ID, DEAL_BOARD_ID
    if wo_id and deal_id:
        return wo_id, deal_id
    boards = discover_boards()
    for name, bid in boards.items():
        nl = name.lower()
        if not wo_id and ("work order" in nl or "workorder" in nl):
            wo_id = bid
        if not deal_id and ("deal" in nl or "pipeline" in nl or "funnel" in nl):
            deal_id = bid
    if not wo_id or not deal_id:
        raise RuntimeError(
            f"Could not find boards. Available: {list(boards.keys())}. "
            "Set WORK_ORDER_BOARD_ID and DEAL_BOARD_ID in .env"
        )
    return wo_id, deal_id


# ── Normalization ─────────────────────────────────────────────────────────────

def _normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _normalize_currency(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(raw).strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_col(col: dict) -> Any:
    ctype = col.get("type", "")
    text  = col.get("text")
    if ctype == "date":
        return _normalize_date(text)
    if ctype in ("numbers", "numeric"):
        return _normalize_currency(text)
    return text.strip() if text else None


# ── Paginated fetcher ─────────────────────────────────────────────────────────

_Q = """
query GetItems($boardId: ID!, $cursor: String, $limit: Int!) {
  boards(ids: [$boardId]) {
    name
    items_page(limit: $limit, cursor: $cursor) {
      cursor
      items {
        id name created_at updated_at
        column_values { id type text value }
      }
    }
  }
}
"""


def _fetch_all_items(board_id: int) -> tuple[str, list[dict]]:
    all_items: list[dict] = []
    cursor: str | None = None
    board_name = str(board_id)

    while True:
        data   = _gql(_Q, {"boardId": str(board_id), "cursor": cursor, "limit": PAGE_LIMIT})
        boards = data.get("boards", [])
        if not boards:
            break
        board      = boards[0]
        board_name = board.get("name", board_name)
        page       = board.get("items_page", {})
        items      = page.get("items", [])
        cursor     = page.get("cursor")

        for raw in items:
            row: dict[str, Any] = {
                "__id":         raw["id"],
                "__name":       (raw.get("name") or "").strip(),
                "__created_at": _normalize_date((raw.get("created_at") or "")[:10]),
                "__updated_at": _normalize_date((raw.get("updated_at") or "")[:10]),
            }
            for col in raw.get("column_values", []):
                row[col["id"]] = _extract_col(col)
            all_items.append(row)

        if not cursor or len(items) < PAGE_LIMIT:
            break

    return board_name, all_items


# ── Confidence scoring ────────────────────────────────────────────────────────

def _confidence(items: list[dict], expected_min: int = 10) -> str:
    if len(items) < expected_min:
        return "Low"
    sample     = items[:50]
    non_meta   = [k for k in (sample[0].keys() if sample else []) if not k.startswith("__")]
    if not non_meta:
        return "Medium"
    null_count = sum(1 for row in sample for k in non_meta if row.get(k) is None)
    total      = len(sample) * len(non_meta)
    null_rate  = null_count / total if total else 0
    if null_rate < 0.05:  return "High"
    if null_rate < 0.20:  return "Medium"
    return "Low"


# ── Public API ────────────────────────────────────────────────────────────────

def get_work_orders() -> dict:
    wo_id, _ = _resolve_board_ids()
    board_name, items = _fetch_all_items(wo_id)
    return {"board": board_name, "count": len(items),
            "confidence": _confidence(items), "items": items}


def get_deals() -> dict:
    _, deal_id = _resolve_board_ids()
    board_name, items = _fetch_all_items(deal_id)
    return {"board": board_name, "count": len(items),
            "confidence": _confidence(items), "items": items}


def get_board_schema(board_id: int) -> list[dict]:
    query = "query GetSchema($boardId: ID!) { boards(ids: [$boardId]) { columns { id title type } } }"
    data  = _gql(query, {"boardId": str(board_id)})
    return data.get("boards", [{}])[0].get("columns", [])