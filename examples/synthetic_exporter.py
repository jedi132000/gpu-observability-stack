#!/usr/bin/env python3
"""Synthetic DCGM-shaped metrics exporter for the local demo.

This serves metrics with the SAME names and labels as the real NVIDIA DCGM
Exporter so the Prometheus rules, alerts, and Grafana dashboards can be
exercised on a machine with no GPU.

The data is NOT real accelerator telemetry. Every series carries a
``synthetic="true"`` label and the process prints a banner saying so. Do not
point production dashboards or alert routing at this endpoint, and never present
its output as live GPU data.

Run:

    pip install prometheus-client
    python examples/synthetic_exporter.py --port 9400

Then scrape http://localhost:9400/metrics.
"""

from __future__ import annotations

import argparse
import math
import sys
import time

from prometheus_client import Gauge, start_http_server

# A small synthetic fleet: two nodes, two GPUs each, each running one pod.
_FLEET = [
    # hostname, gpu index, uuid, model, namespace, pod
    ("gpu-node-a", "0", "GPU-aaaa0000", "NVIDIA A10G", "inference", "llama-7b-a"),
    ("gpu-node-a", "1", "GPU-aaaa0001", "NVIDIA A10G", "inference", "llama-7b-b"),
    ("gpu-node-b", "0", "GPU-bbbb0000", "NVIDIA A10G", "batch", "train-job-1"),
    ("gpu-node-b", "1", "GPU-bbbb0001", "NVIDIA A10G", "batch", "train-job-2"),
]

_LABELS = ["gpu", "UUID", "modelName", "Hostname", "namespace", "pod", "synthetic"]
_FB_TOTAL_MIB = 24576.0  # A10G: 24 GiB, split into used/free like DCGM reports.


def _build_gauges() -> dict[str, Gauge]:
    return {
        "util": Gauge("DCGM_FI_DEV_GPU_UTIL", "GPU utilization (percent) [SYNTHETIC]", _LABELS),
        "fb_used": Gauge("DCGM_FI_DEV_FB_USED", "Framebuffer used (MiB) [SYNTHETIC]", _LABELS),
        "fb_free": Gauge("DCGM_FI_DEV_FB_FREE", "Framebuffer free (MiB) [SYNTHETIC]", _LABELS),
        "temp": Gauge("DCGM_FI_DEV_GPU_TEMP", "GPU temperature (C) [SYNTHETIC]", _LABELS),
        "power": Gauge("DCGM_FI_DEV_POWER_USAGE", "GPU power (W) [SYNTHETIC]", _LABELS),
        "sm_clock": Gauge("DCGM_FI_DEV_SM_CLOCK", "SM clock (MHz) [SYNTHETIC]", _LABELS),
        "xid": Gauge("DCGM_FI_DEV_XID_ERRORS", "Last XID error code [SYNTHETIC]", _LABELS),
    }


def _update(gauges: dict[str, Gauge], tick: float) -> None:
    for i, (host, gpu, uuid, model, ns, pod) in enumerate(_FLEET):
        labels = dict(
            gpu=gpu, UUID=uuid, modelName=model, Hostname=host, namespace=ns, pod=pod,
            synthetic="true",
        )
        # Deterministic-ish waves, phase-shifted per GPU, so panels show movement.
        phase = i * 1.3
        util = 55 + 40 * math.sin(tick / 20 + phase)  # 15..95 %
        util = max(0.0, min(100.0, util))
        # batch namespace runs hot and near-full to exercise memory-pressure alerts.
        mem_frac = 0.92 if ns == "batch" else 0.4 + 0.3 * abs(math.sin(tick / 35 + phase))
        used = round(_FB_TOTAL_MIB * mem_frac)
        gauges["util"].labels(**labels).set(round(util, 1))
        gauges["fb_used"].labels(**labels).set(used)
        gauges["fb_free"].labels(**labels).set(_FB_TOTAL_MIB - used)
        gauges["temp"].labels(**labels).set(round(45 + util * 0.35, 1))
        gauges["power"].labels(**labels).set(round(120 + util * 1.6, 1))
        gauges["sm_clock"].labels(**labels).set(1200 + round(util * 3))
        gauges["xid"].labels(**labels).set(0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9400, help="Port to serve /metrics on.")
    parser.add_argument("--interval", type=float, default=5.0, help="Update interval (seconds).")
    args = parser.parse_args()

    print("=" * 72, file=sys.stderr)
    print("SYNTHETIC DCGM EXPORTER - demo data only, NOT real GPU telemetry.", file=sys.stderr)
    print(f"Serving on http://0.0.0.0:{args.port}/metrics", file=sys.stderr)
    print("=" * 72, file=sys.stderr)

    gauges = _build_gauges()
    start_http_server(args.port)
    start = time.monotonic()
    while True:
        _update(gauges, time.monotonic() - start)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
