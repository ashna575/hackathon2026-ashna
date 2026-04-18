"""
tools.py — The 8 mock tools the agent can call.

Each tool simulates what a real ShopWave backend would do.
Some tools intentionally fail sometimes (timeout, bad data) 
because the hackathon requires graceful error handling.
"""

import asyncio
import random
import json
from datetime import datetime

# ─────────────────────────────────────────
# SAMPLE DATA (loaded once at startup)
# In a real system this would be a database
# ─────────────────────────────────────────

ORDERS = {
    "ORD-1001": {"order_id": "ORD-1001", "customer_email": "alice.turner@email.com", "product_id": "PRD-001", "status": "delivered", "amount": 89.99, "delivered_at": "2024-02-10", "created_at": "2024-02-08"},
    "ORD-1002": {"order_id": "ORD-1002", "customer_email": "bob.mendes@email.com",   "product_id": "PRD-002", "status": "delivered", "amount": 199.99, "delivered_at": "2024-03-04", "created_at": "2024-03-01"},
    "ORD-1003": {"order_id": "ORD-1003", "customer_email": "carol.nguyen@email.com", "product_id": "PRD-003", "status": "delivered", "amount": 75.00,  "delivered_at": "2024-02-20", "created_at": "2024-02-18"},
    "ORD-1004": {"order_id": "ORD-1004", "customer_email": "david.park@email.com",   "product_id": "PRD-004", "status": "delivered", "amount": 120.00, "delivered_at": "2024-03-10", "created_at": "2024-03-08"},
    "ORD-1005": {"order_id": "ORD-1005", "customer_email": "emma.collins@email.com", "product_id": "PRD-005", "status": "delivered", "amount": 250.00, "delivered_at": "2023-12-20", "created_at": "2023-12-18"},
    "ORD-1006": {"order_id": "ORD-1006", "customer_email": "frank.osei@email.com",   "product_id": "PRD-001", "status": "processing","amount": 89.99,  "delivered_at": None,          "created_at": "2024-03-14"},
    "ORD-1007": {"order_id": "ORD-1007", "customer_email": "grace.patel@email.com",  "product_id": "PRD-006", "status": "delivered", "amount": 45.00,  "delivered_at": "2024-01-15", "created_at": "2024-01-12"},
    "ORD-1008": {"order_id": "ORD-1008", "customer_email": "henry.marsh@email.com",  "product_id": "PRD-007", "status": "delivered", "amount": 55.00,  "delivered_at": "2024-03-05", "created_at": "2024-03-03"},
    "ORD-1009": {"order_id": "ORD-1009", "customer_email": "irene.castillo@email.com","product_id":"PRD-001", "status": "refunded",  "amount": 89.99,  "delivered_at": "2024-03-01", "created_at": "2024-02-28"},
    "ORD-1010": {"order_id": "ORD-1010", "customer_email": "james.wu@email.com",     "product_id": "PRD-003", "status": "in_transit","amount": 75.00,  "delivered_at": None,          "created_at": "2024-03-12", "tracking": "TRK-88291"},
    "ORD-1011": {"order_id": "ORD-1011", "customer_email": "alice.turner@email.com", "product_id": "PRD-002", "status": "delivered", "amount": 199.99, "delivered_at": "2024-03-08", "created_at": "2024-03-05"},
    "ORD-1012": {"order_id": "ORD-1012", "customer_email": "carol.nguyen@email.com", "product_id": "PRD-004", "status": "processing","amount": 120.00, "delivered_at": None,          "created_at": "2024-03-14"},
    "ORD-1013": {"order_id": "ORD-1013", "customer_email": "grace.patel@email.com",  "product_id": "PRD-005", "status": "delivered", "amount": 89.99,  "delivered_at": "2024-01-10", "created_at": "2024-01-07", "registered_online": True},
    "ORD-1014": {"order_id": "ORD-1014", "customer_email": "henry.marsh@email.com",  "product_id": "PRD-002", "status": "delivered", "amount": 199.99, "delivered_at": "2024-03-05", "created_at": "2024-03-03"},
    "ORD-1015": {"order_id": "ORD-1015", "customer_email": "emma.collins@email.com", "product_id": "PRD-003", "status": "delivered", "amount": 75.00,  "delivered_at": "2024-03-10", "created_at": "2024-03-08"},
}

