# Phase 2 — DataCo Supply Chain Agent

A Claude tool-calling agent that monitors the DataCo Smart Supply Chain dataset for late and at-risk orders, investigates root causes, and drafts recommended actions gated by human approval.

## Goal

Build a Claude agent that:

1. Continuously scans orders for late or at-risk shipments.
2. Investigates root causes by calling structured tools.
3. Drafts a recommended action and pauses for human approval before marking it executed.

## Stack

- Python 3.10+
- Anthropic API (tool use / function calling)
- Dataset: [DataCo Smart Supply Chain (Kaggle)](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)

## Repo Layout

```
phase2-dataco-agent/
├── data/       # DataCo CSVs (not committed)
├── agent/      # agent script, tool definitions, prompt
├── outputs/    # sample run transcripts and drafted actions
└── README.md
```

## Tools Exposed to the Model

| Tool | Purpose |
| --- | --- |
| `query_orders` | Filter orders by status, region, customer, or delivery-risk flag. |
| `check_inventory` | Look up stock levels for a product or warehouse. |
| `flag_late_shipment` | Mark an order as late and attach investigation notes. |

## Agent Loop

1. **Trigger** — a scheduled or manual run pulls the latest slice of orders from `data/`.
2. **Plan** — the model is prompted to identify late or at-risk orders worth investigating.
3. **Investigate** — the model calls `query_orders` and `check_inventory` iteratively to gather evidence, then `flag_late_shipment` to record findings.
4. **Recommend** — the model drafts a proposed action (expedite, reroute, notify customer, etc.) with a rationale citing the tool results.
5. **Await approval** — the draft is written to `outputs/pending_actions/` and the loop pauses. Nothing executes automatically.
6. **Execute or reject** — a human reviews the draft; on approval the action is logged to `outputs/executed_actions/`. On rejection, feedback is captured for the next run.

## How It Works

`agent/agent.py` is a Claude tool-calling loop. Each turn:

1. Send the running message history to `claude-sonnet-4-6` with the three tool schemas and a system prompt that puts the model in the role of a supply chain operations analyst.
2. If the response `stop_reason` is `tool_use`, execute each `tool_use` block via `dispatch()` in `agent.py` (which calls the real Python functions in `tools.py`), append a `tool_result` block for each, and loop.
3. If the response is anything else (`end_turn`, `max_tokens`, etc.), stop — the last assistant message is the final briefing.
4. Everything — assistant text, tool calls, tool results, approval prompts, and the final briefing — is streamed to `outputs/sample_run.md` as the run happens. The file is truncated at the start of each run, so it always reflects the most recent investigation.

### Tools

| Tool | Purpose | Gated? |
| --- | --- | --- |
| `query_orders` | Filter orders by delivery status, region, category, department, date range, or the `late_delivery_risk` flag. Returns counts, breakdowns, avg real-vs-scheduled shipping days, and a small sample of rows. | No — runs freely. |
| `check_inventory` | Aggregated order-volume view for a product or category (proxy for inventory pressure, since the dataset has no on-hand stock). Returns totals, late-delivery share, top regions, and shipping-mode mix. | No — runs freely. |
| `flag_late_shipment` | Append an order to `outputs/flagged_orders.csv` with timestamp, reason, and full context. | **Yes — human y/n approval required.** |

Note that `category` filters the fine-grained Category Name column (e.g. `Cleats`, `Sporting Goods`) while `department` filters the higher-level Department Name column (e.g. `Fitness`, `Apparel`). The schemas exposed to the model spell this out so the agent picks the right level of the product hierarchy.

### Human-in-the-Loop

Read tools (`query_orders`, `check_inventory`) are free to run — they can't mutate anything. The write tool (`flag_late_shipment`) is different: it produces an operational record that downstream systems act on. Every call prints the proposed order ID and reason to the terminal and blocks on a `y/n` prompt. On `y` the tool runs and the model sees the log record. On `n` the model sees `{"ok": false, "error": "Human operator rejected this flag..."}` and can either revise its rationale or move on to a different order. The model never learns which order gets flagged until the human agrees — the write happens only after a person has looked at what's being proposed. This keeps the LLM on the investigative side of the line and puts a human on anything that touches operational state.

## Running the Agent

```bash
cd phase2-dataco-agent/agent
pip install -r requirements.txt

# Put your Anthropic key in .env (copy .env.example first if needed)
cp .env.example .env  # if you haven't already
# then edit .env and paste your key

# Download the DataCo CSV from Kaggle to ../data/DataCoSupplyChainDataset.csv,
# then run the agent:
python3 agent.py "Investigate late deliveries in the most affected region and recommend actions."
```

Every turn writes to `../outputs/sample_run.md` as it happens, and `flag_late_shipment` will pause for a `y/n` prompt on stdin before executing. Approved flags append to `../outputs/flagged_orders.csv`.

## Definition of Done

- Working `agent/` script that runs end-to-end against the DataCo dataset.
- At least one sample run saved to `outputs/` showing the tool trace and drafted action.
- This README documenting the loop and the approval step.

## Status

Agent implementation complete. Run `agent.py` to produce a sample transcript in `outputs/sample_run.md`.
