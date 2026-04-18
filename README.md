# ShopWave Autonomous Support Agent
### Agentic AI Hackathon 2026 — Submission

---

## What This Does

This agent autonomously resolves customer support tickets for ShopWave (a simulated e-commerce platform). It reads all 20 tickets, reasons about each one, calls the appropriate tools, and resolves or escalates each ticket — without human involvement.

**Tech Stack:**
- Language: Python 3.13
- LLM: Google Gemini 1.5 Flash (via `google-generativeai`)
- Orchestration: Custom ReAct loop (Reason → Act → Observe → Repeat)
- Concurrency: `asyncio.gather()` — all 20 tickets processed simultaneously
- Data: JSON files from the hackathon sample data repo

---

## Project Structure

```
shopwave-agent/
├── main.py              # Entry point — runs all tickets concurrently
├── agent.py             # Core reasoning loop + Gemini integration
├── tools.py             # 8 mock tools with realistic failure simulation
├── tickets.json         # 20 support tickets (from hackathon repo)
├── customers.json       # Customer data
├── orders.json          # Order data
├── products.json        # Product data
├── knowledge-base.md    # Policy FAQs
├── audit_log.json       # Generated on run — full reasoning trail
├── failure_modes.md     # 5 documented failure scenarios
├── architecture.png     # Agent architecture diagram
├── requirements.txt     # Python dependencies
└── .env                 # API key (NOT committed to git)
```

---

## Setup & Run

### 1. Clone and enter the project
```bash
git clone https://github.com/YOUR_USERNAME/hackathon2026-YOUR_NAME
cd hackathon2026-YOUR_NAME
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API key
```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```

### 5. Run the agent
```bash
python main.py
```

That's it. One command. The agent will process all 20 tickets and generate `audit_log.json`.

---

## How It Works (Explained Simply)

### The Reasoning Loop (ReAct pattern)
For each ticket, the agent follows this loop:

```
READ ticket → THINK (what do I need to know?) → CALL tool → OBSERVE result → THINK again → CALL tool → ... → RESOLVE or ESCALATE
```

### Concurrency
All 20 tickets are processed **simultaneously** using `asyncio.gather()`. This means instead of 20 tickets × 2 seconds = 40 seconds, all tickets finish in roughly 2-3 seconds total.

### Tool Chaining (min 3 per ticket)
Example chain for a refund request:
1. `get_customer(email)` → verify the customer exists and their tier
2. `get_order(order_id)` → check order status and delivery date
3. `get_product(product_id)` → check return window
4. `check_refund_eligibility(order_id)` → confirm eligibility
5. `issue_refund(order_id, amount)` → process the refund
6. `send_reply(ticket_id, message)` → notify the customer

### Error Handling
- Every tool call is wrapped in try/except
- Failed tools are retried once with backoff
- After 2 failures, the error is logged and the agent decides what to do next
- The agent never crashes — it always produces an outcome

### Confidence Scoring
The agent scores its confidence (0–1) for each decision:
- ≥ 0.85 → resolve autonomously
- 0.60–0.85 → resolve with a note
- < 0.60 → escalate to human

---

## Audit Log Format

The `audit_log.json` file contains every event:
```json
{
  "run_metadata": { "started_at": "...", "total_duration_seconds": 2.4 },
  "results": [ { "ticket_id": "TKT-001", "status": "resolved", "confidence": 0.95 } ],
  "audit_trail": [
    { "ticket_id": "TKT-001", "event": "ticket_received", "timestamp": "..." },
    { "ticket_id": "TKT-001", "tool": "get_customer", "args": {...}, "result": {...} },
    { "ticket_id": "TKT-001", "event": "ticket_resolved", "outcome": {...} }
  ]
}
```

---

## Judging Criteria Coverage

| Criterion | Implementation |
|-----------|---------------|
| Production Readiness | Error handling, retry logic, env vars, no hardcoded secrets |
| Engineering Depth | asyncio concurrency, realistic mock failures, schema validation |
| Agentic Design | ReAct loop, confidence scoring, knows when NOT to act |
| Evaluation & Self-awareness | Confidence scores, failure detection, dead-letter logging |
| Presentation | Full audit trail, explainable decisions, README |
