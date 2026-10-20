# AGENTS.md

Operational guide for working on this repository (human or agent).

## Layout

```
src/gpuobs/
  metrics.py     the DCGM families/labels the stack depends on (source of truth).
  parse.py       pure parsing of exposition text + query JSON (no I/O).
  prom.py        HTTP clients (timeouts, bounded retries, injectable fetch).
  checks.py      validation checks + status aggregation + exit codes.
  rules.py       structural validation of Prometheus rule files.
  dashboards.py  structural validation of Grafana dashboard JSON.
  report.py      text/JSON rendering.
  cli.py         Typer commands; owns exit codes and output format.
prometheus/      rules (recording + alert), ServiceMonitor, scrape config.
dashboards/      three Grafana dashboard JSON files.
grafana/         datasource + dashboard provisioning.
helm/            kube-prometheus-stack values overlay.
examples/        synthetic exporter + docker-compose demo.
scripts/         validate.sh (static), run-demo.sh.
docs/            metrics, architecture, runbooks, ADRs, evidence.
```

Only `prom.py` performs network I/O; everything else is pure and unit-tested.
Keep it that way — it is what makes the checks testable offline.

## Conventions

- Python 3.10+, full type hints, `from __future__ import annotations`.
- Metric names live in `metrics.py` only. Do not hardcode DCGM names elsewhere;
  reference the registry so the validator and rules cannot drift.
- Only reference metrics that exist in supported DCGM Exporter releases. If you
  add one, document it in `docs/metrics.md` and decide required vs optional.
- Alerts must have a `severity` label, `summary` + `description` annotations,
  and a `for` duration. `rules.py` enforces this and CI runs promtool.
- Dashboard panels must query a real metric; empty panels are rejected by
  `dashboards.py`.

## Build and validation

```bash
pip install -e '.[dev]'
ruff check src tests
mypy
pytest -q
./scripts/validate.sh        # gpuobs rule/dashboard checks (+ promtool if present)
```

CI additionally runs `promtool check rules` (PromQL syntax) and gitleaks.

## Demo

```bash
docker compose -f examples/docker-compose.yaml up
gpuobs check-prometheus --url http://localhost:9090 --job dcgm-exporter
```

The demo exporter is synthetic. Never remove the `synthetic="true"` label or the
banner, and never present demo output as real telemetry (see ADR 0002).

## Security rules

- Parse YAML with `yaml.safe_load` only.
- The validator must refuse non-HTTP(S) URLs and keep timeouts + bounded retries
  on every request. Do not add unauthenticated write operations.

## What not to change casually

- The `dcgm-exporter` job name — rules, ServiceMonitor, demo, and the validator
  all depend on it.
- The DCGM/operator ownership boundary (ADR 0001): do not add a second exporter.
- The purity of everything except `prom.py`.
