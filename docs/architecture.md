# Architecture

## Data flow

```mermaid
flowchart TD
    GPU[GPU on node] --> DCGM[DCGM Exporter :9400]
    DCGM -->|ServiceMonitor or scrape_config| PROM[Prometheus]
    PROM -->|recording rules| PROM
    PROM -->|alert rules| AM[Alertmanager]
    PROM -->|datasource| GRAF[Grafana]
    GRAF --> D1[Fleet Overview]
    GRAF --> D2[Workload Diagnostics]
    GRAF --> D3[Operational Health]
    VAL[gpuobs CLI] -. query API .-> PROM
    VAL -. scrape .-> DCGM
```

## Ownership boundary

| Concern | Owner |
| --- | --- |
| GPU driver, device plugin, DCGM Exporter deployment | `gpu-kubernetes-platform` (GPU Operator) |
| Scrape/discovery of the exporter | this repo (`prometheus/`) |
| Recording rules, alerts | this repo (`prometheus/rules/`) |
| Dashboards + provisioning | this repo (`dashboards/`, `grafana/`) |
| Prometheus/Grafana lifecycle | upstream kube-prometheus-stack chart (`helm/`) |
| Pipeline validation | this repo (`src/gpuobs/`) |

## Validator internals

The `gpuobs` package keeps I/O at the edges so the logic is testable offline:

```mermaid
flowchart LR
    CLI[cli] --> PROM[prom<br/>HTTP, timeouts, retries]
    CLI --> CH[checks]
    CH --> PARSE[parse<br/>pure]
    CH --> MET[metrics<br/>registry]
    CH --> PROM
    CLI --> RPT[report<br/>text/json]
    CLI --> RULES[rules]
    CLI --> DASH[dashboards]
```

`parse`, `metrics`, `rules`, and `dashboards` are pure (no network); only `prom`
touches the network, and its fetch function is injectable, which is how the
checks are unit-tested against fixed payloads.
