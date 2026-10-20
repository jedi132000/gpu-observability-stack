"""Tests for the validation checks using injected (no-network) fetchers."""

from __future__ import annotations

import json

from gpuobs.checks import (
    Status,
    check_exporter,
    check_prometheus,
    check_required_families,
    exit_code,
    overall_status,
)
from gpuobs.metrics import REQUIRED
from gpuobs.parse import parse_exposition
from gpuobs.prom import ExporterClient, PrometheusClient

# --- pure checks ---------------------------------------------------------------------


def test_required_families_pass(make_exposition) -> None:
    result = check_required_families(parse_exposition(make_exposition()))
    assert result.status is Status.OK


def test_required_families_detects_missing(make_exposition) -> None:
    present = [m.name for m in REQUIRED if m.name != "DCGM_FI_DEV_FB_FREE"]
    result = check_required_families(parse_exposition(make_exposition(include=present)))
    assert result.status is Status.FAIL
    assert "DCGM_FI_DEV_FB_FREE" in result.detail


# --- exporter orchestration ----------------------------------------------------------


def test_check_exporter_happy_path(make_exposition) -> None:
    text = make_exposition()
    client = ExporterClient(url="http://x:9400/metrics", fetch=lambda url, timeout: text)
    results = check_exporter(client)
    statuses = {r.name: r.status for r in results}
    assert statuses["exporter-reachable"] is Status.OK
    assert statuses["required-metrics"] is Status.OK
    assert statuses["kube-labels"] is Status.OK


def test_check_exporter_warns_without_kube_labels(make_exposition) -> None:
    text = make_exposition(kube_labels=False)
    client = ExporterClient(url="http://x:9400/metrics", fetch=lambda url, timeout: text)
    results = check_exporter(client)
    kube = next(r for r in results if r.name == "kube-labels")
    assert kube.status is Status.WARN
    assert overall_status(results) is Status.WARN


def test_check_exporter_unreachable_fails() -> None:
    def boom(url: str, timeout: float) -> str:
        raise OSError("connection refused")

    client = ExporterClient(url="http://x:9400/metrics", retries=0, fetch=boom)
    results = check_exporter(client)
    assert results[0].name == "exporter-reachable"
    assert results[0].status is Status.FAIL


# --- prometheus orchestration --------------------------------------------------------


def _prom_fetcher(up_value: str = "1", families_present: bool = True):
    """Build a fetcher that answers buildinfo / up / count(...) queries."""

    def fetch(url: str, timeout: float) -> str:
        if "/status/buildinfo" in url:
            return json.dumps({"status": "success", "data": {"version": "2.54.1"}})
        if "query=up" in url or "up%7B" in url or "up{" in url:
            return json.dumps(
                {
                    "status": "success",
                    "data": {
                        "resultType": "vector",
                        "result": [
                            {
                                "metric": {"__name__": "up", "job": "dcgm-exporter",
                                           "instance": "node-a:9400"},
                                "value": [1700000000, up_value],
                            }
                        ],
                    },
                }
            )
        # count(<family>) queries
        count = "1" if families_present else "0"
        result = (
            [{"metric": {}, "value": [1700000000, count]}] if families_present else []
        )
        return json.dumps(
            {"status": "success", "data": {"resultType": "vector", "result": result}}
        )

    return fetch


def test_check_prometheus_all_healthy() -> None:
    client = PrometheusClient(base_url="http://prom:9090", fetch=_prom_fetcher())
    results = check_prometheus(client, job="dcgm-exporter")
    assert overall_status(results) is Status.OK


def test_check_prometheus_exporter_down() -> None:
    client = PrometheusClient(base_url="http://prom:9090", fetch=_prom_fetcher(up_value="0"))
    results = check_prometheus(client, job="dcgm-exporter")
    scrape = next(r for r in results if r.name == "exporter-scrape-health")
    assert scrape.status is Status.FAIL
    assert "down" in scrape.detail


def test_check_prometheus_missing_metrics() -> None:
    client = PrometheusClient(
        base_url="http://prom:9090", fetch=_prom_fetcher(families_present=False)
    )
    results = check_prometheus(client, job="dcgm-exporter")
    req = next(r for r in results if r.name == "required-metrics")
    assert req.status is Status.FAIL


# --- exit codes ----------------------------------------------------------------------


def test_exit_code_mapping(make_exposition) -> None:
    ok = check_exporter(
        ExporterClient(url="http://x/metrics", fetch=lambda u, t: make_exposition())
    )
    assert exit_code(ok, strict=False) == 0

    no_kube = make_exposition(kube_labels=False)
    warn = check_exporter(
        ExporterClient(url="http://x/metrics", fetch=lambda u, t: no_kube)
    )
    assert exit_code(warn, strict=False) == 0
    assert exit_code(warn, strict=True) == 1
