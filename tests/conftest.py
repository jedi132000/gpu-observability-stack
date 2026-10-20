"""Shared fixtures for the observability-stack tests.

``make_exposition`` builds DCGM-shaped Prometheus text so the parsing and check
logic can be exercised without a live exporter.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_FAMILIES = {
    "DCGM_FI_DEV_GPU_UTIL": 42.0,
    "DCGM_FI_DEV_FB_USED": 1024.0,
    "DCGM_FI_DEV_FB_FREE": 23552.0,
    "DCGM_FI_DEV_GPU_TEMP": 55.0,
    "DCGM_FI_DEV_POWER_USAGE": 180.0,
    "DCGM_FI_DEV_SM_CLOCK": 1400.0,
    "DCGM_FI_DEV_XID_ERRORS": 0.0,
}


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def make_exposition() -> Callable[..., str]:
    def _make(
        *,
        include: list[str] | None = None,
        kube_labels: bool = True,
    ) -> str:
        families = include if include is not None else list(_DEFAULT_FAMILIES)
        base_labels = {
            "gpu": "0",
            "UUID": "GPU-0000",
            "modelName": "NVIDIA A10G",
            "Hostname": "gpu-node-a",
        }
        if kube_labels:
            base_labels |= {"namespace": "inference", "pod": "llama-a"}
        label_str = ",".join(f'{k}="{v}"' for k, v in base_labels.items())
        lines: list[str] = []
        for name in families:
            value = _DEFAULT_FAMILIES.get(name, 1.0)
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{{{label_str}}} {value}")
        return "\n".join(lines) + "\n"

    return _make
