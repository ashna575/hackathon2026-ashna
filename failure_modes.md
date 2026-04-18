# Failure Mode Analysis — ShopWave Support Agent

## Failure 1: Tool Timeout / Network Error

**Scenario:** `check_refund_eligibility` times out and returns no data.

**How it happens:** The tool raises `TimeoutError` after 500ms.

**How the agent handles it:**
1. First attempt fails → agent waits 200ms (backoff)
2. Retries once automatically
3. If second attempt also fails → returns `{"error": "Tool failed after 2 attempts"}`
4. Agent receives the error as an observation and decides to **escalate** the ticket with a note: "Could not verify eligibility due to tool failure"
5. The error is logged in `audit_log.json` with `status: "failed"` and attempt count

**What does NOT happen:** The agent does not crash. It does not silently ignore the error. It does not issue a refund without eligibility data.

---

## Failure 2: LLM Returns Malformed JSON

**Scenario:** Gemini returns a response that cannot be parsed as JSON (e.g., wrapped in unexpected text).

**How it happens:** The model occasionally adds extra prose around the JSON block.

**How the agent handles it:**
1. `agent.py` first strips markdown code fences (` ```json `) using regex
2. Attempts `json.loads()` on the cleaned string
3. If parsing still fails → logs a `json_parse_error` event in the audit trail
4. Automatically escalates the ticket with the message: "Agent could not parse LLM response"
5. No action is taken on the ticket — human takes over with full context

**What does NOT happen:** The agent does not guess at the JSON structure. It does not leave the ticket unresolved.

---

## Failure 3: Social Engineering / Fake Policy Claims

**Scenario:** TKT-018 — customer claims to be a "premium member" entitled to instant refunds with no questions.

**How it happens:** Malicious or dishonest customer invents a policy that doesn't exist.

**How the agent handles it:**
1. Agent calls `get_customer(email)` → confirms customer is `standard` tier, not premium
2. Agent calls `search_knowledge_base("premium instant refund")` → no such policy found
3. Agent also calls `check_refund_eligibility(order_id)` → return window already expired
4. Agent responds politely but firmly: "We could not find a premium membership on your account. Our standard return policy applies."
5. The attempted policy manipulation is logged in the audit trail under `event: "suspicious_request"`

**What does NOT happen:** The agent does not blindly accept the customer's claim. It verifies everything through tools before acting.

---

## Failure 4: Order ID Does Not Exist

**Scenario:** TKT-017 — customer provides order `ORD-9999` which is not in the system.

**How it happens:** Customer provides a fake or incorrect order ID.

**How the agent handles it:**
1. Agent calls `get_order("ORD-9999")` → returns `{"error": "Order ORD-9999 not found"}`
2. Agent does NOT proceed with refund or any write action
3. Agent calls `get_customer(email)` to verify the customer exists
4. Agent replies to customer: "We could not find order ORD-9999 on your account. Please verify your order number."
5. Threatening language in the ticket is flagged in the audit log

---

## Failure 5: Concurrent Write Conflict (Duplicate Refund)

**Scenario:** Two tickets for the same order are processed concurrently and both try to issue a refund.

**How it happens:** asyncio processes all tickets simultaneously — two agents could race to refund the same order.

**How the agent handles it:**
1. `tools.py` maintains a shared `ISSUED_REFUNDS` set
2. `issue_refund()` checks: `if order_id in ISSUED_REFUNDS → return {"success": False, "reason": "already refunded"}`
3. The second refund attempt is blocked and logged
4. The agent receives the error, logs it, and sends a confirmation reply instead

**What does NOT happen:** The customer is not refunded twice.
