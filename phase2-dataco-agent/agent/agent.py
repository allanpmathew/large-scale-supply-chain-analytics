"""DataCo exception-handling agent.

A Claude tool-calling loop that investigates late/at-risk orders. Two tools
run freely; `flag_late_shipment` is gated on human y/n approval in the
terminal before it can execute.

Usage:
    python3 agent.py "Investigate late deliveries and recommend actions."
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from tools import check_inventory, flag_late_shipment, query_orders

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 20

_AGENT_DIR = Path(__file__).resolve().parent
_PHASE_DIR = _AGENT_DIR.parent
_TRANSCRIPT_PATH = _PHASE_DIR / "outputs" / "sample_run.md"

load_dotenv(_AGENT_DIR / ".env")


# --------------------------------------------------------------------------- #
# Tool schemas exposed to Claude
# --------------------------------------------------------------------------- #

TOOL_SCHEMAS = [
    {
        "name": "query_orders",
        "description": (
            "Filter the DataCo order table. Returns a summary dict "
            "(matched count, delivery-status breakdown, avg real vs. scheduled "
            "shipping days, late-delivery-risk %) plus a small sample of rows.\n\n"
            "PRODUCT HIERARCHY — the dataset has two levels:\n"
            "  • `category` filters Category Name — the fine-grained product-line "
            "level (e.g. 'Sporting Goods', 'Cleats', 'Fitness Accessories').\n"
            "  • `department` filters Department Name — the higher-level grouping "
            "(e.g. 'Fitness', 'Apparel', 'Footwear').\n"
            "These are DIFFERENT levels. 'Fitness' is a Department, not a Category. "
            "If a filter returns 0 matches, the response will include a `hint` "
            "field pointing you at the correct column — follow it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "delivery_status": {
                    "type": "string",
                    "description": (
                        "Exact match on Delivery Status. One of: "
                        "'Late delivery', 'Advance shipping', 'Shipping on time', "
                        "'Shipping canceled'."
                    ),
                },
                "region": {
                    "type": "string",
                    "description": (
                        "Order Region (case-insensitive exact match). Examples: "
                        "'Southeast Asia', 'Western Europe', 'Central America'."
                    ),
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Category Name — fine-grained product line (case-insensitive "
                        "substring). Example: 'Cleats', 'Sporting Goods'."
                    ),
                },
                "department": {
                    "type": "string",
                    "description": (
                        "Department Name — higher-level grouping (case-insensitive "
                        "substring). Example: 'Fitness', 'Apparel'."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD). Filters order date >=.",
                },
                "end_date": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD). Filters order date <=.",
                },
                "late_only": {
                    "type": "boolean",
                    "description": "Shortcut: restrict to Late_delivery_risk == 1.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of sample rows to return (default 5).",
                },
            },
        },
    },
    {
        "name": "check_inventory",
        "description": (
            "Aggregated order-volume view for a product or category — a proxy for "
            "inventory pressure since the dataset has no on-hand stock column. "
            "Matches Product Name OR Category Name via case-insensitive substring. "
            "Returns total orders, units moved, late-delivery share, top regions, "
            "and shipping-mode mix."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_or_category": {
                    "type": "string",
                    "description": (
                        "Product name (e.g. 'Smart watch') or category name "
                        "(e.g. 'Cleats')."
                    ),
                },
            },
            "required": ["product_or_category"],
        },
    },
    {
        "name": "flag_late_shipment",
        "description": (
            "Log a specific order as late-flagged with a short investigation note. "
            "Appends to outputs/flagged_orders.csv with timestamp and full context. "
            "HUMAN APPROVAL REQUIRED — every call is reviewed by the operator "
            "before it executes. If rejected, you will be told and should either "
            "revise the rationale or move on."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "Order Id from the DataCo dataset.",
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Short investigation note — cite the evidence (e.g. "
                        "'5-day gap vs scheduled 2 days, Standard Class, "
                        "Southeast Asia cluster')."
                    ),
                },
            },
            "required": ["order_id", "reason"],
        },
    },
]


# --------------------------------------------------------------------------- #
# System prompt
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """You are a supply chain operations analyst investigating late and at-risk orders in the DataCo dataset.

Your job:
1. Query the data to identify where late deliveries concentrate — which regions, categories, departments, customer segments, and shipping modes are worst affected.
2. Diagnose likely causes. Compare scheduled-vs-real shipping-day gaps across slices. Check whether specific shipping modes are chronically late. Consider whether the late_delivery_risk flag is already catching these orders in advance.
3. Propose specific, actionable next steps — expedite, switch shipping mode, notify customer, escalate to a regional lead, etc.
4. Flag the worst individual orders using `flag_late_shipment` so operations can act on them. Each flag is reviewed by a human before it logs; expect and respect rejections.

