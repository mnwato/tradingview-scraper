import json
import os
from datetime import datetime

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tradingview_scraper.settings import get_settings


def format_weight(w: float) -> str:
    return f"{w:.2%}"


def get_trend_icon(adx: float) -> str:
    if adx > 25:
        return "[bold red]🔥[/]"
    if adx > 15:
        return "[bold yellow]📈[/]"
    return "[blue]➡️[/]"


def display_dashboard():
    console = Console()
    data_path = "data/lakehouse/portfolio_optimized_v2.json"
    candidates_path = "data/lakehouse/portfolio_candidates.json"

    if not os.path.exists(data_path):
        console.print("[bold red]Error:[/] portfolio_optimized_v2.json not found. Run 'make optimize-v2' first.")
        return

    with open(data_path, "r") as f:
        data = json.load(f)

    candidates = []
    if os.path.exists(candidates_path):
        with open(candidates_path, "r") as f:
            candidates = json.load(f)

    profiles = data.get("profiles", {})

    console.print(
        Panel.fit(
            "[bold cyan]📊 Quantitative Portfolio Implementation Dashboard[/]",
            subtitle=f"Generated: {datetime.fromtimestamp(os.path.getmtime(data_path)).strftime('%Y-%m-%d %H:%M:%S')}",
            box=box.DOUBLE,
        )
    )

    # 1. Candidate Universe Summary (Top 10 by ADX)
    if candidates:
        table = Table(title="🔍 Top Trend Candidates", box=box.SIMPLE, header_style="bold magenta")
        table.add_column("Symbol", style="cyan")
        table.add_column("Market")
        table.add_column("ADX", justify="right")
        table.add_column("Trend", justify="center")
        table.add_column("Direction", justify="center")

        sorted_c = sorted(candidates, key=lambda x: x.get("adx", 0), reverse=True)[:10]
        for c in sorted_c:
            table.add_row(c["symbol"], c.get("market", "N/A"), f"{c.get('adx', 0):.1f}", get_trend_icon(c.get("adx", 0)), f"[bold]{c.get('direction', 'LONG')}[/]")
        console.print(table)

    # 2. Risk Profiles
    for name, p_data in profiles.items():
        pretty_name = name.replace("_", " ").title()
        assets = p_data.get("assets", [])
        clusters = p_data.get("clusters", [])

        # Calculate summary stats
        unique_clusters = len(clusters)

        table = Table(title=f"\n⚖️  [bold green]{pretty_name} Profile[/]", box=box.ROUNDED, header_style="bold yellow")
        table.add_column("Rank", justify="center", width=4)
        table.add_column("Symbol", style="cyan")
        table.add_column("Cluster", justify="center")
        table.add_column("Weight", justify="right", style="bold green")
        table.add_column("Market")
        table.add_column("Dir", justify="center")

        top_assets = sorted(assets, key=lambda x: x["Weight"], reverse=True)[:15]
        for i, a in enumerate(top_assets, 1):
            table.add_row(str(i), a["Symbol"], str(a.get("Cluster_ID", "N/A")), format_weight(a["Weight"]), a.get("Market", "N/A"), a.get("Direction", "LONG"))

        # Cluster Summary for this profile
        c_table = Table(title="[dim]Top 5 Risk Buckets[/]", box=box.SIMPLE, show_header=False)
        for c in clusters[:5]:
            c_table.add_row(f"Cluster {c['Cluster_ID']}", f"[bold white]{format_weight(c['Gross_Weight'])}[/]", c.get("Lead_Asset", ""))

        console.print(Columns([table, c_table]))

    summaries_path = get_settings().summaries_latest_link
    console.print(f"\n[dim]Artifacts generated in {summaries_path}/ directory.[/]")


if __name__ == "__main__":
    display_dashboard()
