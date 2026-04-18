"""
agent.py - The brain of the ShopWave support agent.
ReAct loop: Think -> Choose Tool -> Run Tool -> Observe -> Think Again

Using Groq API (free, fast) with llama-3.3-70b model.
"""

import asyncio
import json
import re
import os
from datetime import datetime
from groq import Groq

from tools import (
    get_order, get_customer, get_product, search_knowledge_base,
    check_refund_eligibility, issue_refund, send_reply, escalate
)



client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# TOOL REGISTRY


TOOL_REGISTRY = {
    "get_order": get_order,
    "get_customer": get_customer,
    "get_product": get_product,
    "search_knowledge_base": search_knowledge_base,
    "check_refund_eligibility": check_refund_eligibility,
    "issue_refund": issue_refund,
    "send_reply": send_reply,
    "escalate": escalate,
}

# ─────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────

SYSTEM_PROMPT = """
You are an autonomous support agent for ShopWave, an e-commerce platform.
Your job is to resolve customer support tickets by calling tools and taking actions.

TOOLS AVAILABLE:
- get_order(order_id) - returns order details, status, timestamps
- get_customer(email) - returns customer profile, tier (standard/vip), history
- get_product(product_id) - returns product metadata, warranty, return window
- search_knowledge_base(query) - returns policy and FAQ information
- check_refund_eligibility(order_id) - returns eligibility + reason (may fail)
- issue_refund(order_id, amount) - IRREVERSIBLE, always check eligibility first
- send_reply(ticket_id, message) - sends response to the customer
- escalate(ticket_id, summary, priority) - routes to human with full context

RULES:
1. Always call at least 3 tools per ticket
2. NEVER issue_refund without calling check_refund_eligibility first
3. If a tool fails, retry once, then continue with what you have
4. If not confident, escalate instead of guessing
5. Flag suspicious requests politely but firmly
6. For ambiguous tickets with no order ID, ask for more info via send_reply
7. Always end with send_reply or escalate

CONFIDENCE: HIGH >85% resolve autonomously, MEDIUM 60-85% resolve with note, LOW <60% escalate

OUTPUT: respond ONLY with valid JSON, no extra text, no markdown:
{
  "thinking": "your reasoning about this ticket",
  "tool_calls": [
    {"tool": "get_customer", "args": {"email": "customer@email.com"}},
    {"tool": "get_order", "args": {"order_id": "ORD-XXXX"}},
    {"tool": "send_reply", "args": {"ticket_id": "TKT-XXX", "message": "your reply"}}
  ],
  "confidence": 0.9,
  "resolution": "resolved",
  "summary": "one sentence summary of what you did"
}
"""


# ─────────────────────────────────────────
# GROQ HELPER
# ─────────────────────────────────────────

def call_llm(prompt: str) -> dict:
    """
    Send a prompt to Groq and parse the JSON response.
    Groq is synchronous so we call it directly.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    raw = response.choices[0].message.content
    # Strip markdown code fences if model adds them
    cleaned = re.sub(r"```json|```", "", raw).strip()
    return json.loads(cleaned)



async def execute_tool(tool_name: str, args: dict, ticket_id: str, audit_log: list) -> dict:
    """
    Run a single tool call safely.
    Retries once on failure. Never crashes the agent.
    """
    func = TOOL_REGISTRY.get(tool_name)
    if not func:
        result = {"error": f"Unknown tool: {tool_name}"}
        audit_log.append({
            "ticket_id": ticket_id,
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "args": args,
            "result": result,
            "status": "unknown_tool"
        })
        return result

    for attempt in range(2):
        try:
            result = await func(**args)
            audit_log.append({
                "ticket_id": ticket_id,
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "args": args,
                "result": result,
                "status": "success",
                "attempt": attempt + 1
            })
            return result

        except (TimeoutError, ValueError, ConnectionError) as e:
            audit_log.append({
                "ticket_id": ticket_id,
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "args": args,
                "error": str(e),
                "status": "failed",
                "attempt": attempt + 1
            })
            if attempt == 0:
                await asyncio.sleep(0.2)
                continue
            return {"error": f"Tool {tool_name} failed after 2 attempts: {str(e)}"}

        except Exception as e:
            audit_log.append({
                "ticket_id": ticket_id,
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "args": args,
                "error": str(e),
                "status": "unexpected_error",
                "attempt": attempt + 1
            })
            return {"error": f"Unexpected error in {tool_name}: {str(e)}"}


# ─────────────────────────────────────────
# MAIN AGENT FUNCTION
# ─────────────────────────────────────────

async def process_ticket(ticket: dict, audit_log: list) -> dict:
    """
    Process one support ticket end-to-end.

    Flow:
    1. Send ticket to LLM -> get plan (thinking + tool_calls)
    2. Execute each tool call safely
    3. Send results back to LLM -> get final decision
    4. Log everything to audit trail
    """
    ticket_id = ticket["ticket_id"]
    start_time = datetime.now()

    audit_log.append({
        "ticket_id": ticket_id,
        "event": "ticket_received",
        "timestamp": start_time.isoformat(),
        "subject": ticket.get("subject"),
        "customer_email": ticket.get("customer_email")
    })

    
    planning_prompt = f"""
