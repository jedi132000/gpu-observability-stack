"""CLI integration tests via Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import gpuobs.prom as prom
from gpuobs.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parent.parent


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "gpuobs" in result.stdout


def test_validate_rules_on_shipped_files() -> None:
    result = runner.invoke(app, ["validate-rules", str(ROOT / "prometheus" / "rules")])
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_validate_dashboards_on_shipped_files_json_output() -> None:
    result = runner.invoke(
        app, ["validate-dashboards", str(ROOT / "dashboards"), "-o", "json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["overall"] == "OK"
    assert len(payload["checks"]) == 3


def test_validate_rules_missing_path_is_usage_error() -> None:
    result = runner.invoke(app, ["validate-rules", str(ROOT / "nope")])
    assert result.exit_code == 2


def test_check_exporter_with_patched_http(monkeypatch, make_exposition) -> None:
    text = make_exposition()
    monkeypatch.setattr(prom, "http_get", lambda url, timeout: text)
    result = runner.invoke(app, ["check-exporter", "--url", "http://fake:9400/metrics"])
    assert result.exit_code == 0
    assert "required-metrics" in result.stdout


def test_check_exporter_unreachable_exits_one(monkeypatch) -> None:
    def boom(url: str, timeout: float) -> str:
        raise OSError("refused")

    monkeypatch.setattr(prom, "http_get", boom)
    result = runner.invoke(
        app, ["check-exporter", "--url", "http://fake:9400/metrics", "--timeout", "0.1"]
    )
    assert result.exit_code == 1


def test_unknown_output_format_exits_two() -> None:
    result = runner.invoke(
        app, ["validate-dashboards", str(ROOT / "dashboards"), "-o", "xml"]
    )
    assert result.exit_code == 2
