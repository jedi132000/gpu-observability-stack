"""Validate the shipped Grafana dashboards and the dashboard validator."""

from __future__ import annotations

import json
from pathlib import Path

from gpuobs.checks import Status
from gpuobs.dashboards import validate_dashboard

DASH_DIR = Path(__file__).resolve().parent.parent / "dashboards"
EXPECTED = {
    "gpu-fleet-overview.json",
    "gpu-workload-diagnostics.json",
    "gpu-operational-health.json",
}


def test_expected_dashboards_exist() -> None:
    present = {p.name for p in DASH_DIR.glob("*.json")}
    assert present >= EXPECTED


def test_shipped_dashboards_are_valid() -> None:
    for f in sorted(DASH_DIR.glob("*.json")):
        result = validate_dashboard(f)
        assert result.status is Status.OK, f"{f.name}: {result.detail}"


def test_shipped_dashboards_target_known_metrics() -> None:
    # Every query references either a DCGM family or one of our recording rules.
    allowed_fragments = ("DCGM_FI_DEV_", "gpu:", "namespace:", "fleet:", "node:", "up{")
    for f in DASH_DIR.glob("*.json"):
        doc = json.loads(f.read_text(encoding="utf-8"))
        for panel in doc["panels"]:
            for target in panel.get("targets", []):
                expr = target["expr"]
                assert any(frag in expr for frag in allowed_fragments), f"{f.name}: {expr}"


def test_validator_flags_empty_expr(tmp_path: Path) -> None:
    bad = {
        "title": "bad",
        "panels": [
            {"id": 1, "type": "timeseries", "title": "x", "targets": [{"refId": "A", "expr": ""}]}
        ],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert validate_dashboard(path).status is Status.FAIL


def test_validator_flags_dashboard_with_no_panels(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"title": "t", "panels": []}), encoding="utf-8")
    assert validate_dashboard(path).status is Status.FAIL
