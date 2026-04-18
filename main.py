"""
main.py - Entry point for the ShopWave Support Agent.
Run with: python main.py
Processes tickets one by one with small delay to respect rate limits.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from agent import process_ticket


def load_tickets(path="tickets.json"):
    with open(path, "r") as f:
        return json.load(f)


async def run_agent():
    print("=" * 60)
    print("  ShopWave Autonomous Support Agent")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tickets = load_tickets("tickets.json")
    print(f"\n Loaded {len(tickets)} tickets\n")

    audit_log = []
    results = []
    start_time = datetime.now()

    for i, ticket in enumerate(tickets):
        print(f"  Processing {ticket['ticket_id']} ({i+1}/{len(tickets)})...")
        try:
            result = await process_ticket(ticket, audit_log)
            results.append(result)
        except Exception as e:
            results.append({"ticket_id": ticket["ticket_id"], "status": "error",
                            "subject": ticket["subject"], "customer_email": ticket["customer_email"],
                            "confidence": 0, "summary": str(e), "tools_called": [],
                            "tool_count": 0, "duration_ms": 0,
                            "processed_at": datetime.now().isoformat()})
        # Small delay between tickets to avoid rate limits
        if i < len(tickets) - 1:
            time.sleep(5)

    end_time = datetime.now()
    total_seconds = (end_time - start_time).total_seconds()

    # Save audit log
    audit_output = {
        "run_metadata": {
            "started_at": start_time.isoformat(),
            "finished_at": end_time.isoformat(),
            "total_duration_seconds": round(total_seconds, 2),
            "tickets_processed": len(tickets),
        },
        "results": results,
        "audit_trail": audit_log
    }
    with open("audit_log.json", "w") as f:
        json.dump(audit_output, f, indent=2, default=str)

    # Save dead letter queue
    failed = [r for r in results if r.get("status") in ["error", "escalated"]]
    with open("dead_letter_queue.json", "w") as f:
        json.dump({"failed_tickets": failed, "timestamp": datetime.now().isoformat()}, f, indent=2)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    resolved   = sum(1 for r in results if r.get("status") == "resolved")
    escalated  = sum(1 for r in results if r.get("status") == "escalated")
    needs_info = sum(1 for r in results if r.get("status") == "needs_info")
    errors     = sum(1 for r in results if r.get("status") == "error")

    print(f"\n  Total tickets : {len(tickets)}")
    print(f"  Resolved      : {resolved}")
    print(f"  Escalated     : {escalated}")
    print(f"  Needs info    : {needs_info}")
    print(f"  Errors        : {errors}")
    print(f"\n  Total time    : {total_seconds:.2f}s")
    print(f"  Audit log     : audit_log.json")
    print("\n" + "=" * 60)
    print("\n  TICKET-BY-TICKET BREAKDOWN\n")

    for r in results:
        icon = {"resolved": "[OK]", "escalated": "[ESC]",
                "needs_info": "[INFO]", "error": "[ERR]"}.get(r.get("status"), "[?]")
        conf = r.get("confidence", 0)
        print(f"  {icon} {r['ticket_id']} | {r.get('status','?'):10} | "
              f"conf: {conf:.0%} | {r.get('summary','')[:55]}")

    print("\nDone! Check audit_log.json for full reasoning trail.\n")


if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set!")
        print("Run: $env:GROQ_API_KEY='your_key_here'")
        exit(1)
    asyncio.run(run_agent())