"""
Configurable Legal Metrology compliance rule engine.
Operates ONLY on extracted declarations from the current image OCR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.extraction import ExtractedDeclaration, declarations_to_map

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "legal_metrology_rules.json"


@dataclass
class RuleResult:
    rule_id: str
    status: str  # PASS | FAIL | WARNING | NOT_DETECTED | NOT_APPLICABLE
    severity: str
    message: str
    recommendation: str
    field_key: str
    field_label: str | None = None
    value: str | None = None
    confidence: float = 0.0


def load_ruleset() -> dict[str, Any]:
    with RULES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _status_for_field(
    rule: dict[str, Any],
    decl: ExtractedDeclaration | None,
) -> RuleResult:
    required = bool(rule.get("required", False))
    applicability = rule.get("applicability", "always")
    severity = rule.get("severity", "MEDIUM")
    field_key = rule["field_key"]

    found = bool(decl and decl.found and decl.value)
    confidence = decl.confidence if decl else 0.0
    value = decl.value if decl else None
    label = decl.field_label if decl else rule.get("name")

    if field_key == "_readability":
        status = (decl.status if decl else "WARNING") or "WARNING"
        if status == "PASS":
            message = "Readability screening indicates text is adequate for automated OCR review."
            recommendation = (
                "Still verify physically. This is not a legal font-size determination."
            )
        else:
            message = rule.get("warning_message", "Manual verification required.")
            recommendation = rule.get(
                "warning_recommendation",
                "Manual verification required.",
            )
            status = "WARNING"
        return RuleResult(
            rule_id=rule["rule_id"],
            status=status,
            severity=severity,
            message=message,
            recommendation=recommendation,
            field_key=field_key,
            field_label=label,
            value=value,
            confidence=confidence,
        )

    if found and confidence >= 0.55:
        return RuleResult(
            rule_id=rule["rule_id"],
            status="PASS",
            severity=severity,
            message=f"{rule['name']} detected from OCR text.",
            recommendation="Declaration appears present; officer should still verify authenticity/accuracy.",
            field_key=field_key,
            field_label=label,
            value=value,
            confidence=confidence,
        )

    if found and confidence < 0.55:
        return RuleResult(
            rule_id=rule["rule_id"],
            status="WARNING",
            severity=severity,
            message=rule.get("warning_message", f"{rule['name']} low confidence."),
            recommendation=rule.get(
                "warning_recommendation", "Manually verify this declaration."
            ),
            field_key=field_key,
            field_label=label,
            value=value,
            confidence=confidence,
        )

    # Not found
    if not required and applicability == "where_applicable":
        return RuleResult(
            rule_id=rule["rule_id"],
            status="NOT_APPLICABLE",
            severity=severity,
            message=rule.get(
                "warning_message",
                f"{rule['name']} not detected; may be applicable only in specific cases.",
            ),
            recommendation=rule.get(
                "warning_recommendation",
                "Confirm applicability. Absence alone is not automatically treated as illegal in this prototype.",
            ),
            field_key=field_key,
            field_label=label,
            value=None,
            confidence=0.0,
        )

    if required:
        return RuleResult(
            rule_id=rule["rule_id"],
            status="NOT_DETECTED",
            severity=severity,
            message=rule.get("fail_message", f"{rule['name']} not detected."),
            recommendation=rule.get(
                "fail_recommendation", "Capture a clearer image or check the physical label."
            ),
            field_key=field_key,
            field_label=label,
            value=None,
            confidence=0.0,
        )

    return RuleResult(
        rule_id=rule["rule_id"],
        status="WARNING",
        severity=severity,
        message=rule.get("warning_message", f"{rule['name']} not detected."),
        recommendation=rule.get("warning_recommendation", "Verify manually."),
        field_key=field_key,
        field_label=label,
        value=None,
        confidence=0.0,
    )


def evaluate_compliance(declarations: list[ExtractedDeclaration]) -> list[RuleResult]:
    ruleset = load_ruleset()
    field_map = declarations_to_map(declarations)
    results: list[RuleResult] = []

    for rule in ruleset.get("rules", []):
        field_key = rule["field_key"]

        # Combined manufacturer/packer/importer rule
        if field_key == "_manufacturer_packer_importer":
            related = rule.get("related_fields", ["manufacturer", "packer", "importer"])
            parts = []
            best_conf = 0.0
            for key in related:
                d = field_map.get(key)
                if d and d.found and d.value:
                    parts.append(f"{d.field_label}: {d.value}")
                    best_conf = max(best_conf, d.confidence)
            if parts:
                synthetic = ExtractedDeclaration(
                    field_key=field_key,
                    field_label=rule["name"],
                    value=" | ".join(parts),
                    confidence=best_conf,
                    found=True,
                    status="DETECTED",
                )
            else:
                synthetic = ExtractedDeclaration(
                    field_key=field_key,
                    field_label=rule["name"],
                    value=None,
                    confidence=0.0,
                    found=False,
                    status="NOT_DETECTED",
                )
            results.append(_status_for_field(rule, synthetic))
            continue

        results.append(_status_for_field(rule, field_map.get(field_key)))

    return results


def compute_screening_score(rule_results: list[RuleResult]) -> dict[str, Any]:
    """Dynamic Automated Screening Score from THIS scan's rule results only."""
    ruleset = load_ruleset()
    scoring = ruleset.get("scoring", {})
    pass_points = float(scoring.get("pass_points", 12))
    warning_penalty = float(scoring.get("warning_penalty", 4))
    fail_penalty = float(scoring.get("fail_penalty", 16))
    nd_penalty = float(scoring.get("not_detected_penalty", fail_penalty))
    max_score = float(scoring.get("max_score", 100))
    min_score = float(scoring.get("min_score", 0))

    passed = sum(1 for r in rule_results if r.status == "PASS")
    warnings = sum(1 for r in rule_results if r.status == "WARNING")
    failed = sum(1 for r in rule_results if r.status == "FAIL")
    not_detected = sum(1 for r in rule_results if r.status == "NOT_DETECTED")
    not_applicable = sum(1 for r in rule_results if r.status == "NOT_APPLICABLE")

    evaluated = [r for r in rule_results if r.status != "NOT_APPLICABLE"]
    denom = max(len(evaluated), 1)
    base = (passed / denom) * max_score
    alt = (
        passed * pass_points
        - warnings * warning_penalty
        - failed * fail_penalty
        - not_detected * nd_penalty
    )
    score = max(min_score, min(max_score, round((base * 0.4 + alt * 0.6), 0)))

    hard_misses = failed + not_detected
    if hard_misses >= 3 or score < 50:
        status = "Non-Compliant"
    elif hard_misses >= 1 or warnings >= 2 or score < 80:
        status = "Partially Compliant"
    else:
        status = "Compliant"

    return {
        "screening_score": float(score),
        "passed_count": passed,
        "warning_count": warnings,
        "failed_count": failed,
        "not_detected_count": not_detected,
        "not_applicable_count": not_applicable,
        "status": status,
    }


