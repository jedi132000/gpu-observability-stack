# Helm

This repository does not define its own chart. It provides a **values overlay**
for the upstream [kube-prometheus-stack] chart so Prometheus discovers the DCGM
exporter and loads the GPU rules and dashboards.

## Install

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
# Pin a chart version you have validated rather than taking latest.
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f kube-prometheus-stack-values.yaml
```

Then apply the exporter discovery object (for the Prometheus Operator):

```bash
kubectl apply -f ../prometheus/servicemonitor.yaml
```

## What the overlay does

- Lets Prometheus select ServiceMonitors and PrometheusRules regardless of the
  Helm release label, so the DCGM `ServiceMonitor` in `gpu-operator` is scraped.
  Tighten these selectors to your label scheme in production.
- Adds the GPU recording and alert rules as `PrometheusRule` objects. Keep them
  in sync with `../prometheus/rules/*.yaml` (that directory is the source the
  validator and CI check).
- Enables the Grafana dashboard sidecar so dashboards delivered as labelled
  ConfigMaps (`grafana_dashboard=1`) are loaded.

## Verify the overlay renders

```bash
helm template kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -f kube-prometheus-stack-values.yaml > /dev/null
```

[kube-prometheus-stack]: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