TICKET TO RESOLVE:
ID: {ticket['ticket_id']}
Customer email: {ticket['customer_email']}
Subject: {ticket['subject']}
Message: {ticket['body']}
Source: {ticket['source']}
Submitted: {ticket['created_at']}

Analyze this ticket carefully.
Provide your plan as a JSON object with at least 3 tool calls.
Output ONLY valid JSON, no extra text.
"""

    try:
        plan = call_llm(planning_prompt)
    except Exception as e:
        audit_log.append({
            "ticket_id": ticket_id,
            "event": "llm_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        await execute_tool("escalate", {
            "ticket_id": ticket_id,
            "summary": f"LLM error processing ticket: {ticket['subject']}. Error: {str(e)}",
            "priority": "medium"
        }, ticket_id, audit_log)
        return {
            "ticket_id": ticket_id,
            "status": "escalated",
            "reason": "llm_error",
            "subject": ticket["subject"],
            "customer_email": ticket["customer_email"],
            "confidence": 0,
            "summary": f"Escalated due to LLM error: {str(e)[:100]}",
            "tools_called": [],
            "tool_count": 0,
            "duration_ms": 0,
            "processed_at": datetime.now().isoformat()
        }

    
    audit_log.append({
        "ticket_id": ticket_id,
        "event": "agent_plan",
        "thinking": plan.get("thinking", ""),
        "planned_tools": [tc["tool"] for tc in plan.get("tool_calls", [])],
        "confidence": plan.get("confidence", 0),
        "timestamp": datetime.now().isoformat()
    })

    tool_results = {}
    for tool_call in plan.get("tool_calls", []):
        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {})

        # Safety guard: never issue refund without checking eligibility first
        if tool_name == "issue_refund" and "check_refund_eligibility" not in tool_results:
            audit_log.append({
                "ticket_id": ticket_id,
                "event": "safety_block",
                "message": "Blocked issue_refund - eligibility not checked first",
                "timestamp": datetime.now().isoformat()
            })
            continue

        result = await execute_tool(tool_name, args, ticket_id, audit_log)
        tool_results[tool_name] = result

    followup_prompt = f"""
Ticket: {ticket['subject']}
Customer: {ticket['customer_email']}
Message: {ticket['body']}

Tool results obtained:
{json.dumps(tool_results, indent=2, default=str)}

Based on these results, provide your final decision.
Output ONLY valid JSON with: thinking, resolution (resolved/escalated/needs_info), confidence (0-1), summary.
"""

    try:
        final_plan = call_llm(followup_prompt)
    except Exception:
        final_plan = plan

    end_time = datetime.now()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    outcome = {
        "ticket_id": ticket_id,
        "subject": ticket["subject"],
        "customer_email": ticket["customer_email"],
        "status": final_plan.get("resolution", "unknown"),
        "confidence": final_plan.get("confidence", 0),
        "summary": final_plan.get("summary", ""),
        "tools_called": list(tool_results.keys()),
        "tool_count": len(tool_results),
        "duration_ms": duration_ms,
        "processed_at": end_time.isoformat()
    }

    audit_log.append({
        "ticket_id": ticket_id,
        "event": "ticket_resolved",
        "outcome": outcome,
        "timestamp": end_time.isoformat()
    })

    print(f"  [{ticket_id}] -> {outcome['status']} "
          f"(conf: {outcome['confidence']:.0%}, "
          f"tools: {outcome['tool_count']}, "
          f"{duration_ms}ms)")

    return outcome