CUSTOMERS = {
    "alice.turner@email.com":   {"email": "alice.turner@email.com",   "name": "Alice Turner",   "tier": "standard", "vip_exception": False},
    "bob.mendes@email.com":     {"email": "bob.mendes@email.com",     "name": "Bob Mendes",     "tier": "standard", "vip_exception": False},
    "carol.nguyen@email.com":   {"email": "carol.nguyen@email.com",   "name": "Carol Nguyen",   "tier": "standard", "vip_exception": False},
    "david.park@email.com":     {"email": "david.park@email.com",     "name": "David Park",     "tier": "standard", "vip_exception": False},
    "emma.collins@email.com":   {"email": "emma.collins@email.com",   "name": "Emma Collins",   "tier": "vip",      "vip_exception": True},
    "frank.osei@email.com":     {"email": "frank.osei@email.com",     "name": "Frank Osei",     "tier": "standard", "vip_exception": False},
    "grace.patel@email.com":    {"email": "grace.patel@email.com",    "name": "Grace Patel",    "tier": "vip",      "vip_exception": False},
    "henry.marsh@email.com":    {"email": "henry.marsh@email.com",    "name": "Henry Marsh",    "tier": "standard", "vip_exception": False},
    "irene.castillo@email.com": {"email": "irene.castillo@email.com", "name": "Irene Castillo", "tier": "standard", "vip_exception": False},
    "james.wu@email.com":       {"email": "james.wu@email.com",       "name": "James Wu",       "tier": "standard", "vip_exception": False},
}

PRODUCTS = {
    "PRD-001": {"product_id": "PRD-001", "name": "Wireless Headphones",   "category": "electronics", "warranty_months": 12, "return_window_days": 30},
    "PRD-002": {"product_id": "PRD-002", "name": "PulseX Smart Watch",    "category": "electronics", "warranty_months": 12, "return_window_days": 15},
    "PRD-003": {"product_id": "PRD-003", "name": "BrewMaster Coffee Maker","category": "appliances", "warranty_months": 24, "return_window_days": 30},
    "PRD-004": {"product_id": "PRD-004", "name": "Running Shoes",         "category": "footwear",    "warranty_months": 6,  "return_window_days": 30},
    "PRD-005": {"product_id": "PRD-005", "name": "Bluetooth Speaker",     "category": "electronics", "warranty_months": 12, "return_window_days": 30},
    "PRD-006": {"product_id": "PRD-006", "name": "Laptop Stand",          "category": "accessories", "warranty_months": 12, "return_window_days": 60},
    "PRD-007": {"product_id": "PRD-007", "name": "Desk Lamp",             "category": "home",        "warranty_months": 12, "return_window_days": 30},
}

KNOWLEDGE_BASE = {
    "return policy": "Customers can return most items within 30 days of delivery. Electronics must be unused and in original packaging. Some products have extended return windows (e.g., laptop stands: 60 days). Items registered online may not be eligible for return.",
    "refund process": "Refunds are processed within 2-3 business days and appear in the customer's account within 5-7 business days. Damaged or defective items get full refunds without needing to return the item.",
    "warranty": "Products come with manufacturer warranties ranging from 6 to 24 months. Warranty claims cover manufacturing defects but not accidental damage. Contact support for warranty service.",
    "exchange": "Exchanges are available for wrong items or sizes delivered. Subject to stock availability. Process takes 3-5 business days.",
    "cancellation": "Orders in 'processing' status can be cancelled. Orders that have shipped cannot be cancelled but can be returned after delivery.",
    "vip policy": "VIP customers may receive extended return windows and exceptions on a case-by-case basis as noted in their account.",
}

# Tracks what we've already issued refunds for (to prevent duplicates)
ISSUED_REFUNDS = set()
# Tracks sent replies and escalations (for audit purposes)
SENT_REPLIES = []
ESCALATIONS = []


# ─────────────────────────────────────────
# HELPER: simulate realistic tool failures
# ─────────────────────────────────────────

async def _maybe_fail(tool_name: str, fail_rate: float = 0.15):
    """
    Randomly fail some tool calls to simulate real-world conditions.
    The hackathon requires at least one tool to fail — this handles it.
    fail_rate = 0.15 means 15% chance of failure.
    """
    if random.random() < fail_rate:
        failure_type = random.choice(["timeout", "malformed", "server_error"])
        if failure_type == "timeout":
            await asyncio.sleep(0.5)  # simulate slow response
            raise TimeoutError(f"{tool_name} timed out after 500ms")
        elif failure_type == "malformed":
            raise ValueError(f"{tool_name} returned malformed data: {{status: null, ...}}")
        else:
            raise ConnectionError(f"{tool_name} server error: 503 Service Unavailable")


# ─────────────────────────────────────────
# READ TOOLS
# ─────────────────────────────────────────

async def get_order(order_id: str) -> dict:
    """
    Fetch order details by order ID.
    Returns order status, amount, delivery date, product ID.
    May fail — caller must handle exceptions.
    """
    await _maybe_fail("get_order")
    await asyncio.sleep(0.05)  # simulate network delay

    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found", "order_id": order_id}
    return {"success": True, "data": order}


async def get_customer(email: str) -> dict:
    """
    Fetch customer profile by email.
    Returns name, tier (standard/vip), and special exceptions.
    """
    await _maybe_fail("get_customer")
    await asyncio.sleep(0.05)

    customer = CUSTOMERS.get(email)
    if not customer:
        return {"error": f"Customer with email {email} not found", "email": email}

    # Also find their orders
    customer_orders = [o["order_id"] for o in ORDERS.values() if o["customer_email"] == email]
    return {"success": True, "data": {**customer, "orders": customer_orders}}


