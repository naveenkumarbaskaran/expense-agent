"""CLI entry point for the expense auditor."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agent import ExpenseAgent
from .policy import ExpensePolicy

console = Console()


@click.group()
def cli() -> None:
    """Expense Audit Agent — AI-powered expense policy enforcement."""


@cli.command()
@click.argument("expenses_csv", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--policy",
    "policy_yaml",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a YAML policy configuration file.",
    show_default=True,
)
@click.option(
    "--output",
    "output_path",
    default="audit-report.md",
    type=click.Path(dir_okay=False),
    help="Output path for the markdown audit report.",
    show_default=True,
)
def audit(
    expenses_csv: str,
    policy_yaml: str | None,
    output_path: str,
) -> None:
    """Audit EXPENSES_CSV and generate a policy compliance report.

    EXPENSES_CSV must be a CSV file with columns: date, merchant, amount, description.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Expense Audit Agent[/bold cyan]",
            subtitle="Powered by Claude",
        )
    )

    # Load policy
    if policy_yaml:
        console.print(f"[dim]Loading policy from {policy_yaml}[/dim]")
        policy = ExpensePolicy.from_yaml(policy_yaml)
    else:
        console.print("[dim]Using default expense policy[/dim]")
        policy = ExpensePolicy()

    agent = ExpenseAgent(policy=policy)

    console.print(f"[bold]Input:[/bold]  {expenses_csv}")
    console.print(f"[bold]Output:[/bold] {output_path}")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Running audit with Claude...", total=None)
        try:
            result = agent.audit(csv_path=expenses_csv, output_path=output_path)
            progress.update(task, description="Done.")
        except Exception as exc:
            progress.stop()
            console.print(f"[bold red]Audit failed:[/bold red] {exc}")
            raise SystemExit(1) from exc

    report_path = Path(result)
    size_kb = report_path.stat().st_size / 1024
    console.print(
        Panel(
            f"[green]Audit complete![/green]\n"
            f"Report saved to [bold]{result}[/bold] ({size_kb:.1f} KB)",
            title="Success",
            border_style="green",
        )
    )


@cli.command(name="show-policy")
@click.option(
    "--policy",
    "policy_yaml",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a YAML policy configuration file.",
)
def show_policy(policy_yaml: str | None) -> None:
    """Display the current expense policy."""
    if policy_yaml:
        policy = ExpensePolicy.from_yaml(policy_yaml)
        console.print(f"[dim]Policy loaded from {policy_yaml}[/dim]\n")
    else:
        policy = ExpensePolicy()
        console.print("[dim]Default policy[/dim]\n")

    console.print(policy.to_prompt_description())


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
