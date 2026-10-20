"""Pure parsing helpers for Prometheus data (no network I/O).

Separated from :mod:`gpuobs.prom` so the parsing and classification logic can be
tested against fixed payloads without a live Prometheus or exporter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prometheus_client.parser import text_string_to_metric_families


@dataclass(frozen=True)
class Sample:
    name: str
    labels: dict[str, str]
    value: float


def parse_exposition(text: str) -> list[Sample]:
    """Parse Prometheus text-exposition into a flat list of samples.

    Raises ValueError on malformed input (surfaced as a failed check upstream).
    """

    samples: list[Sample] = []
    try:
        for family in text_string_to_metric_families(text):
            for s in family.samples:
                samples.append(Sample(name=s.name, labels=dict(s.labels), value=s.value))
    except Exception as exc:  # the parser raises assorted errors on bad input
        raise ValueError(f"could not parse Prometheus exposition text: {exc}") from exc
    return samples


def family_names(samples: list[Sample]) -> set[str]:
    return {s.name for s in samples}


def samples_for(samples: list[Sample], name: str) -> list[Sample]:
    return [s for s in samples if s.name == name]


def labels_present(samples: list[Sample], name: str) -> set[str]:
    """Union of label keys seen across all samples of a metric family."""

    keys: set[str] = set()
    for s in samples_for(samples, name):
        keys.update(s.labels)
    return keys


def parse_query_result(payload: dict[str, Any]) -> list[Sample]:
    """Turn a Prometheus HTTP API ``/query`` JSON payload into samples.

    Supports the ``vector`` result type (the only type the checks issue).
    """

    if payload.get("status") != "success":
        raise ValueError(f"query was not successful: {payload.get('error', 'unknown error')}")
    data = payload.get("data", {})
    if data.get("resultType") != "vector":
        raise ValueError(f"unexpected result type: {data.get('resultType')!r}")
    out: list[Sample] = []
    for item in data.get("result", []):
        metric = dict(item.get("metric", {}))
        name = metric.pop("__name__", "")
        value = float(item["value"][1])
        out.append(Sample(name=name, labels=metric, value=value))
    return out
