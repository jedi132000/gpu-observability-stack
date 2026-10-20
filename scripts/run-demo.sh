#!/usr/bin/env bash
# Bring up the local CPU-only demo (synthetic exporter -> Prometheus -> Grafana)
# and point gpuobs at it once Prometheus is scraping.
set -euo pipefail

cd "$(dirname "$0")/.."

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

echo "Starting demo stack (synthetic data, not real GPU telemetry)..."
compose -f examples/docker-compose.yaml up -d

echo "Grafana:    http://localhost:3000  (admin / admin)"
echo "Prometheus: http://localhost:9090"
echo
echo "Once targets are up (~15s), validate with:"
echo "  gpuobs check-prometheus --url http://localhost:9090 --job dcgm-exporter"
echo
echo "Tear down with: docker compose -f examples/docker-compose.yaml down"
