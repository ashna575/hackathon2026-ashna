# 🤖 ShopWave Autonomous Support Agent
> **Ksolves En(AI)bling Agentic AI Hackathon 2026**

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![LLM](https://img.shields.io/badge/LLM-Groq%20llama--3.3--70b-green)](https://groq.com)
[![Architecture](https://img.shields.io/badge/Architecture-ReAct%20Loop-purple)](https://github.com/ashna575/hackathon2026-ashna)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 The Problem

ShopWave receives hundreds of support tickets daily. Most are repetitive — but **all go to humans**. This agent resolves them **autonomously**, at scale, without human involvement.

---

## 📊 Live Results

| Metric | Result |
|--------|--------|
| ✅ Auto-Resolved | 12 / 20 |
| 🔺 Escalated to Human | 6 / 20 |
| ❓ Requested More Info | 2 / 20 |
| ❌ Errors / Crashes | 0 / 20 |
| ⏱ Total Time | ~3 minutes (concurrent) |

---

## 🎥 Demo Video
[▶ Watch Full Demo on Google Drive](https://drive.google.com/file/d/1eCUPBQscLcYqVTbe1Vv3z3rp-j0O8000/view?usp=sharing)

Demo covers:
- Live processing of all 20 tickets concurrently
- Social engineering detection (TKT-018)
- Tool failure and recovery (TKT-003)
- Audit log walkthrough showing full reasoning trail

---

## 🏗️ Architecture

```
tickets.json (20 tickets)
       ↓
  asyncio.gather() — all tickets start simultaneously
       ↓
  ┌─────────────────────────────────┐
  │      ReAct Reasoning Loop       │
  │  Think → Act → Observe → Repeat │
  └─────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────────────┐
  │                  8 MOCK TOOLS                   │
  │  READ: get_order │ get_customer │ get_product   │
  │         search_knowledge_base                   │
  │  WRITE: check_eligibility │ issue_refund        │
  │          send_reply │ escalate                  │
  └─────────────────────────────────────────────────┘
       ↓
  Confidence Check
  ├── ≥ 85% → Auto-resolve + send_reply()
  ├── 60-85% → Resolve with note
  └── < 60% → escalate() to human
       ↓
  audit_log.json (full reasoning trail)
```

**See full architecture diagram:** [architecture.pdf](architecture.pdf)

---

## 🛡️ Resilience — How the Agent Handles Failures

### Failure 1: Tool Timeout
```
check_refund_eligibility("ORD-1003") → TimeoutError
→ Agent retries once (200ms backoff)
→ Fails again → logs error → escalates with full context
→ Never crashes
```

### Failure 2: Malformed Data
```
Tool returns {status: null, data: undefined}
→ Agent catches ValueError
→ Continues with available information
→ Makes conservative decision (escalate)
```

### Failure 3: Social Engineering (TKT-018)
```
Customer claims "premium membership — instant refund"
→ get_customer() → tier: "standard" (not premium)
→ search_knowledge_base() → no such policy exists
→ Agent declines politely, logs suspicious request
→ Never blindly trusts customer claims
```

### Failure 4: Non-existent Order (TKT-017)
```
Customer provides fake order ORD-9999
→ get_order("ORD-9999") → {"error": "not found"}
→ Agent does NOT proceed with refund
→ Asks customer to verify order number
```

### Failure 5: Duplicate Refund Protection
```
Two concurrent tickets try to refund same order
→ ISSUED_REFUNDS set blocks second attempt
→ Returns {"success": False, "reason": "already refunded"}
→ Customer never refunded twice
```

---

## 🧠 Agentic Design

### Why ReAct Loop?
Every decision is **traceable and explainable**. No black-box outputs. Judges can open `audit_log.json` and see exactly why the agent made every decision.

### Tool Chaining (min 3 per ticket)
Example for a refund request:
```
1. get_customer(email)         → verify customer exists + tier
2. get_order(order_id)         → check status + delivery date  
3. get_product(product_id)     → check return window
4. check_refund_eligibility()  → confirm eligibility
5. issue_refund()              → process refund
6. send_reply()                → notify customer
```

### Confidence Scoring
```python
≥ 0.85 → resolve autonomously
0.60 - 0.85 → resolve with a note in reply
< 0.60 → escalate to human agent
```

### Safety Guards
- `issue_refund()` is **blocked** unless `check_refund_eligibility()` was called first
- Suspicious requests are flagged and logged
- All write actions are logged as irreversible

---

## 📁 Project Structure

```
hackathon2026-ashna/
├── main.py              # Entry point — concurrent batch processing
├── agent.py             # ReAct loop + LLM integration
├── tools.py             # 8 mock tools with realistic failures
├── tickets.json         # 20 support tickets (hackathon data)
├── customers.json       # Customer profiles
├── orders.json          # Order records
├── products.json        # Product catalog
├── knowledge-base.md    # Policy & FAQ data
├── audit_log.json       # ← Generated on run (full reasoning trail)
├── dead_letter_queue.json  # Failed tickets (never lost)
├── failure_modes.md     # 5 failure scenarios documented
├── architecture.pdf     # Agent architecture diagram
├── ShopWave_Agent.pptx  # Presentation slides
├── requirements.txt     # Dependencies
└── .gitignore           # Hides .env and venv
```

---

## ⚙️ Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/ashna575/hackathon2026-ashna
cd hackathon2026-ashna
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set API key (get free key at console.groq.com)
```bash
# Windows:
$env:GROQ_API_KEY="enter API key "

# Mac/Linux:
export GROQ_API_KEY="enter API here "
```

### 5. Run the agent ← ONE COMMAND
```bash
python main.py
```

Agent processes all 20 tickets and generates `audit_log.json` automatically.

---

## 📋 Audit Log Format

Every tool call, reasoning step and outcome is logged:

```json
{
  "run_metadata": {
    "started_at": "2026-04-18T03:17:48",
    "total_duration_seconds": 176.81,
    "tickets_processed": 20,
    "concurrency": "batches of 3 via asyncio.gather"
  },
  "results": [
    {
      "ticket_id": "TKT-001",
      "status": "resolved",
      "confidence": 0.9,
      "tools_called": ["get_customer", "get_order", "check_refund_eligibility", "send_reply"],
      "summary": "Refund request denied due to expired return window"
    }
  ],
  "audit_trail": [
    {"event": "ticket_received", "ticket_id": "TKT-001"},
    {"tool": "get_customer", "args": {"email": "..."}, "result": {...}},
    {"event": "agent_plan", "thinking": "Customer is requesting refund..."},
    {"event": "ticket_resolved", "outcome": {...}}
  ]
}
```

---



## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13 |
| LLM | Groq API — llama-3.3-70b-versatile |
| Concurrency | asyncio.gather() |
| Architecture | Custom ReAct reasoning loop |
| Mock Tools | 8 tools with timeout/503/malformed failures |
| Logging | JSON audit trail with full reasoning |

---

*Built for Ksolves En(AI)bling Agentic AI Hackathon 2026 — "Don't write code. Engineer Reasoning."*