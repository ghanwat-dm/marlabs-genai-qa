from __future__ import annotations

import json
from pathlib import Path

from .evaluator import ROOT, evaluate_all


def _md_value(value):
    if isinstance(value, (dict, list)):
        return "`" + json.dumps(value, ensure_ascii=False) + "`"
    return "`" + str(value) + "`"


def generate_reports() -> tuple[Path, Path]:
    report = evaluate_all()
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    json_path = reports_dir / "evaluation_report.json"
    md_path = reports_dir / "evaluation_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Offline Evaluation Report",
        "",
        "This report evaluates the twelve supplied recordings without modifying them. Expected behavior is derived from the API contract, caller lookup, policy metadata/text, effective dates, and trace evidence where the contract defines provider-error mapping.",
        "",
        "## Summary by risk area",
        "",
        "| Risk area | PASS | FAIL | NOT_EVALUATED | NOT_RUN | Denominator |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for area, counts in report["summary"]["by_risk_area"].items():
        lines.append(f"| {area} | {counts['PASS']} | {counts['FAIL']} | {counts['NOT_EVALUATED']} | {counts['NOT_RUN']} | {counts['denominator']} |")
    lines += [
        "",
        "**Overall pass percentage:** not reported. " + report["summary"]["overall_percentage_note"],
        "",
        "## Recording checks",
        "",
    ]
    for result in report["results"]:
        lines += [f"### Recording {result['recording_id']}", ""]
        for check in result["checks"]:
            lines += [
                f"- **{check['rule']}** - **{check['verdict']}**",
                f"  - Expected: {_md_value(check['expected'])}",
                f"  - Observed: {_md_value(check['observed'])}",
                f"  - Reason: {check['reason']}",
            ]
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    j, m = generate_reports()
    print(j)
    print(m)
