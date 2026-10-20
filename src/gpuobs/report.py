"""Render check results as text or JSON."""

from __future__ import annotations

import json

from gpuobs.checks import CheckResult, Status, overall_status

_SYMBOL = {
    Status.OK: "[ OK ]",
    Status.WARN: "[WARN]",
    Status.FAIL: "[FAIL]",
    Status.SKIP: "[SKIP]",
}


def render_text(title: str, results: list[CheckResult]) -> str:
    lines = [title, "=" * len(title), ""]
    width = max((len(r.name) for r in results), default=0)
    for r in results:
        lines.append(f"{_SYMBOL[r.status]} {r.name:<{width}}  {r.detail}")
    lines.append("")
    lines.append(f"overall: {overall_status(results).value}")
    return "\n".join(lines)


def render_json(title: str, results: list[CheckResult]) -> str:
    payload = {
        "title": title,
        "overall": overall_status(results).value,
        "checks": [{"name": r.name, "status": r.status.value, "detail": r.detail} for r in results],
    }
    return json.dumps(payload, indent=2)
