# ADR 0002: Provide a synthetic-data demo, explicitly labeled as not real

## Status

Accepted.

## Context

Most developers who want to work on dashboards, rules, or the validator do not
have a GPU. Without a way to run the stack locally, configuration bugs (a wrong
label join, an empty panel, a malformed alert) are only found in a GPU cluster,
which is slow and scarce. But fabricating "GPU metrics" risks someone mistaking
demo output for real telemetry.

## Decision

Ship a CPU-only demo: a synthetic exporter that emits DCGM-named metrics with the
same labels a real exporter uses, wired to Prometheus and Grafana via
docker-compose. Make the synthetic nature impossible to miss:

- every series carries a `synthetic="true"` label;
- metric HELP text is suffixed `[SYNTHETIC]`;
- the process prints a banner stating it is not real GPU telemetry;
- the README, ADR, and evidence doc repeat the caveat.

## Alternatives considered

- **No local demo.** Rejected: pushes all iteration onto scarce GPU clusters and
  slows contribution.
- **Record and replay real GPU metrics.** Rejected: heavier to maintain, and a
  captured snapshot is still easy to misrepresent as live. Synthetic-but-labeled
  is clearer about what it is.

## Consequences

- Rules, dashboards, and the validator can be exercised end to end on any laptop.
- The demo validates *wiring and configuration*, not hardware behavior; this
  limitation is stated wherever the demo is described.
- The synthetic job uses the real `dcgm-exporter` job name so the shipped rules
  and `gpuobs` behave identically against demo and real data.
