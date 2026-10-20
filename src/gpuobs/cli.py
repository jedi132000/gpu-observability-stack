"""Command line for validating the GPU observability stack.

    gpuobs check-exporter --url http://localhost:9400/metrics
    gpuobs check-prometheus --url http://localhost:9090 --job dcgm-exporter
    gpuobs validate-rules prometheus/rules
    gpuobs validate-dashboards dashboards

Exit codes: 0 on success (warnings allowed), 1 on any failed check (or any
warning with --strict), 2 on usage error.
"""

from __future__ import annotations

from pathlib import Path

import typer

from gpuobs import __version__
from gpuobs.checks import CheckResult, check_exporter, check_prometheus, exit_code
from gpuobs.dashboards import validate_dashboard
from gpuobs.prom import ExporterClient, PrometheusClient
from gpuobs.report import render_json, render_text
from gpuobs.rules import validate_rule_file

app = typer.Typer(
    add_completion=False,
    help="Validate a DCGM/Prometheus/Grafana GPU observability stack.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"gpuobs {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """GPU observability stack validator."""


def _emit(title: str, results: list[CheckResult], output: str, strict: bool) -> None:
    if output == "json":
        typer.echo(render_json(title, results))
    elif output == "text":
        typer.echo(render_text(title, results))
    else:
        typer.echo(f"Unknown output format: {output}", err=True)
        raise typer.Exit(code=2)
    raise typer.Exit(code=exit_code(results, strict=strict))


@app.command("check-exporter")
def check_exporter_cmd(
    url: str = typer.Option(..., "--url", help="DCGM exporter /metrics URL."),
    timeout: float = typer.Option(5.0, "--timeout", help="Per-request timeout (seconds)."),
    output: str = typer.Option("text", "--output", "-o", help="text or json."),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as failures."),
) -> None:
    """Scrape a DCGM exporter directly and validate its metric families/labels."""

    client = ExporterClient(url=url, timeout=timeout)
    results = check_exporter(client)
    _emit(f"DCGM exporter: {url}", results, output, strict)


@app.command("check-prometheus")
def check_prometheus_cmd(
    url: str = typer.Option(..., "--url", help="Prometheus base URL, e.g. http://localhost:9090."),
    job: str = typer.Option("dcgm-exporter", "--job", help="Scrape job name for the exporter."),
    timeout: float = typer.Option(5.0, "--timeout", help="Per-request timeout (seconds)."),
    output: str = typer.Option("text", "--output", "-o", help="text or json."),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as failures."),
) -> None:
    """Check Prometheus connectivity, exporter scrape health, and metric presence."""

    client = PrometheusClient(base_url=url, timeout=timeout)
    results = check_prometheus(client, job)
    _emit(f"Prometheus: {url}", results, output, strict)


@app.command("validate-rules")
def validate_rules_cmd(
    path: Path = typer.Argument(..., help="A rule file or a directory of *.yaml rule files."),
    output: str = typer.Option("text", "--output", "-o", help="text or json."),
) -> None:
    """Validate Prometheus recording/alert rule files structurally."""

    files = _yaml_files(path)
    if not files:
        typer.echo(f"no YAML rule files found at {path}", err=True)
        raise typer.Exit(code=2)
    results = [validate_rule_file(f) for f in files]
    _emit("Prometheus rule files", results, output, strict=False)


@app.command("validate-dashboards")
def validate_dashboards_cmd(
    path: Path = typer.Argument(..., help="A dashboard JSON file or a directory of them."),
    output: str = typer.Option("text", "--output", "-o", help="text or json."),
) -> None:
    """Validate Grafana dashboard JSON (provisionable, no empty panels)."""

    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files:
        typer.echo(f"no dashboard JSON files found at {path}", err=True)
        raise typer.Exit(code=2)
    results = [validate_dashboard(f) for f in files]
    _emit("Grafana dashboards", results, output, strict=False)


def _yaml_files(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(p for p in path.glob("*.y*ml"))
    return [path] if path.exists() else []


if __name__ == "__main__":
    app()
