# Runbooks

Operator responses for each shipped alert. Severities: **critical** pages,
**warning** is a ticket, **info** is dashboard context.

## DCGMExporterDown (critical)

**Means:** Prometheus has a target for the DCGM exporter but scrapes are failing
(`up{job="dcgm-exporter"} == 0`) for 5 minutes. All GPU telemetry from that node
is missing.

**Respond:**
1. `kubectl -n gpu-operator get pods -l app=nvidia-dcgm-exporter -o wide` — find
   the pod on the affected node.
2. Check pod status/logs; a `CrashLoopBackOff` often means a driver/toolkit
   mismatch on the node.
3. Confirm the Service endpoint exists and the ServiceMonitor selector matches.
4. Validate once recovered: `gpuobs check-exporter --url http://<pod-ip>:9400/metrics`.

## GPUTelemetryMissing (critical)

**Means:** `DCGM_FI_DEV_GPU_UTIL` has been absent entirely for 10 minutes — no
GPU nodes, exporter exposing nothing, or broken service discovery.

**Respond:**
1. If the cluster has no GPU nodes, this alert should be scoped out — do that.
2. Otherwise run `gpuobs check-prometheus --url <prom> --job dcgm-exporter` to
   see whether the issue is discovery (no `up` series) or empty metrics.
3. Check `nvidia-smi` on a GPU node and the device-plugin/GPU-Operator status in
   `gpu-kubernetes-platform`.

## GPUMemoryPressureHigh / GPUMemoryPressureCritical (warning / critical)

**Means:** `gpu:fb_used_ratio` above 0.90 for 15m (warning) or 0.98 for 10m
(critical). New allocations risk out-of-memory failures.

**Respond:**
1. Identify the workload: the alert carries `pod` and `namespace`.
2. Check whether the model's memory footprint grew or a leak is accumulating.
3. Reschedule, lower batch size, or move to a larger-memory GPU. Capacity
   what-ifs can be modeled in `gpu-scheduler-capacity-lab`.

## GPUHighTemperatureSustained (warning)

**Means:** `DCGM_FI_DEV_GPU_TEMP > 85 °C` for 10m; thermal throttling likely.

**Respond:**
1. Check node cooling/airflow and neighboring GPU load.
2. Correlate with utilization and clock (`DCGM_FI_DEV_SM_CLOCK`) to confirm
   throttling.
3. If temperature keeps climbing, cordon and drain the node.

## GPUXidErrorDetected (critical)

**Means:** `DCGM_FI_DEV_XID_ERRORS > 0` for 5m — a GPU hardware or driver fault;
the alert value is the XID code.

**Respond:**
1. `kubectl cordon <node>` to stop new GPU work landing there.
2. On the node: `nvidia-smi -q`, `dmesg | grep -i xid` to identify the fault.
3. Drain and, for persistent hardware XIDs (e.g. 48/63/79), raise a hardware
   replacement with the provider.