def field_status_from_rules(
    declarations: list[ExtractedDeclaration], rule_results: list[RuleResult]
) -> list[dict[str, Any]]:
    by_field = {r.field_key: r for r in rule_results}
    rows: list[dict[str, Any]] = []
    for d in declarations:
        if d.field_key.startswith("_"):
            # expose readability as its own row
            if d.field_key == "_readability":
                rr = by_field.get("_readability")
                rows.append(
                    {
                        "field_key": "readability_screening",
                        "field_label": d.field_label,
                        "value": d.value,
                        "confidence": d.confidence,
                        "status": rr.status if rr else d.status,
                    }
                )
            continue
        rr = by_field.get(d.field_key)
        if not d.found and d.status == "NOT_APPLICABLE":
            status = "NOT_APPLICABLE"
        elif not d.found:
            status = "NOT_DETECTED"
        elif rr and rr.status == "PASS":
            status = "PASS"
        elif rr and rr.status == "WARNING":
            status = "WARNING"
        else:
            status = d.status if d.status in ("DETECTED", "LOW_CONFIDENCE") else "DETECTED"
        rows.append(
            {
                "field_key": d.field_key,
                "field_label": d.field_label,
                "value": d.value,
                "confidence": d.confidence,
                "status": status,
            }
        )
    return rows
