# Metrics reference

Only metrics present in the default counter set of supported DCGM Exporter 3.x
releases are used. The validator's source of truth is `src/gpuobs/metrics.py`.

## Required families

| Metric | Unit | Meaning |
| --- | --- | --- |
| `DCGM_FI_DEV_GPU_UTIL` | percent (0–100) | GPU compute utilization. |
| `DCGM_FI_DEV_FB_USED` | MiB | Framebuffer memory in use. |
| `DCGM_FI_DEV_FB_FREE` | MiB | Framebuffer memory free. |
| `DCGM_FI_DEV_GPU_TEMP` | °C | GPU die temperature. |
| `DCGM_FI_DEV_POWER_USAGE` | W | Instantaneous board power draw. |

## Optional (health) families

| Metric | Unit | Meaning |
| --- | --- | --- |
| `DCGM_FI_DEV_SM_CLOCK` | MHz | Streaming-multiprocessor clock. |
| `DCGM_FI_DEV_XID_ERRORS` | code | Last XID error code (0 = none). |

These are supported on datacenter GPUs but not all parts, so their absence is a
warning, not a failure.

## No total-memory gauge

DCGM Exporter does not publish a total-framebuffer gauge in the default set.
Memory utilization is therefore computed as a recording rule:

```promql
gpu:fb_used_ratio = DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)
```

`FB_USED` and `FB_FREE` share an identical label set, so the division is
element-wise and label-safe.

## Labels

Always present (DCGM identity/topology):

- `gpu`, `UUID`, `modelName`, `Hostname`

Present only with Kubernetes pod mapping (the GPU Operator default, via the
kubelet PodResources API):

- `namespace`, `pod`

Workload (per-pod) dashboards depend on the second group. If they are empty,
`gpuobs check-exporter` reports a `kube-labels` warning and names the missing
labels. The ServiceMonitor/scrape config also adds a `node` label and pins the
scrape `job` to `dcgm-exporter` so alerts and the validator line up.
