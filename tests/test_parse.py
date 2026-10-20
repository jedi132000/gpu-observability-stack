"""Tests for the pure Prometheus parsing helpers."""

from __future__ import annotations

import pytest

from gpuobs.parse import (
    family_names,
    labels_present,
    parse_exposition,
    parse_query_result,
    samples_for,
)


def test_parse_exposition_extracts_samples(make_exposition) -> None:
    samples = parse_exposition(make_exposition())
    names = family_names(samples)
    assert "DCGM_FI_DEV_GPU_UTIL" in names
    util = samples_for(samples, "DCGM_FI_DEV_GPU_UTIL")
    assert len(util) == 1
    assert util[0].value == 42.0
    assert util[0].labels["Hostname"] == "gpu-node-a"


def test_labels_present_reports_kube_labels(make_exposition) -> None:
    with_kube = parse_exposition(make_exposition(kube_labels=True))
    without_kube = parse_exposition(make_exposition(kube_labels=False))
    assert {"namespace", "pod"} <= labels_present(with_kube, "DCGM_FI_DEV_GPU_UTIL")
    assert "pod" not in labels_present(without_kube, "DCGM_FI_DEV_GPU_UTIL")


def test_parse_exposition_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_exposition("# TYPE x gauge\nx{bad=} not_a_number\n")


def test_parse_query_result_vector() -> None:
    payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {"__name__": "up", "job": "dcgm-exporter"}, "value": [1700000000, "1"]}
            ],
        },
    }
    samples = parse_query_result(payload)
    assert len(samples) == 1
    assert samples[0].name == "up"
    assert samples[0].value == 1.0
    assert samples[0].labels["job"] == "dcgm-exporter"


def test_parse_query_result_rejects_error_payload() -> None:
    with pytest.raises(ValueError, match="not successful"):
        parse_query_result({"status": "error", "error": "boom"})
