"""Validate the shipped rule files and the rule validator itself."""

from __future__ import annotations

from pathlib import Path

import yaml

from gpuobs.checks import Status
from gpuobs.rules import _validate_doc, validate_rule_file

RULES_DIR = Path(__file__).resolve().parent.parent / "prometheus" / "rules"


def test_shipped_rule_files_are_valid() -> None:
    files = sorted(RULES_DIR.glob("*.yaml"))
    assert files, "no rule files found"
    for f in files:
        result = validate_rule_file(f)
        assert result.status is Status.OK, f"{f.name}: {result.detail}"


def test_every_shipped_alert_has_severity_and_annotations() -> None:
    for f in RULES_DIR.glob("*.yaml"):
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        for group in doc["groups"]:
            for rule in group["rules"]:
                if "alert" in rule:
                    assert rule["labels"]["severity"] in {"critical", "warning", "info"}
                    assert "summary" in rule["annotations"]
                    assert "description" in rule["annotations"]


def test_validator_rejects_alert_without_severity() -> None:
    doc = {
        "groups": [
            {
                "name": "g",
                "rules": [
                    {
                        "alert": "NoSeverity",
                        "expr": "up == 0",
                        "for": "5m",
                        "annotations": {"summary": "s", "description": "d"},
                    }
                ],
            }
        ]
    }
    errors = _validate_doc(doc)
    assert any("severity" in e for e in errors)


def test_validator_rejects_rule_that_is_both_alert_and_record() -> None:
    doc = {"groups": [{"name": "g", "rules": [{"alert": "A", "record": "r", "expr": "x"}]}]}
    errors = _validate_doc(doc)
    assert any("exactly one" in e for e in errors)


def test_validator_rejects_missing_expr() -> None:
    doc = {"groups": [{"name": "g", "rules": [{"record": "r"}]}]}
    errors = _validate_doc(doc)
    assert any("missing 'expr'" in e for e in errors)
