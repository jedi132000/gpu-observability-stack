"""gpuobs: validation tooling for a DCGM/Prometheus/Grafana GPU observability stack.

Modules:

* :mod:`gpuobs.metrics` - the DCGM metric families this stack depends on.
* :mod:`gpuobs.parse`   - parse Prometheus exposition text and Prometheus query
  responses (pure, no I/O).
* :mod:`gpuobs.prom`    - a small HTTP client for exporters and the Prometheus
  API, with timeouts and bounded retries.
* :mod:`gpuobs.checks`  - validation checks returning structured results.
* :mod:`gpuobs.report`  - text / JSON rendering and exit-code mapping.
* :mod:`gpuobs.cli`     - the ``gpuobs`` command line.
"""

from gpuobs.checks import CheckResult, Status

__all__ = ["CheckResult", "Status", "__version__"]

__version__ = "0.1.0"
