# Phase 2 — DataCo Exception-Handling Agent

A Claude tool-calling agent that investigates late and at-risk orders in the DataCo Smart Supply Chain dataset (180,519 orders). The agent queries data autonomously but requires human terminal approval before taking any operational action.

## How It Works

The agent runs a multi-turn tool-calling loop powered by Claude Sonnet. On each turn, Claude reads the conversation history and decides which tool to call next. Read-only tools (`query_orders`, `check_inventory`) execute immediately. The action tool (`flag_late_shipment`) pauses execution and prints a confirmation prompt to the terminal — the operator must type `y` to approve or `n` to reject before the agent continues.

This creates two trust levels: the agent investigates freely, but a human gates every operational decision.

## Tools

| Tool | Type | Trust Level | Description |
|---|---|---|---|
| `query_orders` | read | autonomous | Filter 180k orders by delivery status, region, category, department, date range, or late-risk flag. Returns summary stats and sample rows. |
| `check_inventory` | read | autonomous | Aggregated order-volume view for a product or category — total orders, units moved, late-delivery share, top regions, and shipping-mode mix. |
| `flag_late_shipment` | action | human approval | Log a specific order as late-flagged with a timestamped investigation note. Appends to `outputs/flagged_orders.csv`. Every call requires terminal y/n approval. |

### Why Action Tools Are Gated

In supply chain operations, flagging an order triggers downstream workflows — re-routing, customer notifications, carrier escalations. A false flag wastes operational time and erodes trust. Gating `flag_late_shipment` behind human approval means the agent can surface evidence and recommend, but a human makes the final call on whether to act. This is the same pattern used in regulated environments (pharma, defence, public sector) where auditability and accountability matter.

## Running the Agent

```bash
cd phase2-dataco-agent/agent

# Install dependencies
pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add your real ANTHROPIC_API_KEY

# Run
python3 agent.py "Investigate late deliveries in the most affected region and recommend actions."
```

The transcript is saved to `outputs/sample_run.md` after each turn. You can `tail -f outputs/sample_run.md` in a separate terminal to watch the agent work.

## Key Findings (Sample Run)

The agent's first real investigation produced these results:

- **Central America** is the worst-affected region at **57.9% late delivery rate** (15,548 late out of 26,839 orders).
- **Root cause:** Second Class shipping promises 2-day delivery but actually takes 4–6 days — a **200% overrun**. This is a structural SLA mismatch, not a one-off.
- **Late-delivery risk signal** is present at order time on **100% of late orders** (`Late_delivery_risk = 1`), meaning the system already knows before dispatch.
- **Approval gate in action:** the agent proposed 6 flags. The operator **approved 4** and **rejected 2** (Standard Class orders with smaller gaps that didn't warrant escalation).

See `outputs/sample_run.md` for the full transcript with every tool call, result, and approval decision.
