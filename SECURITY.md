# Security

## Threat model

This repository is monitoring configuration plus a read-only validator. It:

- ships Prometheus rules, Grafana dashboards, and Helm values (static config);
- provides `gpuobs`, which makes **outbound HTTP GET** requests to a Prometheus
  or exporter endpoint you specify and reads the responses.

`gpuobs`:

- refuses any URL that is not `http://` or `https://`;
- applies a timeout and a bounded number of retries to every request, so a hung
  or flapping endpoint cannot stall it;
- requires no credentials, performs no writes, and persists nothing;
- parses YAML with `yaml.safe_load` only.

The local demo runs third-party container images (Prometheus, Grafana, a Python
base image) via docker-compose on your machine with default demo credentials
(`admin`/`admin`); it is for local use, not exposure to a network.

## What must never be committed

- Alertmanager receiver secrets (PagerDuty/Slack keys), Grafana admin passwords,
  cloud or registry credentials, kubeconfig files.
- Real scrape targets or dashboards that leak internal hostnames or topology if
  that is sensitive in your context.

CI runs gitleaks on every push and pull request, and GitHub Actions use
least-privilege (`contents: read`) permissions.

## Reporting a vulnerability

Use GitHub's "Report a vulnerability" flow on this repository, or open an issue
without sensitive detail. Fixes ship as normal releases.
