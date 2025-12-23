"""Shared presentation helpers for CLI output."""

from collections.abc import Iterable, Sequence
from contextlib import contextmanager

from rich.console import Console
from rich.table import Table

# Single console instance for consistent styling
console = Console()


def section(title: str, subtitle: str | None = None) -> None:
    """Render a section divider with an optional subtitle."""
    label = f"[bold]{title}[/bold]"
    if subtitle:
        label = f"{label} [dim]{subtitle}[/dim]"
    console.rule(label)


def info(message: str) -> None:
    """Display an informational line."""
    console.print(f"[cyan][INFO][/cyan] {message}", soft_wrap=True, overflow="ignore")


def success(message: str) -> None:
    """Display a success line."""
    console.print(f"[green][OK][/green] {message}", soft_wrap=True, overflow="ignore")


def warning(message: str) -> None:
    """Display a warning line."""
    console.print(
        f"[yellow][WARN][/yellow] {message}", soft_wrap=True, overflow="ignore"
    )


def error(message: str) -> None:
    """Display an error line."""
    console.print(f"[red][ERROR][/red] {message}", soft_wrap=True, overflow="ignore")


def hint(message: str) -> None:
    """Display a muted hint line."""
    console.print(f"[dim]{message}[/dim]", soft_wrap=True, overflow="ignore")


def render_table(
    columns: Sequence[str],
    rows: Iterable[Sequence[object]],
    title: str | None = None,
    caption: str | None = None,
) -> None:
    """Render a simple table with consistent styling."""
    table = Table(
        show_header=True,
        header_style="bold",
        title=title,
        caption=caption,
        pad_edge=False,
    )
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*(str(cell) if cell is not None else "" for cell in row))
    console.print(table)


@contextmanager
def working(message: str):
    """Show a transient status spinner while work is performed."""
    with console.status(message):
        yield
