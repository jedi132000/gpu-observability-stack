"""The DCGM Exporter metric families this stack depends on.

Only metrics that exist in supported DCGM Exporter releases (3.x default
counter set) are listed. GPU memory *capacity* is intentionally absent: DCGM
Exporter does not publish a total-framebuffer gauge in the default set, so
capacity is derived as ``FB_USED + FB_FREE`` (see docs/metrics.md).

Pod/namespace/container labels are present only when the exporter is run with
Kubernetes pod mapping enabled (the GPU Operator default); they are marked
``kube_mapped`` here so the label-diagnostics check can explain their absence
rather than failing a bare-metal exporter.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricFamily:
    name: str
    unit: str
    description: str
    # True when this family is only populated once the exporter maps metrics to
    # pods via the kubelet PodResources API.
    kube_mapped: bool = False


# Core families used by the dashboards, recording rules, and alerts.
REQUIRED: tuple[MetricFamily, ...] = (
    MetricFamily("DCGM_FI_DEV_GPU_UTIL", "percent", "GPU utilization (0-100)."),
    MetricFamily("DCGM_FI_DEV_FB_USED", "MiB", "Framebuffer memory used."),
    MetricFamily("DCGM_FI_DEV_FB_FREE", "MiB", "Framebuffer memory free."),
    MetricFamily("DCGM_FI_DEV_GPU_TEMP", "celsius", "GPU temperature."),
    MetricFamily("DCGM_FI_DEV_POWER_USAGE", "watt", "GPU power draw."),
)

# Health signals used by alerts; supported on most datacenter GPUs but not all
# consumer parts, so their absence is a warning rather than a hard failure.
OPTIONAL: tuple[MetricFamily, ...] = (
    MetricFamily("DCGM_FI_DEV_SM_CLOCK", "MHz", "Streaming-multiprocessor clock."),
    MetricFamily("DCGM_FI_DEV_XID_ERRORS", "count", "Last XID error code seen on the device."),
)

# Identity/topology labels DCGM always emits.
BASE_LABELS: tuple[str, ...] = ("gpu", "UUID", "modelName", "Hostname")

# Labels only present with Kubernetes pod mapping. Used by workload dashboards.
KUBE_LABELS: tuple[str, ...] = ("namespace", "pod")


def required_names() -> frozenset[str]:
    return frozenset(m.name for m in REQUIRED)


def all_families() -> tuple[MetricFamily, ...]:
    return REQUIRED + OPTIONAL


def family(name: str) -> MetricFamily | None:
    return next((m for m in all_families() if m.name == name), None)
