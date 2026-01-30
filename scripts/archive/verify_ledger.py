import hashlib
import json
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Add the project root to the path so we can import internal modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_audit_chain(ledger_path: Path):
    console = Console()
    if not ledger_path.exists():
        console.print(f"[bold red]Error:[/] Ledger not found at {ledger_path}")
        return False

    console.print(f"\n[bold cyan]🔐 Verifying Audit Ledger Integrity:[/] {ledger_path.name}")

    with open(ledger_path, "r") as f:
        lines = f.readlines()

    if not lines:
        console.print("[yellow]Warning:[/] Ledger is empty.")
        return True

    table = Table(title="Audit Chain Verification", box=None)
    table.add_column("Index", justify="right")
    table.add_column("Step", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Integrity", justify="center")

    prev_hash = "0" * 64
    all_valid = True

    for i, line in enumerate(lines):
        record = json.loads(line)
        reported_hash = record.pop("hash")
        reported_prev = record.get("prev_hash")

        # 1. Check prev_hash match
        if reported_prev != prev_hash:
            integrity = "[bold red]FAIL (Chain Break)[/]"
            all_valid = False
        else:
            # 2. Recompute current hash
            record_json = json.dumps(record, sort_keys=True)
            recomputed_hash = hashlib.sha256(record_json.encode()).hexdigest()

            if recomputed_hash != reported_hash:
                integrity = "[bold red]FAIL (Signature mismatch)[/]"
                all_valid = False
            else:
                integrity = "[green]VALID[/]"

        table.add_row(str(i), record.get("step", record.get("type", "unknown")), record.get("status", "N/A"), integrity)
        prev_hash = reported_hash

    console.print(table)

    if all_valid:
        console.print("\n[bold green]✅ Cryptographic Integrity Verified.[/] Chain is consistent and untampered.\n")
    else:
        console.print("\n[bold red]❌ INTEGRITY BREACH DETECTED.[/] One or more records have been modified or the chain is broken.\n")

    return all_valid


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", help="Path to audit.jsonl file")
    args = parser.parse_args()

    success = verify_audit_chain(Path(args.ledger))
    sys.exit(0 if success else 1)
