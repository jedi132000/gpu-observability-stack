"""Structural validation of Prometheus recording/alerting rule files.

This validates shape and the conventions this repository enforces (every alert
has a severity label and summary/description annotations). It is complementary
to ``promtool check rules``, which validates PromQL syntax and runs in CI; this
check runs with no external binary so it works anywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from gpuobs.checks import CheckResult, Status


def _validate_doc(doc: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, dict) or "groups" not in doc:
        return ["file has no top-level 'groups' key"]
    groups = doc.get("groups")
    if not isinstance(groups, list) or not groups:
        return ["'groups' must be a non-empty list"]
    for gi, group in enumerate(groups):
        gname = group.get("name", f"#{gi}") if isinstance(group, dict) else f"#{gi}"
        if not isinstance(group, dict) or "name" not in group:
            errors.append(f"group {gname}: missing 'name'")
            continue
        rules = group.get("rules")
        if not isinstance(rules, list) or not rules:
            errors.append(f"group {gname}: 'rules' must be a non-empty list")
            continue
        for ri, rule in enumerate(rules):
            errors.extend(_validate_rule(gname, ri, rule))
    return errors


def _validate_rule(gname: str, ri: int, rule: Any) -> list[str]:
    where = f"group {gname} rule #{ri}"
    if not isinstance(rule, dict):
        return [f"{where}: not a mapping"]
    is_alert = "alert" in rule
    is_record = "record" in rule
    if is_alert == is_record:
        return [f"{where}: must have exactly one of 'alert' or 'record'"]
    if not rule.get("expr"):
        return [f"{where}: missing 'expr'"]
    if not is_alert:
        return []

    name = rule["alert"]
    errs: list[str] = []
    labels = rule.get("labels") or {}
    if "severity" not in labels:
        errs.append(f"alert {name}: missing labels.severity")
    elif labels["severity"] not in {"critical", "warning", "info"}:
        errs.append(f"alert {name}: severity {labels['severity']!r} is not critical/warning/info")
    annotations = rule.get("annotations") or {}
    for required in ("summary", "description"):
        if required not in annotations:
            errs.append(f"alert {name}: missing annotations.{required}")
    if "for" not in rule:
        # Not fatal, but flag it: alerts without 'for' fire on a single scrape.
        errs.append(f"alert {name}: no 'for' duration (will fire on a single sample)")
    return errs


def validate_rule_file(path: Path) -> CheckResult:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return CheckResult(path.name, Status.FAIL, f"could not read/parse: {exc}")
    errors = _validate_doc(doc)
    if errors:
        return CheckResult(path.name, Status.FAIL, "; ".join(errors))
    return CheckResult(path.name, Status.OK, "rule file is well-formed")
