"""Validation of Grafana dashboard JSON.

Enforces that dashboards are provisionable and that every graph panel actually
queries something -- guarding against the "empty or misleading panel" failure
mode called out in the project requirements.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gpuobs.checks import CheckResult, Status

# Panel types that are decorative and legitimately have no query targets.
_NON_QUERY_PANELS = {"row", "text", "dashlist", "news"}


def _panel_errors(panel: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    ptype = panel.get("type", "")
    title = panel.get("title", "<untitled>")
    # Nested panels inside a collapsed row.
    for i, child in enumerate(panel.get("panels", []) or []):
        errors.extend(_panel_errors(child, f"{path}.panels[{i}]"))
    if ptype in _NON_QUERY_PANELS:
        return errors
    targets = panel.get("targets")
    if not targets:
        errors.append(f"{path} panel {title!r} ({ptype}) has no targets")
        return errors
    for ti, target in enumerate(targets):
        expr = target.get("expr")
        if not expr or not str(expr).strip():
            errors.append(f"{path} panel {title!r} target #{ti} has an empty expr")
    return errors


def validate_dashboard(path: Path) -> CheckResult:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return CheckResult(path.name, Status.FAIL, f"invalid JSON: {exc}")
    if not isinstance(doc, dict):
        return CheckResult(path.name, Status.FAIL, "dashboard is not a JSON object")
    if not doc.get("title"):
        return CheckResult(path.name, Status.FAIL, "dashboard has no title")
    panels = doc.get("panels")
    if not isinstance(panels, list) or not panels:
        return CheckResult(path.name, Status.FAIL, "dashboard has no panels")

    errors: list[str] = []
    for i, panel in enumerate(panels):
        if not isinstance(panel, dict):
            errors.append(f"panels[{i}] is not an object")
            continue
        errors.extend(_panel_errors(panel, f"panels[{i}]"))
    if errors:
        return CheckResult(path.name, Status.FAIL, "; ".join(errors))

    # Count queryable panels for a useful success message.
    queryable = sum(
        1 for p in panels if isinstance(p, dict) and p.get("type") not in _NON_QUERY_PANELS
    )
    return CheckResult(path.name, Status.OK, f"valid ({queryable} queryable panel(s))")
