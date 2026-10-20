# Engineering evidence

Recorded from the development environment. Static checks are reproducible; the
demo requires Docker.

## Environment

- OS: Windows 11 (local dev); CI: `ubuntu-latest`.
- Python: 3.13.5 locally; CI matrix 3.10 and 3.12.
- Key packages: prometheus-client 0.26.0, typer 0.25.1, PyYAML 6.0.3.
- Tooling: ruff 0.17.0, mypy 2.4.0, pytest 9.1.1.

## Commands and results

| Command | Result |
| --- | --- |
| `ruff check src tests` | pass — "All checks passed!" |
| `mypy` (strict) | pass — "no issues found in 9 source files" |
| `pytest -q` | pass — 31 passed |
| `gpuobs validate-rules prometheus/rules` | pass — both rule files well-formed |
| `gpuobs validate-dashboards dashboards` | pass — 3 dashboards valid (6/7/4 queryable panels) |

## Demo exporter self-check

The synthetic exporter's output was generated offline and run through
`gpuobs check-exporter`:

```
OK    exporter-reachable: scraped 38 samples
OK    required-metrics: all 5 required families present
OK    optional-metrics: optional health families present
OK    kube-labels: pod/namespace labels present on GPU metrics
OVERALL: OK
```

Every synthetic series carries `synthetic="true"`; the output is demo data, not
real GPU telemetry.

## Hardware validation status

**Not performed.** No GPU was available. The exporter integration, rules, and
dashboards were validated structurally and against synthetic data only. Behavior
against real DCGM metrics on NVIDIA hardware is unverified and should be
confirmed on a GPU cluster before production use.

## PromQL syntax (promtool)

`promtool check rules` runs in CI (it needs the Prometheus toolchain). Locally
it is skipped by `scripts/validate.sh` when `promtool` is not installed, and the
skip is printed rather than counted as a pass.
