# ADR 0001: The GPU Operator owns the DCGM Exporter; this repo owns downstream

## Status

Accepted.

## Context

GPU telemetry needs the DCGM Exporter running on every GPU node, tightly coupled
to the NVIDIA driver and container toolkit versions. The NVIDIA GPU Operator
already deploys and version-matches the exporter as part of bringing up GPU
nodes (done in `gpu-kubernetes-platform`). This observability repo needs those
metrics but should not fight the operator for ownership of the exporter
deployment.

## Decision

Treat the exporter's `/metrics` endpoint as the contract boundary. The GPU
Operator owns deploying and upgrading the exporter; this repository owns scrape
configuration, recording rules, alerts, dashboards, and validation downstream of
that endpoint. We do **not** install a second DCGM Exporter.

## Alternatives considered

- **Deploy our own DCGM Exporter here.** Rejected: duplicate device access and
  version drift against the operator-managed driver; two exporters competing for
  the same GPU is a known source of scrape confusion.
- **Put rules/dashboards in the platform repo.** Rejected: couples monitoring
  changes to cluster provisioning and muddies ownership. Keeping them here lets
  monitoring evolve independently.

## Consequences

- A clean, stable contract (DCGM metric names + the `dcgm-exporter` job label)
  between the two repositories.
- This repo can be validated and demoed without the platform repo, using the
  synthetic exporter.
- If the operator changes exporter defaults (metric set, labels), this repo must
  adapt; the `gpuobs` validator exists partly to catch that drift early.
