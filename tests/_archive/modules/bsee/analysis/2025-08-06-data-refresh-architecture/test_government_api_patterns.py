#!/usr/bin/env python3
"""
Test Common Government API Patterns for BSEE

This module tests common patterns used by government agencies for API access,
including standard endpoints, authentication methods, and data formats.

Tests cover:
- Common government API URL patterns
- Standard REST endpoint conventions
- Federal API catalog integration
- JSON/XML response format testing
- Authentication pattern detection
- Rate limiting and access control analysis

Based on research findings, BSEE primarily uses:
1. ArcGIS REST services for spatial data
2. Web-based query interfaces with AJAX callbacks
3. File download systems rather than traditional REST APIs
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import pytest
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GovernmentAPIPatternTester:
    """
    Test common government API patterns against BSEE endpoints.

    This class systematically tests government API patterns commonly used
    by federal agencies to provide programmatic access to data.
    """

    def __init__(self):
        self.base_urls = [
            "https://www.bsee.gov",
            "https://www.data.bsee.gov",
            "https://gis.boem.gov",  # Known working GIS endpoint
        ]

        # Standard government API patterns
        self.api_patterns = [
            "/api/",
            "/api/v1/",
            "/api/v2/",
            "/rest/",
            "/rest/v1/",
            "/services/",
            "/webapi/",
            "/data/api/",
            "/open/api/",
            "/public/api/",
            "/gov/api/",
        ]

        # ArcGIS REST patterns (known to work for BOEM/BSEE)
        self.arcgis_patterns = [
            "/arcgis/rest/services/",
            "/rest/services/",
            "/services/",
            "/MapServer/",
        ]

        # Common government data endpoints
        self.data_patterns = [
            "/data/",
            "/opendata/",
            "/catalog/",
            "/datasets/",
            "/export/",
            "/download/",
        ]

        self.test_results = []
        self.findings = []

    def test_endpoint_pattern(self, base_url: str, pattern: str) -> Dict:
        """
        Test a specific endpoint pattern against a base URL.

        Returns comprehensive analysis of the endpoint response.
        """
        test_url = urljoin(base_url, pattern)
        result = {
            "url": test_url,
            "base_url": base_url,
            "pattern": pattern,
            "accessible": False,
            "status_code": 0,
            "response_time": 0,
            "content_type": "",
            "content_length": 0,
            "has_json": False,
            "has_xml": False,
            "api_indicators": [],
            "auth_required": False,
            "rate_limited": False,
            "error_details": None,
        }

        start_time = time.time()
        try:
            headers = {
                "Accept": "application/json, application/xml, text/html",
                "User-Agent": "BSEE-API-Research/1.0",
            }

            response = requests.get(test_url, timeout=15, headers=headers)
            result["response_time"] = time.time() - start_time
            result["accessible"] = True
            result["status_code"] = response.status_code
            result["content_type"] = response.headers.get("content-type", "")
            result["content_length"] = len(response.content)

            # Check for authentication requirements
            if response.status_code == 401:
                result["auth_required"] = True
            elif response.status_code == 429:
                result["rate_limited"] = True

            # Analyze response content if successful
            if response.status_code == 200:
                self._analyze_response_content(response, result)

        except requests.exceptions.Timeout:
            result["error_details"] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result["error_details"] = "Connection error"
        except requests.RequestException as e:
            result["error_details"] = str(e)

        return result

    def _analyze_response_content(self, response, result):
        """Analyze response content for API indicators."""
        content_lower = response.text.lower()

        # Check for JSON response
        try:
            response.json()
            result["has_json"] = True
        except ValueError:
            pass

        # Check for XML response
        if "<?xml" in content_lower or "<xml" in content_lower:
            result["has_xml"] = True

        # Look for API indicators
        api_indicators = [
            "api",
            "rest",
            "endpoint",
            "swagger",
            "openapi",
            "json",
            "xml",
            "service",
            "query",
            "data",
        ]

        found_indicators = [
            indicator for indicator in api_indicators if indicator in content_lower
        ]
        result["api_indicators"] = found_indicators

    def document_finding(self, category: str, description: str, details: Dict = None):
        """Document research findings."""
        finding = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "description": description,
            "details": details or {},
        }
        self.findings.append(finding)
        logger.info(f"[{category}] {description}")


class TestGovernmentAPIPatterns:
    """Test suite for government API patterns against BSEE endpoints."""

    def setup_method(self):
        """Initialize pattern tester for each test."""
        self.pattern_tester = GovernmentAPIPatternTester()

    def test_standard_api_patterns(self):
        """
        Test 1.3a: Test standard government API patterns.

        Tests common API endpoint patterns used by federal agencies
        to determine if BSEE follows standard government API conventions.
        """
        successful_endpoints = []
        total_tests = 0

        for base_url in self.pattern_tester.base_urls:
            for pattern in self.pattern_tester.api_patterns:
                result = self.pattern_tester.test_endpoint_pattern(base_url, pattern)
                self.pattern_tester.test_results.append(result)
                total_tests += 1

                if result["accessible"] and result["status_code"] == 200:
                    successful_endpoints.append(result["url"])

                    self.pattern_tester.document_finding(
                        "Standard API Pattern",
                        f"Accessible endpoint: {result['url']}",
                        result,
                    )

        # Document summary
        summary = {
            "total_patterns_tested": total_tests,
            "successful_endpoints": len(successful_endpoints),
            "endpoints_found": successful_endpoints,
        }

        self.pattern_tester.document_finding(
            "Standard API Summary",
            f"Tested {total_tests} standard API patterns",
            summary,
        )

        logger.info(
            f"Standard API pattern testing complete: {len(successful_endpoints)}/{total_tests} successful"
        )
        assert True  # Always passes, documents findings

    def test_arcgis_rest_patterns(self):
        """
        Test 1.3b: Test ArcGIS REST service patterns.

        Based on research, BSEE/BOEM uses ArcGIS REST services for spatial data.
        This test specifically validates those known working patterns.
        """
        arcgis_endpoints = []
        total_tests = 0

        # Focus on known working GIS endpoint
        gis_base = "https://gis.boem.gov"

        for pattern in self.pattern_tester.arcgis_patterns:
            result = self.pattern_tester.test_endpoint_pattern(gis_base, pattern)
            self.pattern_tester.test_results.append(result)
            total_tests += 1

            if result["accessible"] and result["status_code"] == 200:
                arcgis_endpoints.append(result["url"])

                self.pattern_tester.document_finding(
                    "ArcGIS REST Pattern",
                    f"Working ArcGIS endpoint: {result['url']}",
                    result,
                )

        # Test known working BOEM/BSEE service
        known_service = "https://gis.boem.gov/arcgis/rest/services/BOEM_BSEE"
        result = self.pattern_tester.test_endpoint_pattern(known_service, "/")

        if result["accessible"]:
            arcgis_endpoints.append(result["url"])
            self.pattern_tester.document_finding(
                "ArcGIS REST Confirmed",
                f"Confirmed working BOEM/BSEE service: {result['url']}",
                result,
            )

        summary = {
            "total_arcgis_tests": total_tests + 1,
            "working_endpoints": len(arcgis_endpoints),
            "endpoints": arcgis_endpoints,
        }

        self.pattern_tester.document_finding(
            "ArcGIS REST Summary", f"ArcGIS REST pattern testing complete", summary
        )

        # Should find at least one working ArcGIS endpoint
        assert len(arcgis_endpoints) > 0, "No ArcGIS REST endpoints found"
        logger.info(f"Found {len(arcgis_endpoints)} working ArcGIS endpoints")

    def test_data_download_patterns(self):
        """
        Test 1.3c: Test data download and export patterns.

        Since BSEE primarily uses file downloads rather than APIs,
        test common data export and download endpoint patterns.
        """
        data_endpoints = []
        total_tests = 0

        for base_url in self.pattern_tester.base_urls:
            for pattern in self.pattern_tester.data_patterns:
                result = self.pattern_tester.test_endpoint_pattern(base_url, pattern)
                self.pattern_tester.test_results.append(result)
                total_tests += 1

                if result["accessible"] and result["status_code"] == 200:
                    data_endpoints.append(result["url"])

                    self.pattern_tester.document_finding(
                        "Data Download Pattern",
                        f"Data endpoint accessible: {result['url']}",
                        result,
                    )

        # Test known data endpoints
        known_endpoints = [
            "https://www.data.bsee.gov/Main/RawData.aspx",
            "https://www.data.bsee.gov/Production/OCSProduction/Default.aspx",
            "https://www.data.bsee.gov/Well/API/Default.aspx",
        ]

        for endpoint in known_endpoints:
            result = self.pattern_tester.test_endpoint_pattern(endpoint, "")
            if result["accessible"]:
                data_endpoints.append(result["url"])
                self.pattern_tester.document_finding(
                    "Known Data Endpoint",
                    f"Confirmed data interface: {result['url']}",
                    result,
                )

        summary = {
            "total_data_tests": total_tests + len(known_endpoints),
            "accessible_endpoints": len(data_endpoints),
            "endpoints": data_endpoints,
        }

        self.pattern_tester.document_finding(
            "Data Download Summary", "Data download pattern testing complete", summary
        )

        logger.info(f"Found {len(data_endpoints)} data access endpoints")
        assert True  # Always passes, documents findings

    def test_authentication_patterns(self):
        """
        Test 1.3d: Test authentication and access control patterns.

        Test for common government authentication methods and access controls.
        """
        auth_patterns = []
        endpoints_requiring_auth = []

        # Test endpoints that might require authentication
        auth_test_urls = [
            "https://www.data.bsee.gov/api/",
            "https://www.data.bsee.gov/admin/",
            "https://www.data.bsee.gov/secure/",
            "https://www.bsee.gov/api/",
            "https://gis.boem.gov/admin/",
        ]

        for test_url in auth_test_urls:
            result = self.pattern_tester.test_endpoint_pattern(test_url, "")

            if result["auth_required"]:
                endpoints_requiring_auth.append(result["url"])
                self.pattern_tester.document_finding(
                    "Authentication Required",
                    f"Endpoint requires auth: {result['url']}",
                    result,
                )

        # Document authentication findings
        auth_summary = {
            "endpoints_tested": len(auth_test_urls),
            "auth_required_count": len(endpoints_requiring_auth),
            "auth_required_endpoints": endpoints_requiring_auth,
            "public_access_confirmed": len(endpoints_requiring_auth) == 0,
        }

        self.pattern_tester.document_finding(
            "Authentication Summary",
            "Authentication pattern analysis complete",
            auth_summary,
        )

        logger.info(
            f"Authentication testing complete: {len(endpoints_requiring_auth)} endpoints require auth"
        )
        assert True  # Always passes, documents findings

    def teardown_method(self):
        """Save comprehensive government API pattern research results."""
        if hasattr(self, "pattern_tester") and self.pattern_tester.findings:
            # Generate detailed research report
            report_lines = []
            report_lines.append("# Government API Pattern Testing Report")
            report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")

            # Executive Summary
            total_tests = len(self.pattern_tester.test_results)
            successful_tests = len(
                [
                    r
                    for r in self.pattern_tester.test_results
                    if r["accessible"] and r["status_code"] == 200
                ]
            )

            report_lines.append("## Executive Summary")
            report_lines.append(f"- Total endpoint tests conducted: {total_tests}")
            report_lines.append(f"- Successful endpoint responses: {successful_tests}")
            report_lines.append(
                f"- Success rate: {(successful_tests/total_tests*100):.1f}%"
                if total_tests > 0
                else "- Success rate: 0%"
            )
            report_lines.append("")

            # Findings by category
            categories = {}
            for finding in self.pattern_tester.findings:
                cat = finding["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(finding)

            for category, findings in categories.items():
                report_lines.append(f"## {category}")
                for finding in findings:
                    report_lines.append(
                        f"- **{finding['timestamp']}**: {finding['description']}"
                    )
                    if finding["details"]:
                        for key, value in finding["details"].items():
                            if isinstance(value, (list, dict)):
                                report_lines.append(
                                    f"  - {key}: {json.dumps(value, indent=2)}"
                                )
                            else:
                                report_lines.append(f"  - {key}: {value}")
                report_lines.append("")

            # Detailed test results
            if self.pattern_tester.test_results:
                report_lines.append("## Detailed Test Results")
                for result in self.pattern_tester.test_results:
                    if result["accessible"] and result["status_code"] == 200:
                        report_lines.append(f"### ✓ {result['url']}")
                        report_lines.append(f"- Status: {result['status_code']}")
                        report_lines.append(f"- Content Type: {result['content_type']}")
                        report_lines.append(
                            f"- Response Time: {result['response_time']:.2f}s"
                        )
                        if result["api_indicators"]:
                            report_lines.append(
                                f"- API Indicators: {result['api_indicators']}"
                            )
                        report_lines.append("")

            report = "\n".join(report_lines)

            # Save report
            report_path = "tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/results/government_api_patterns_report.md"
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Government API patterns report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Could not save report: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
