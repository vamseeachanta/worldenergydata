"""
Compliance References for regulatory compliance reporting.

This module contains regulatory reference data and functions for
BSEE regulatory compliance documentation.
"""

from datetime import datetime
from typing import Any, Dict, List


def get_regulatory_references() -> List[Dict[str, Any]]:
    """Get comprehensive list of regulatory references"""
    return [
        # Core BSEE Production Regulations
        {
            "category": "Production Reporting",
            "title": "BSEE Production Reporting Requirements",
            "regulation": "30 CFR 250.1160",
            "url": "https://www.bsee.gov/guidance-and-regulations/regulations/30-cfr-250-oil-and-gas-and-sulphur-operations-in-the-ocs/subpart-l-oil-and-gas-production-measurement-surface-commingling-and-security",
            "description": "Requirements for monthly production reporting to BSEE",
            "compliance_area": "production",
            "frequency": "monthly",
            "penalties": "Civil penalties up to $44,539 per day per violation",
        },
        {
            "category": "Production Reporting",
            "title": "Well Production Casing Pressure Requirements",
            "regulation": "30 CFR 250.804",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-H/section-250.804",
            "description": "Requirements for monitoring and reporting well casing pressures",
            "compliance_area": "production",
            "frequency": "continuous_monitoring",
            "penalties": "Shutdown orders and civil penalties",
        },
        # Environmental Compliance Regulations
        {
            "category": "Environmental Compliance",
            "title": "Environmental Compliance Requirements",
            "regulation": "30 CFR 250.300",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-C",
            "description": "Environmental compliance and pollution prevention requirements",
            "compliance_area": "environmental",
            "frequency": "ongoing",
            "penalties": "Civil penalties and operational restrictions",
        },
        {
            "category": "Environmental Compliance",
            "title": "Spill Response and Reporting",
            "regulation": "30 CFR 254",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-254",
            "description": "Oil spill response planning and incident reporting requirements",
            "compliance_area": "environmental",
            "frequency": "immediate_reporting",
            "penalties": "Civil penalties up to $44,539 per day per violation",
        },
        {
            "category": "Environmental Compliance",
            "title": "Air Quality Requirements",
            "regulation": "40 CFR 60 Subpart OOOO",
            "url": "https://www.ecfr.gov/current/title-40/chapter-I/subchapter-C/part-60/subpart-OOOO",
            "description": "Standards of performance for crude oil and natural gas facilities",
            "compliance_area": "environmental",
            "frequency": "ongoing_monitoring",
            "penalties": "EPA civil penalties up to $37,500 per day per violation",
        },
        # Safety and Management System Regulations
        {
            "category": "Safety Management",
            "title": "Safety and Environmental Management System (SEMS)",
            "regulation": "30 CFR 250.1900",
            "url": "https://www.bsee.gov/what-we-do/offshore-regulatory-programs/sems",
            "description": "Safety and Environmental Management System requirements",
            "compliance_area": "safety",
            "frequency": "annual_audit",
            "penalties": "Operational shutdowns and civil penalties",
        },
        {
            "category": "Safety Management",
            "title": "Incident Reporting Requirements",
            "regulation": "30 CFR 250.188",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-B/section-250.188",
            "description": "Requirements for reporting incidents and accidents",
            "compliance_area": "safety",
            "frequency": "immediate_reporting",
            "penalties": "Civil penalties and potential criminal liability",
        },
        # Financial Assurance and Bonding
        {
            "category": "Financial Assurance",
            "title": "Supplemental Bonding Requirements",
            "regulation": "30 CFR 250.1700",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-Q",
            "description": "Financial assurance requirements for offshore operations",
            "compliance_area": "financial",
            "frequency": "periodic_review",
            "penalties": "Lease cancellation and forfeiture",
        },
        # Inspection and Enforcement
        {
            "category": "Inspection and Enforcement",
            "title": "Inspection Requirements and Procedures",
            "regulation": "30 CFR 250.130",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-B/section-250.130",
            "description": "BSEE inspection authority and facility access requirements",
            "compliance_area": "operational",
            "frequency": "unscheduled",
            "penalties": "Operational restrictions and civil penalties",
        },
        {
            "category": "Inspection and Enforcement",
            "title": "Civil Penalty Procedures",
            "regulation": "30 CFR 550.1400",
            "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-550/subpart-N",
            "description": "Civil penalty assessment and appeal procedures",
            "compliance_area": "enforcement",
            "frequency": "as_needed",
            "penalties": "Varies by violation type and severity",
        },
    ]


def get_quick_references() -> List[Dict[str, Any]]:
    """Get quick reference guides"""
    return [
        {
            "category": "Quick Reference",
            "title": "BSEE Compliance Checklist",
            "regulation": "BSEE Guidance",
            "url": "https://www.bsee.gov/sites/bsee.gov/files/guidance-and-regulations/guidance/notices-to-lessees-ntl/bsee-compliance-checklist.pdf",
            "description": "Comprehensive compliance checklist for offshore operations",
            "compliance_area": "all",
            "frequency": "reference_document",
        },
        {
            "category": "Quick Reference",
            "title": "Emergency Contact Information",
            "regulation": "BSEE Emergency Response",
            "url": "https://www.bsee.gov/what-we-do/emergency-response",
            "description": "Emergency contact information and reporting procedures",
            "compliance_area": "emergency",
            "frequency": "immediate_access",
        },
    ]


def get_all_references() -> List[Dict[str, Any]]:
    """Get all regulatory references including quick references"""
    return get_regulatory_references() + get_quick_references()


def get_reference_metadata(references: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate metadata about regulatory references"""
    return {
        "total_references": len(references),
        "categories": list(set([ref["category"] for ref in references])),
        "compliance_areas": list(
            set(
                [
                    ref["compliance_area"]
                    for ref in references
                    if ref.get("compliance_area")
                ]
            )
        ),
        "last_updated": datetime.now().isoformat(),
        "disclaimer": "Regulatory references are provided for guidance only. Always consult current CFR text and legal counsel for authoritative interpretation.",
    }


def filter_references_by_category(
    references: List[Dict[str, Any]], category: str
) -> List[Dict[str, Any]]:
    """Filter references by category"""
    return [ref for ref in references if ref.get("category") == category]


def filter_references_by_compliance_area(
    references: List[Dict[str, Any]], area: str
) -> List[Dict[str, Any]]:
    """Filter references by compliance area"""
    return [ref for ref in references if ref.get("compliance_area") == area]


# Public API
__all__ = [
    "get_regulatory_references",
    "get_quick_references",
    "get_all_references",
    "get_reference_metadata",
    "filter_references_by_category",
    "filter_references_by_compliance_area",
]
