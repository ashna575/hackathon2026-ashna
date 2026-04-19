# ShopWave Autonomous Support Agent
### Agentic AI Hackathon 2026 — Ksolves En(AI)bling

---

## What This Does

This agent autonomously resolves customer support tickets for ShopWave (a simulated e-commerce platform). It reads all 20 tickets, reasons about each one, calls the appropriate tools, and resolves or escalates each ticket — without human involvement.

**Results:** 12 resolved ✅ | 6 escalated 🔺 | 2 needs info ❓ | 0 errors ❌

**Tech Stack:**
- Language: Python 3.13
- LLM: Groq API (llama-3.3-70b-versatile) — fast, free tier
- Orchestration: Custom ReAct loop (Reason → Act → Observe → Repeat)
- Concurrency: `asyncio.gather()` — tickets processed in concurrent batches
- Data: JSON files from the hackathon sample data repo

---

## Project Structure

```
hackathon-agent/
├── main.py              # Entry point — runs all tickets concurrently
├── agent.py             # Core reasoning loop + Groq LLM integration
├── tools.py             # 8 mock tools with realistic failure simulation
├── tickets.json         # 20 support tickets (from hackathon repo)
├── customers.json       # Customer data
├── orders.json          # Order data
├── products.json        # Product data
├── knowledge-base.md    # Policy FAQs
├── audit_log.json       # Generated on run — full reasoning trail
├── failure_modes.md     # 5 documented failure scenarios
├── architecture.pdf     # Agent architecture diagram
├── requirements.txt     # Python dependencies
└── .gitignore           # Hides .env and venv from git
```

---

## Setup & Run

### 1. Clone and enter the project
```bash
git clone https://github.com/ashna575/hackathon2026-ashna
cd hackathon2026-ashna
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

### 4. Set your Groq API key
Get a free key at: https://console.groq.com

```bash
# Windows PowerShell:
$env:GROQ_API_KEY="your_groq_key_here"

# Mac/Linux:
export GROQ_API_KEY="your_groq_key_here"
```

### 5. Run the agent
```bash
python main.py
```

That's it. One command. The agent processes all 20 tickets and generates `audit_log.json`.

---

## How It Works

### The Reasoning Loop (ReAct pattern)
For each ticket, the agent follows this loop:

```
READ ticket → THINK → CALL tool → OBSERVE result → THINK → CALL tool → ... → RESOLVE or ESCALATE
```

### Concurrency
Tickets are processed in **concurrent batches** using `asyncio.gather()`.
Multiple tickets are handled simultaneously — not one by one.

### Tool Chaining (min 3 per ticket)
Example chain for a refund request:
1. `get_customer(email)` → verify customer exists and their tier
2. `get_order(order_id)` → check order status and delivery date
3. `get_product(product_id)` → check return window
4. `check_refund_eligibility(order_id)` → confirm eligibility
5. `issue_refund(order_id, amount)` → process the refund
6. `send_reply(ticket_id, message)` → notify the customer

### Error Handling
- Every tool call is wrapped in try/except
- Failed tools are retried once with 200ms backoff
- After 2 failures, the error is logged and agent decides next step
- The agent never crashes — it always produces an outcome
- Duplicate refund protection via shared ISSUED_REFUNDS set

### Confidence Scoring
The agent scores its own confidence (0–1) for each decision:
- ≥ 0.85 → resolve autonomously
- 0.60–0.85 → resolve with a note in the reply
- < 0.60 → escalate to human agent

### Social Engineering Detection
The agent catches manipulation attempts (TKT-018) by:
1. Verifying customer tier via `get_customer()`
2. Searching knowledge base for claimed policies
3. Declining politely if claims don't match records

---

## Audit Log Format

The `audit_log.json` covers all 20 tickets with full reasoning:
```json
{
  "run_metadata": {
    "started_at": "2026-04-18T03:17:48",
    "total_duration_seconds": 176.81,
    "tickets_processed": 20
  },
  "results": [
    { "ticket_id": "TKT-001", "status": "resolved", "confidence": 0.9 }
  ],
  "audit_trail": [
    { "ticket_id": "TKT-001", "event": "ticket_received", "timestamp": "..." },
    { "ticket_id": "TKT-001", "tool": "get_customer", "args": {...}, "result": {...} },
    { "ticket_id": "TKT-001", "event": "ticket_resolved", "outcome": {...} }
  ]
}
```

---

## Judging Criteria Coverage

| Criterion | Points | Implementation |
|-----------|--------|---------------|
| Production Readiness | 30 | Error handling, retry logic, env vars, no hardcoded secrets, duplicate protection |
| Engineering Depth | 30 | asyncio concurrency, realistic mock failures (timeout/malformed/503), schema validation |
| Agentic Design | 10 | ReAct loop, confidence scoring, safety guards, knows when NOT to act |
| Evaluation & Self-awareness | 10 | Confidence scores, failure detection, dead-letter logging, social engineering detection |
| Presentation & Deployment | 20 | Full audit trail, explainable decisions, architecture diagram, this README |

---

## Key Design Decisions

**Why Groq?** Fast inference, generous free tier, no rate limit issues for concurrent processing.

**Why ReAct loop?** Industry standard for agentic systems — every decision is traceable and explainable.

**Why asyncio?** Allows true concurrency without threads — safe, predictable, production-grade.

**Why batch processing?** Respects API rate limits while maintaining concurrency within each batch.







### Demo Video

[Watch Full Demo on Google Drive](https://drive.google.com/file/d/1eCUPBQscLcYqVTbe1Vv3z3rp-j0O8000/view?usp=drive_link)

Demo shows:
- All 20 tickets processed concurrently in batches
- 12 auto-resolved, 6 escalated, 2 needs info, 0 errors
- Live audit log generation
- Social engineering detection (TKT-018)
- Tool failure recovery (TKT-003)