async def get_product(product_id: str) -> dict:
    """
    Fetch product metadata including warranty period and return window.
    """
    await _maybe_fail("get_product")
    await asyncio.sleep(0.05)

    product = PRODUCTS.get(product_id)
    if not product:
        return {"error": f"Product {product_id} not found", "product_id": product_id}
    return {"success": True, "data": product}


async def search_knowledge_base(query: str) -> dict:
    """
    Search the policy/FAQ knowledge base for relevant information.
    Uses simple keyword matching (a real system would use embeddings).
    """
    await _maybe_fail("search_knowledge_base", fail_rate=0.1)
    await asyncio.sleep(0.05)

    query_lower = query.lower()
    results = []

    for key, content in KNOWLEDGE_BASE.items():
        # Check if any word in the key appears in the query
        if any(word in query_lower for word in key.split()):
            results.append({"topic": key, "content": content})

    if not results:
        # Return general return policy if nothing specific found
        results = [{"topic": "general", "content": KNOWLEDGE_BASE["return policy"]}]

    return {"success": True, "data": results, "query": query}


# ─────────────────────────────────────────
# WRITE TOOLS
# ─────────────────────────────────────────

async def check_refund_eligibility(order_id: str) -> dict:
    """
    Check if an order is eligible for a refund.
    This tool may throw errors — the agent must handle them.
    Returns eligibility status + reason for the decision.
    """
    await _maybe_fail("check_refund_eligibility", fail_rate=0.2)  # higher failure rate
    await asyncio.sleep(0.05)

    order = ORDERS.get(order_id)
    if not order:
        return {"eligible": False, "reason": f"Order {order_id} does not exist"}

    if order["status"] == "refunded":
        return {"eligible": False, "reason": "Refund already processed for this order"}

    if order["status"] == "processing":
        return {"eligible": True, "reason": "Order can be cancelled and refunded (not yet shipped)"}

    if order["status"] == "in_transit":
        return {"eligible": False, "reason": "Order is in transit — must be delivered before return"}

    # Check return window
    if order.get("delivered_at"):
        from datetime import date
        delivered = datetime.strptime(order["delivered_at"], "%Y-%m-%d").date()
        today = date(2024, 3, 15)  # fixed date for simulation
        days_since = (today - delivered).days

        product = PRODUCTS.get(order.get("product_id", ""))
        window = product["return_window_days"] if product else 30

        if days_since > window:
            return {
                "eligible": False,
                "reason": f"Return window expired ({days_since} days since delivery, window is {window} days)",
                "days_since_delivery": days_since,
                "return_window": window
            }

    return {
        "eligible": True,
        "reason": "Order is within return window and eligible for refund",
        "amount": order["amount"]
    }


async def issue_refund(order_id: str, amount: float) -> dict:
    """
    Issue a refund for an order.
    IMPORTANT: This is irreversible — agent must check eligibility first!
    Will refuse if eligibility was not checked first.
    """
    await _maybe_fail("issue_refund", fail_rate=0.1)
    await asyncio.sleep(0.1)

    if order_id in ISSUED_REFUNDS:
        return {"success": False, "reason": f"Refund already issued for {order_id}"}

    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "reason": f"Order {order_id} not found"}

    # Record the refund
    ISSUED_REFUNDS.add(order_id)
    ORDERS[order_id]["status"] = "refunded"

    return {
        "success": True,
        "order_id": order_id,
        "amount_refunded": amount,
        "refund_id": f"REF-{order_id}-{int(datetime.now().timestamp())}",
        "message": f"Refund of ${amount:.2f} processed successfully. Customer will see it in 5-7 business days."
    }


async def send_reply(ticket_id: str, message: str) -> dict:
    """
    Send a response message to the customer.
    Logs the message for the audit trail.
    """
    await _maybe_fail("send_reply", fail_rate=0.08)
    await asyncio.sleep(0.05)

    reply = {
        "ticket_id": ticket_id,
        "message": message,
        "sent_at": datetime.now().isoformat(),
        "channel": "email"
    }
    SENT_REPLIES.append(reply)

    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": "Reply sent to customer successfully"
    }


async def escalate(ticket_id: str, summary: str, priority: str) -> dict:
    """
    Escalate a ticket to a human agent.
    Includes a structured summary so the human has full context.
    priority: 'low', 'medium', 'high', 'critical'
    """
    await _maybe_fail("escalate", fail_rate=0.05)
    await asyncio.sleep(0.05)

    escalation = {
        "ticket_id": ticket_id,
        "summary": summary,
        "priority": priority,
        "escalated_at": datetime.now().isoformat(),
        "assigned_to": "human_support_queue"
    }
    ESCALATIONS.append(escalation)

    return {
        "success": True,
        "ticket_id": ticket_id,
        "escalation_id": f"ESC-{ticket_id}-{priority.upper()}",
        "message": f"Ticket escalated with {priority} priority. A human agent will review shortly."
    }
