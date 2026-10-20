#!/usr/bin/env bash
# Static validation of the observability stack. Runs the checks that do not need
# a running Prometheus. Each tool is skipped (not failed) if it is not installed,
# and the skip is printed so it is never mistaken for a pass.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== gpuobs: validate rule files =="
python -m gpuobs.cli validate-rules prometheus/rules

echo
echo "== gpuobs: validate dashboards =="
python -m gpuobs.cli validate-dashboards dashboards

echo
if command -v promtool >/dev/null 2>&1; then
  echo "== promtool: check rules (PromQL syntax) =="
  promtool check rules prometheus/rules/*.yaml
else
  echo "SKIP promtool not installed; PromQL syntax not checked here (CI runs it)."
fi

echo
if command -v yamllint >/dev/null 2>&1; then
  echo "== yamllint =="
  yamllint prometheus grafana examples/prometheus-demo.yml || true
else
  echo "SKIP yamllint not installed."
fi

echo
echo "Static validation complete."