Guidance:
- The dataset has ~180k orders. Filter aggressively — don't ask for everything.
- Category Name and Department Name are different levels of the product hierarchy. If a query returns 0 matches with a `hint` field, follow the hint.
- When you're done investigating, end with a concise briefing: root-cause summary, top affected slices, and 2–4 recommended actions.
"""


# --------------------------------------------------------------------------- #
# Transcript writer
# --------------------------------------------------------------------------- #

class Transcript:
    """Streams lines to both console and the markdown file.

    Writes to disk after every line so a partial transcript survives crashes
    and so the operator can `tail -f outputs/sample_run.md` while the agent
    runs.
    """

    def __init__(self, path: Path):
        self.path = path
        self.lines: list[str] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Truncate at start of run.
        self.path.write_text("", encoding="utf-8")

    def write(self, s: str = "") -> None:
        self.lines.append(s)
        print(s)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def _fmt(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


# --------------------------------------------------------------------------- #
# Human-in-the-loop confirmation for flag_late_shipment
# --------------------------------------------------------------------------- #

def _confirm() -> bool:
    print("Approve? [y/N]: ", end="", flush=True)
    try:
        answer = input().strip().lower()
    except EOFError:
        answer = ""
    return answer == "y"


def dispatch(name: str, args: dict, tx: Transcript) -> str:
    """Route a tool call to its Python implementation. Gates flag_late_shipment."""
    if name == "query_orders":
        return _fmt(query_orders(args))
    if name == "check_inventory":
        return _fmt(check_inventory(args["product_or_category"]))
    if name == "flag_late_shipment":
        tx.write("")
        tx.write("> **Human approval required**  ")
        tx.write(
            f"> Proposed flag → order_id=`{args.get('order_id')}`, "
            f"reason: {args.get('reason')!r}"
        )
        approved = _confirm()
        tx.write(f"> Operator response: **{'APPROVED' if approved else 'REJECTED'}**")
        if not approved:
            return _fmt(
                {
                    "ok": False,
                    "error": (
                        "Human operator rejected this flag. Do not retry the same "
                        "order without stronger justification; consider a different "
                        "order or a sharper reason."
                    ),
                }
            )
        return _fmt(flag_late_shipment(args["order_id"], args["reason"]))
    return _fmt({"error": f"unknown tool {name}"})


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #

def run(user_task: str) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY missing — put it in agent/.env")

    client = Anthropic()
    tx = Transcript(_TRANSCRIPT_PATH)

    tx.write("# DataCo Agent — Sample Run")
    tx.write("")
    tx.write(f"- **Model:** `{MODEL}`")
    tx.write(f"- **Timestamp:** {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    tx.write(f"- **Task:** {user_task}")
    tx.write("")
    tx.write("---")
    tx.write("")

    messages: list[dict] = [{"role": "user", "content": user_task}]

    for turn in range(1, MAX_TURNS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        tx.write(f"## Turn {turn}")
        tx.write(f"_stop_reason: `{response.stop_reason}`_")
        tx.write("")

        assistant_content = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                if block.text.strip():
                    tx.write("**Assistant:**")
                    tx.write("")
                    tx.write(block.text)
                    tx.write("")
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tx.write(f"**Tool call → `{block.name}`**")
                tx.write("")
                tx.write("```json")
                tx.write(_fmt(block.input))
                tx.write("```")
                tx.write("")
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
                tool_uses.append(block)

        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason != "tool_use":
            tx.write("---")
            tx.write("")
            tx.write("_Agent finished (no more tool calls)._")
            break

        tool_results = []
        for tu in tool_uses:
            result_text = dispatch(tu.name, tu.input, tx)
            tx.write(f"**Tool result ← `{tu.name}`**")
            tx.write("")
            tx.write("```json")
            tx.write(result_text)
            tx.write("```")
            tx.write("")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_text,
                }
            )
        messages.append({"role": "user", "content": tool_results})
    else:
        tx.write("---")
        tx.write("")
        tx.write(f"_Hit max turns ({MAX_TURNS}) — stopping._")

    print(f"\nTranscript saved to {_TRANSCRIPT_PATH}")


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or (
        "Investigate late deliveries in the most affected region and recommend actions."
    )
    run(task)
