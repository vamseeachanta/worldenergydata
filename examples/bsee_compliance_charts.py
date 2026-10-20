"""Write compliance charts for synthetic inputs to an explicit output folder.

See docs/domains/bsee/compliance-chart-inputs.md for the hand calculation
and the distinction between presentation policy and regulatory assessment.
"""

import argparse
import json
from pathlib import Path

from worldenergydata.bsee.reports.comprehensive.templates.compliance_models import (
    ComplianceMetrics,
    SafetyMetrics,
)
from worldenergydata.bsee.reports.comprehensive.templates.compliance_template import (
    ComplianceTemplate,
)


def main():
    """Render the worked example without requiring production data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)

    # Synthetic example inputs; no measured operating data is represented.
    # Percent basis: NIST SP 811 section 7.10.2, online revision 2025.
    production = ComplianceMetrics(
        permitted_production_bbls=100000, actual_production_bbls=110000
    )
    # Repository policy: compliance_models.py::SafetyMetrics, d867ba1e (2026).
    # 1 + min(0.1, 12 * 0.01) + min(0.05, 1000 * 0.001) is capped to 1.
    safety = SafetyMetrics(safety_inspections=12, safety_training_hours=1000)
    inputs = {
        "production_compliance": production.production_compliance_percentage(),
        "safety_score": safety.calculate_safety_score(),
        "environmental_score": None,
        "overall_compliance_score": None,
    }
    template = ComplianceTemplate(template_path=output)
    template.context["quota_analysis"] = {
        "oil_quota": production.permitted_production_bbls,
        "oil_actual": production.actual_production_bbls,
    }
    for name, html in template.generate_compliance_visualizations(inputs).items():
        (output / f"{name}.html").write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "production_compliance_pct": round(inputs["production_compliance"], 1),
                "safety_score": inputs["safety_score"],
                "not_evaluated": [
                    "environmental_score",
                    "overall_compliance_score",
                    "gas_quota",
                    "gas_actual",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
