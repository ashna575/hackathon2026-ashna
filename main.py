"""
main.py - Entry point for the ShopWave Support Agent.
Run with: python main.py
"""

import asyncio
import json
import os
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
    print(f"\n Loaded {len(tickets)} tickets")
    print("Processing tickets in batches...\n")

    audit_log = []
    results = []
    start_time = datetime.now()

    batch_size = 3
    total_batches = (len(tickets) + batch_size - 1) // batch_size

    for i in range(0, len(tickets), batch_size):
        batch = tickets[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}: tickets {i+1}-{min(i+batch_size, len(tickets))}")

        batch_results = await asyncio.gather(
            *[process_ticket(ticket, audit_log) for ticket in batch],
            return_exceptions=True
        )
        results.extend(batch_results)

        if i + batch_size < len(tickets):
            print(f"  Waiting 20 seconds before next batch...")
            await asyncio.sleep(20)

    end_time = datetime.now()
    total_seconds = (end_time - start_time).total_seconds()

    audit_output = {
        "run_metadata": {
            "started_at": start_time.isoformat(),
            "finished_at": end_time.isoformat(),
            "total_duration_seconds": round(total_seconds, 2),
            "tickets_processed": len(tickets),
            "concurrency": "batches of 3 via asyncio.gather"
        },
        "results": [r for r in results if not isinstance(r, Exception)],
        "errors": [str(r) for r in results if isinstance(r, Exception)],
        "audit_trail": audit_log
    }

    with open("audit_log.json", "w") as f:
        json.dump(audit_output, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    resolved   = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "resolved")
    escalated  = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "escalated")
    needs_info = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "needs_info")
    errors     = sum(1 for r in results if isinstance(r, Exception))

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
            icon = {"resolved": "OK", "escalated": "ESC", "needs_info": "INFO"}.get(r.get("status"), "ERR")
            conf = r.get("confidence", 0)
            print(f"  [{icon}] {r['ticket_id']} | {r.get('status','?'):10} | conf: {conf:.0%} | {r.get('summary','')[:50]}")

    print("\nDone! Check audit_log.json for full reasoning trail.\n")


if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set!")
        print("Run: $env:GROQ_API_KEY='your_key_here'")
        exit(1)
    asyncio.run(run_agent())