"""
main.py - Entry point for the ShopWave Support Agent.
Run with: python main.py

Set ONE of these before running:
  $env:GROQ_API_KEY="your_key"      (try this first)
  $env:GEMINI_API_KEY="your_key"    (fallback)
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
    print(f"\n  Loaded {len(tickets)} tickets")
    print("  Processing in concurrent batches of 3...\n")

    audit_log = []
    results = []
    start_time = datetime.now()

    # ── CONCURRENCY: batch of 3 tickets at once ──
    batch_size = 3
    total_batches = (len(tickets) + batch_size - 1) // batch_size

    for i in range(0, len(tickets), batch_size):
        batch = tickets[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}: "
              f"tickets {i+1}-{min(i+batch_size, len(tickets))}")

        batch_results = await asyncio.gather(
            *[process_ticket(ticket, audit_log) for ticket in batch],
            return_exceptions=True
        )

        for r in batch_results:
            if isinstance(r, Exception):
                results.append({"status": "error", "summary": str(r),
                                "confidence": 0, "tools_called": [],
                                "tool_count": 0, "ticket_id": "unknown"})
            else:
                results.append(r)

        if i + batch_size < len(tickets):
            print(f"  Waiting 20s before next batch...")
            time.sleep(20)

    end_time = datetime.now()
    total_seconds = (end_time - start_time).total_seconds()

    # Save audit log
    audit_output = {
        "run_metadata": {
            "started_at": start_time.isoformat(),
            "finished_at": end_time.isoformat(),
            "total_duration_seconds": round(total_seconds, 2),
            "tickets_processed": len(tickets),
            "concurrency": "batches of 3 via asyncio.gather"
        },
        "results": results,
        "audit_trail": audit_log
    }
    with open("audit_log.json", "w") as f:
        json.dump(audit_output, f, indent=2, default=str)

    # Dead letter queue
    failed = [r for r in results if r.get("status") == "error"]
    with open("dead_letter_queue.json", "w") as f:
        json.dump({"failed_tickets": failed,
                   "timestamp": datetime.now().isoformat()}, f, indent=2)

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
        if isinstance(r, dict):
            icon = {"resolved":   "[OK] ",
                    "escalated":  "[ESC]",
                    "needs_info": "[NFO]",
                    "error":      "[ERR]"}.get(r.get("status"), "[?]  ")
            conf = r.get("confidence", 0)
            tid  = r.get("ticket_id", "???")
            summ = r.get("summary", "")[:55]
            print(f"  {icon} {tid} | {r.get('status','?'):10} | "
                  f"conf: {conf:.0%} | {summ}")

    print("\nDone! Check audit_log.json for full reasoning trail.\n")


if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: No API key found!")
        print("Set one of these:")
        print("  $env:GROQ_API_KEY='your_key'")
        print("  $env:GEMINI_API_KEY='your_key'")
        exit(1)
    asyncio.run(run_agent())