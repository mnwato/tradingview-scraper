import os
from typing import cast

import pandas as pd
import scipy.cluster.hierarchy as sch
from rich.console import Console
from rich.table import Table
from rich.text import Text


def get_color(val: float) -> str:
    """Maps correlation value to rich color."""
    if val > 0.8:
        return "bold red"
    if val > 0.5:
        return "red"
    if val > 0.2:
        return "orange3"
    if val > -0.2:
        return "white"
    if val > -0.5:
        return "cyan"
    return "bold blue"


def get_block(val: float) -> str:
    """Maps correlation value to a Unicode block character."""
    if abs(val) > 0.8:
        return "█"
    if abs(val) > 0.5:
        return "▓"
    if abs(val) > 0.2:
        return "▒"
    return "░"


def visualize_cli():
    console = Console()
    returns_path = "data/lakehouse/portfolio_returns.pkl"

    if not os.path.exists(returns_path):
        console.print("[bold red]Error:[/] portfolio_returns.pkl not found.")
        return

    returns = cast(pd.DataFrame, pd.read_pickle(returns_path))
    corr = returns.corr()

    # Hierarchical ordering (same as clustermap)
    if len(corr) > 1:
        d = sch.distance.pdist(corr.values)
        L = sch.linkage(d, method="average")
        ind = sch.leaves_list(L)
        ordered_symbols = [cast(str, corr.columns[i]) for i in ind]
        corr = corr.loc[ordered_symbols, ordered_symbols]

    # Downsample if too large for terminal
    max_dim = 40
    if len(corr) > max_dim:
        console.print(f"[yellow]Warning:[/] Matrix too large ({len(corr)}x{len(corr)}). Downsampling to {max_dim}x{max_dim} for CLI view.")
        # Simple slicing for now, better would be cluster-aware sampling
        step = len(corr) // max_dim
        indices = list(range(0, len(corr), step))[:max_dim]
        corr = corr.iloc[indices, indices]

    table = Table(show_header=True, header_style="bold", box=None, padding=0)
    table.add_column("Symbol", width=15)

    for col in corr.columns:
        # Use short name for header
        col_str = str(col)
        short_name = col_str.split(":")[-1][:4]
        table.add_column(short_name, justify="center", width=2)

    for _, (sym, row) in enumerate(corr.iterrows()):
        sym_str = str(sym)
        row_cells = [Text(sym_str.split(":")[-1][:12], style="cyan")]
        for val in row:
            v_float = float(val)
            color = get_color(v_float)
            block = get_block(v_float)
            row_cells.append(Text(block, style=color))
        table.add_row(*row_cells)

    console.print("\n[bold cyan]📉 Hierarchical Correlation Heatmap (CLI View)[/]")
    console.print("[dim]Order based on hierarchical linkage. █=High, ░=Low correlation.[/]")
    console.print(table)

    # Legend
    legend = Text()
    legend.append("\nLegend: ", style="bold")
    legend.append("█ >0.8 ", style="bold red")
    legend.append("▓ >0.5 ", style="red")
    legend.append("▒ >0.2 ", style="orange3")
    legend.append("░ <0.2 ", style="white")
    legend.append("█ <-0.5", style="bold blue")
    console.print(legend)


if __name__ == "__main__":
    visualize_cli()
