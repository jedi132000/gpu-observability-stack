"""Validation checks for the observability stack.

Pure classification functions operate on already-parsed samples so they can be
tested with fixed payloads. Orchestration functions wrap the HTTP clients and
convert transport errors into failed checks with actionable detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gpuobs import metrics
from gpuobs.parse import (
    Sample,
    family_names,
    labels_present,
    parse_exposition,
    parse_query_result,
)
from gpuobs.prom import ExporterClient, PromError, PrometheusClient


class Status(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    detail: str


# --- pure checks over parsed samples -------------------------------------------------


def check_required_families(samples: list[Sample]) -> CheckResult:
    present = family_names(samples)
    missing = sorted(metrics.required_names() - present)
    if missing:
        return CheckResult(
            "required-metrics",
            Status.FAIL,
            f"missing required DCGM families: {', '.join(missing)}",
        )
    return CheckResult(
        "required-metrics", Status.OK, f"all {len(metrics.REQUIRED)} required families present"
    )


def check_optional_families(samples: list[Sample]) -> CheckResult:
    present = family_names(samples)
    missing = sorted({m.name for m in metrics.OPTIONAL} - present)
    if missing:
        return CheckResult(
            "optional-metrics",
            Status.WARN,
            f"optional health families absent (not supported on all GPUs): {', '.join(missing)}",
        )
    return CheckResult("optional-metrics", Status.OK, "optional health families present")


def check_kube_labels(samples: list[Sample]) -> CheckResult:
    """Workload dashboards need pod/namespace labels from Kubernetes pod mapping."""

    probe = metrics.REQUIRED[0].name  # DCGM_FI_DEV_GPU_UTIL
    if not any(s.name == probe for s in samples):
        return CheckResult("kube-labels", Status.SKIP, f"no {probe} samples to inspect")
    seen = labels_present(samples, probe)
    missing = [label for label in metrics.KUBE_LABELS if label not in seen]
    if missing:
        return CheckResult(
            "kube-labels",
            Status.WARN,
            (
                f"{probe} is missing Kubernetes labels {missing}; workload (pod/namespace) "
                "dashboards will be empty. Enable pod mapping on the exporter."
            ),
        )
    return CheckResult("kube-labels", Status.OK, "pod/namespace labels present on GPU metrics")


# --- orchestration (network) ---------------------------------------------------------


def check_exporter(client: ExporterClient) -> list[CheckResult]:
    try:
        text = client.scrape()
    except PromError as exc:
        return [CheckResult("exporter-reachable", Status.FAIL, str(exc))]
    try:
        samples = parse_exposition(text)
    except ValueError as exc:
        return [CheckResult("exporter-parse", Status.FAIL, str(exc))]

    reachable = CheckResult(
        "exporter-reachable", Status.OK, f"scraped {len(samples)} samples from {client.url}"
    )
    return [
        reachable,
        check_required_families(samples),
        check_optional_families(samples),
        check_kube_labels(samples),
    ]


def check_prometheus(client: PrometheusClient, job: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    # 1. Connectivity.
    try:
        info = client.build_info()
        version = info.get("data", {}).get("version", "unknown")
        results.append(
            CheckResult("prometheus-reachable", Status.OK, f"connected (version {version})")
        )
    except PromError as exc:
        return [CheckResult("prometheus-reachable", Status.FAIL, str(exc))]

    # 2. Exporter scrape health via up{job}.
    results.append(_check_up(client, job))

    # 3. Required metric-family discovery via the query API.
    results.append(_check_required_via_query(client))

    return results


def _check_up(client: PrometheusClient, job: str) -> CheckResult:
    try:
        payload = client.query(f'up{{job="{job}"}}')
        samples = parse_query_result(payload)
    except (PromError, ValueError) as exc:
        return CheckResult("exporter-scrape-health", Status.FAIL, str(exc))
    if not samples:
        return CheckResult(
            "exporter-scrape-health",
            Status.FAIL,
            f'no up series for job="{job}"; the DCGM exporter target is not being scraped',
        )
    down = [s for s in samples if s.value != 1.0]
    if down:
        hosts = ", ".join(sorted(s.labels.get("instance", "?") for s in down))
        return CheckResult(
            "exporter-scrape-health",
            Status.FAIL,
            f"{len(down)}/{len(samples)} exporter target(s) down: {hosts}",
        )
    return CheckResult(
        "exporter-scrape-health", Status.OK, f"{len(samples)} exporter target(s) up"
    )


def _check_required_via_query(client: PrometheusClient) -> CheckResult:
    missing: list[str] = []
    for name in sorted(metrics.required_names()):
        try:
            payload = client.query(f"count({name})")
            samples = parse_query_result(payload)
        except (PromError, ValueError) as exc:
            return CheckResult("required-metrics", Status.FAIL, f"query for {name} failed: {exc}")
        if not samples or samples[0].value < 1:
            missing.append(name)
    if missing:
        return CheckResult(
            "required-metrics",
            Status.FAIL,
            f"Prometheus has no series for: {', '.join(missing)}",
        )
    return CheckResult(
        "required-metrics", Status.OK, "all required DCGM families present in Prometheus"
    )


# --- aggregation ---------------------------------------------------------------------


def overall_status(results: list[CheckResult]) -> Status:
    statuses = {r.status for r in results}
    if Status.FAIL in statuses:
        return Status.FAIL
    if Status.WARN in statuses:
        return Status.WARN
    return Status.OK


def exit_code(results: list[CheckResult], *, strict: bool) -> int:
    status = overall_status(results)
    if status is Status.FAIL:
        return 1
    if status is Status.WARN and strict:
        return 1
    return 0
