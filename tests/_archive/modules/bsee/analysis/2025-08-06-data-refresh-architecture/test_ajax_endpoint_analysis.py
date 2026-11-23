#!/usr/bin/env python3
"""
Test Hidden AJAX/JSON Endpoint Analysis for BSEE Web Interfaces

This module analyzes BSEE web interfaces to discover hidden AJAX calls,
JSON endpoints, and asynchronous data loading mechanisms that might
provide programmatic access to BSEE data.

Tests cover:
- JavaScript code analysis for AJAX calls
- XHR endpoint discovery through HTML inspection
- Form submission endpoint analysis
- Callback URL identification
- JSON data endpoint testing
- WebForm_DoCallback endpoint analysis
- DevExpress control API investigation

Based on initial research, BSEE uses DevExpress controls with callback
mechanisms and WebForm_DoCallback patterns for dynamic data loading.
"""

import base64
import json
import logging
import re
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import pytest
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AJAXEndpointAnalyzer:
    """
    Analyze BSEE web interfaces for hidden AJAX/JSON endpoints.

    This class systematically examines BSEE web pages to identify
    asynchronous data loading mechanisms and potential API endpoints
    hidden within the web interface infrastructure.
    """

    def __init__(self):
        # Known BSEE web interfaces
        self.target_interfaces = [
            "https://www.data.bsee.gov/Production/OCSProduction/Default.aspx",
            "https://www.data.bsee.gov/Well/API/Default.aspx",
            "https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx",
            "https://www.data.bsee.gov/Main/RawData.aspx",
        ]

        # AJAX/JSON endpoint patterns to look for
        self.ajax_patterns = [
            r"\.ajax\s*\(",
            r"XMLHttpRequest",
            r"fetch\s*\(",
            r"WebForm_DoCallback",
            r"callback\s*:",
            r'url\s*:\s*["\']([^"\']+)["\']',
            r"data\s*:\s*\{",
            r'contentType\s*:\s*["\']application/json["\']',
        ]

        # DevExpress specific patterns (identified in initial research)
        self.devexpress_patterns = [
            r"ASPx\w+",
            r"ClientSideEvents",
            r"CallbackPanel",
            r"__doPostBack",
            r"WebForm_DoCallback",
        ]

        # Common callback parameter patterns
        self.callback_patterns = [
            r"callback\s*=\s*([^&\s]+)",
            r"__EVENTARGUMENT",
            r"__EVENTTARGET",
            r"__VIEWSTATE",
            r"__CALLBACKID",
        ]

        self.findings = []
        self.discovered_endpoints = []
        self.ajax_calls_found = []
        self.callback_mechanisms = []

    def analyze_page_ajax_calls(self, url: str) -> Dict:
        """
        Analyze a web page for AJAX calls and dynamic data loading.

        Returns comprehensive analysis of AJAX mechanisms found on the page.
        """
        result = {
            "url": url,
            "analysis_successful": False,
            "page_title": "",
            "ajax_calls_found": [],
            "json_endpoints_found": [],
            "callback_mechanisms_found": [],
            "devexpress_controls_found": [],
            "form_endpoints_found": [],
            "javascript_apis_found": [],
            "error_details": None,
        }

        try:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "BSEE-AJAX-Analysis/1.0",
            }

            response = requests.get(url, timeout=20)

            if response.status_code == 200:
                result["analysis_successful"] = True
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract page title
                title_tag = soup.find("title")
                if title_tag:
                    result["page_title"] = title_tag.get_text().strip()

                # Analyze JavaScript code
                self._analyze_javascript_code(soup, result)

                # Analyze forms for submission endpoints
                self._analyze_form_endpoints(soup, result)

                # Look for DevExpress controls
                self._analyze_devexpress_controls(response.text, result)

                # Search for callback mechanisms
                self._analyze_callback_mechanisms(response.text, result)

                # Store discovered endpoints
                self.discovered_endpoints.extend(result["json_endpoints_found"])
                self.ajax_calls_found.extend(result["ajax_calls_found"])
                self.callback_mechanisms.extend(result["callback_mechanisms_found"])

        except requests.RequestException as e:
            result["error_details"] = str(e)

        return result

    def _analyze_javascript_code(self, soup, result):
        """Analyze JavaScript code for AJAX calls and API endpoints."""
        scripts = soup.find_all("script")

        for script in scripts:
            if script.string:
                script_content = script.string

                # Look for AJAX patterns
                for pattern in self.ajax_patterns:
                    matches = re.findall(pattern, script_content, re.IGNORECASE)
                    if matches:
                        ajax_call = {
                            "pattern": pattern,
                            "matches": matches,
                            "script_snippet": (
                                script_content[:200] + "..."
                                if len(script_content) > 200
                                else script_content
                            ),
                        }
                        result["ajax_calls_found"].append(ajax_call)

                # Look for URL endpoints
                url_matches = re.findall(
                    r'url\s*:\s*["\']([^"\']+)["\']', script_content, re.IGNORECASE
                )
                for url_match in url_matches:
                    if any(
                        ext in url_match.lower()
                        for ext in [".aspx", ".ashx", ".asmx", "/api/", "json"]
                    ):
                        full_url = urljoin(result["url"], url_match)
                        result["json_endpoints_found"].append(full_url)

                # Look for fetch() calls
                fetch_matches = re.findall(
                    r'fetch\s*\(\s*["\']([^"\']+)["\']', script_content, re.IGNORECASE
                )
                for fetch_url in fetch_matches:
                    full_url = urljoin(result["url"], fetch_url)
                    result["javascript_apis_found"].append(full_url)

    def _analyze_form_endpoints(self, soup, result):
        """Analyze HTML forms for submission endpoints."""
        forms = soup.find_all("form")

        for form in forms:
            action = form.get("action", "")
            method = form.get("method", "GET").upper()

            if action:
                full_url = urljoin(result["url"], action)
                form_info = {
                    "url": full_url,
                    "method": method,
                    "id": form.get("id", ""),
                    "name": form.get("name", ""),
                }
                result["form_endpoints_found"].append(form_info)

    def _analyze_devexpress_controls(self, page_content, result):
        """Analyze DevExpress controls and their callback mechanisms."""
        for pattern in self.devexpress_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                control_info = {
                    "pattern": pattern,
                    "count": len(matches),
                    "unique_matches": list(set(matches)),
                }
                result["devexpress_controls_found"].append(control_info)

        # Look for specific DevExpress callback patterns
        callback_patterns = [
            r'ASPx\.Callback\s*\(\s*["\']([^"\']+)["\']',
            r'WebForm_DoCallback\s*\(\s*["\']([^"\']+)["\']',
            r'__doPostBack\s*\(\s*["\']([^"\']+)["\']',
        ]

        for pattern in callback_patterns:
            matches = re.findall(pattern, page_content)
            if matches:
                for match in matches:
                    callback_info = {
                        "type": "devexpress_callback",
                        "target": match,
                        "pattern": pattern,
                    }
                    result["callback_mechanisms_found"].append(callback_info)

    def _analyze_callback_mechanisms(self, page_content, result):
        """Analyze general callback and postback mechanisms."""
        # Look for ViewState and other ASP.NET mechanisms
        viewstate_match = re.search(
            r'__VIEWSTATE["\']?\s*value\s*=\s*["\']([^"\']+)["\']', page_content
        )
        if viewstate_match:
            callback_info = {
                "type": "aspnet_viewstate",
                "mechanism": "__VIEWSTATE",
                "has_value": True,
            }
            result["callback_mechanisms_found"].append(callback_info)

        # Look for event validation
        event_validation = re.search(
            r'__EVENTVALIDATION["\']?\s*value\s*=\s*["\']([^"\']+)["\']', page_content
        )
        if event_validation:
            callback_info = {
                "type": "aspnet_event_validation",
                "mechanism": "__EVENTVALIDATION",
                "has_value": True,
            }
            result["callback_mechanisms_found"].append(callback_info)

    def test_discovered_endpoints(self) -> Dict:
        """
        Test discovered AJAX/JSON endpoints for functionality.

        Attempts to access discovered endpoints to validate they're working APIs.
        """
        result = {
            "total_endpoints": len(self.discovered_endpoints),
            "tested_endpoints": 0,
            "working_endpoints": [],
            "failed_endpoints": [],
            "json_responses": [],
            "endpoint_details": [],
        }

        # Remove duplicates
        unique_endpoints = list(set(self.discovered_endpoints))

        for endpoint_url in unique_endpoints[:15]:  # Limit testing
            try:
                # Try both GET and POST methods
                methods_to_test = ["GET", "POST"]

                for method in methods_to_test:
                    response = requests.request(method, endpoint_url, timeout=10)
                    result["tested_endpoints"] += 1

                    endpoint_details = {
                        "url": endpoint_url,
                        "method": method,
                        "accessible": response.status_code == 200,
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type", ""),
                        "has_json": False,
                        "content_length": len(response.content),
                    }

                    if response.status_code == 200:
                        result["working_endpoints"].append(f"{method} {endpoint_url}")

                        # Check for JSON response
                        try:
                            json_data = response.json()
                            endpoint_details["has_json"] = True
                            result["json_responses"].append(
                                {
                                    "url": endpoint_url,
                                    "method": method,
                                    "json_keys": (
                                        list(json_data.keys())
                                        if isinstance(json_data, dict)
                                        else []
                                    ),
                                }
                            )
                        except ValueError:
                            pass
                    else:
                        result["failed_endpoints"].append(f"{method} {endpoint_url}")

                    result["endpoint_details"].append(endpoint_details)

                    # If GET worked, don't test POST
                    if response.status_code == 200:
                        break

            except requests.RequestException as e:
                result["failed_endpoints"].append(f"ERROR {endpoint_url}")
                result["endpoint_details"].append(
                    {"url": endpoint_url, "error": str(e), "accessible": False}
                )

        return result

    def analyze_network_patterns(self, page_content: str) -> Dict:
        """
        Analyze network request patterns embedded in page content.

        Looks for patterns that indicate dynamic data loading mechanisms.
        """
        result = {
            "async_patterns_found": [],
            "data_loading_indicators": [],
            "api_like_endpoints": [],
            "json_data_structures": [],
        }

        # Look for asynchronous loading patterns
        async_patterns = [
            r"async\s*:\s*true",
            r'dataType\s*:\s*["\']json["\']',
            r"success\s*:\s*function",
            r"complete\s*:\s*function",
            r"beforeSend\s*:\s*function",
        ]

        for pattern in async_patterns:
            if re.search(pattern, page_content, re.IGNORECASE):
                result["async_patterns_found"].append(pattern)

        # Look for data loading indicators
        loading_patterns = [
            "loading",
            "spinner",
            "progress",
            "wait",
            "fetching",
            "retrieving",
        ]

        for pattern in loading_patterns:
            if pattern in page_content.lower():
                result["data_loading_indicators"].append(pattern)

        # Look for embedded JSON data
        json_pattern = r'\{[^}]*["\'][^"\']*["\'][^}]*\}'
        json_matches = re.findall(json_pattern, page_content)

        for match in json_matches[:10]:  # Limit to first 10
            try:
                json.loads(match)
                result["json_data_structures"].append(
                    match[:100] + "..." if len(match) > 100 else match
                )
            except json.JSONDecodeError:
                pass

        return result

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


class TestAJAXEndpointAnalysis:
    """Test suite for AJAX/JSON endpoint analysis of BSEE web interfaces."""

    def setup_method(self):
        """Initialize AJAX endpoint analyzer for each test."""
        self.ajax_analyzer = AJAXEndpointAnalyzer()

    def test_web_interface_ajax_analysis(self):
        """
        Test 1.6a: Analyze BSEE web interfaces for AJAX calls.

        Systematically analyzes known BSEE web interfaces to identify
        AJAX calls, JSON endpoints, and dynamic data loading mechanisms.
        """
        analyzed_interfaces = []
        total_ajax_calls = 0
        total_endpoints = 0

        for interface_url in self.ajax_analyzer.target_interfaces:
            result = self.ajax_analyzer.analyze_page_ajax_calls(interface_url)

            if result["analysis_successful"]:
                analyzed_interfaces.append(result)
                total_ajax_calls += len(result["ajax_calls_found"])
                total_endpoints += len(result["json_endpoints_found"])

                self.ajax_analyzer.document_finding(
                    "AJAX Analysis",
                    f"Analyzed {interface_url}",
                    {
                        "page_title": result["page_title"],
                        "ajax_calls_count": len(result["ajax_calls_found"]),
                        "json_endpoints_count": len(result["json_endpoints_found"]),
                        "callback_mechanisms_count": len(
                            result["callback_mechanisms_found"]
                        ),
                        "devexpress_controls_count": len(
                            result["devexpress_controls_found"]
                        ),
                    },
                )

                # Document significant findings
                if result["ajax_calls_found"]:
                    for ajax_call in result["ajax_calls_found"]:
                        self.ajax_analyzer.document_finding(
                            "AJAX Call Found",
                            f"AJAX pattern detected: {ajax_call['pattern']}",
                            ajax_call,
                        )

                if result["json_endpoints_found"]:
                    for endpoint in result["json_endpoints_found"]:
                        self.ajax_analyzer.document_finding(
                            "JSON Endpoint Found",
                            f"Potential JSON endpoint: {endpoint}",
                            {"url": endpoint},
                        )
            else:
                self.ajax_analyzer.document_finding(
                    "AJAX Analysis Failed",
                    f"Could not analyze {interface_url}",
                    {"error": result["error_details"]},
                )

        summary = {
            "interfaces_analyzed": len(analyzed_interfaces),
            "total_ajax_calls_found": total_ajax_calls,
            "total_json_endpoints_found": total_endpoints,
            "interfaces_with_ajax": len(
                [i for i in analyzed_interfaces if i["ajax_calls_found"]]
            ),
            "interfaces_with_devexpress": len(
                [i for i in analyzed_interfaces if i["devexpress_controls_found"]]
            ),
        }

        self.ajax_analyzer.document_finding(
            "AJAX Analysis Summary", f"Web interface AJAX analysis complete", summary
        )

        logger.info(
            f"AJAX analysis complete: {total_ajax_calls} AJAX calls, {total_endpoints} endpoints found"
        )
        assert True  # Always passes, documents findings

    def test_discovered_endpoint_validation(self):
        """
        Test 1.6b: Validate discovered AJAX/JSON endpoints.

        Tests the functionality of endpoints discovered through AJAX analysis.
        """
        # Ensure we have discovered endpoints by running analysis first
        if not self.ajax_analyzer.discovered_endpoints:
            for interface_url in self.ajax_analyzer.target_interfaces[:2]:
                self.ajax_analyzer.analyze_page_ajax_calls(interface_url)

        validation_result = self.ajax_analyzer.test_discovered_endpoints()

        self.ajax_analyzer.document_finding(
            "Endpoint Validation",
            f"Validated {validation_result['tested_endpoints']} discovered endpoints",
            {
                "total_endpoints_discovered": validation_result["total_endpoints"],
                "working_endpoints_count": len(validation_result["working_endpoints"]),
                "failed_endpoints_count": len(validation_result["failed_endpoints"]),
                "json_responses_count": len(validation_result["json_responses"]),
            },
        )

        # Document working endpoints
        for working_endpoint in validation_result["working_endpoints"]:
            self.ajax_analyzer.document_finding(
                "Working AJAX Endpoint",
                f"Functional endpoint: {working_endpoint}",
                {"status": "accessible"},
            )

        # Document JSON responses
        for json_response in validation_result["json_responses"]:
            self.ajax_analyzer.document_finding(
                "JSON Response Found",
                f"JSON API response: {json_response['method']} {json_response['url']}",
                json_response,
            )

        logger.info(
            f"Endpoint validation complete: {len(validation_result['working_endpoints'])} working endpoints"
        )
        assert True  # Always passes, documents findings

    def test_devexpress_callback_analysis(self):
        """
        Test 1.6c: Analyze DevExpress callback mechanisms.

        Specifically analyzes DevExpress controls and their callback mechanisms
        that were identified in the initial research.
        """
        devexpress_findings = []
        callback_mechanisms = []

        for interface_url in self.ajax_analyzer.target_interfaces:
            try:
                response = requests.get(interface_url, timeout=15)

                if response.status_code == 200:
                    # Analyze DevExpress-specific patterns
                    page_content = response.text

                    # Look for ASPx controls
                    aspx_controls = re.findall(r"ASPx(\w+)", page_content)
                    if aspx_controls:
                        devexpress_findings.append(
                            {
                                "url": interface_url,
                                "controls_found": list(set(aspx_controls)),
                                "total_controls": len(aspx_controls),
                            }
                        )

                    # Look for callback mechanisms
                    callback_patterns = [
                        r'WebForm_DoCallback\s*\(\s*["\']([^"\']+)["\']',
                        r'__doPostBack\s*\(\s*["\']([^"\']+)["\']',
                        r"ASPx\.Callback\s*\(",
                    ]

                    for pattern in callback_patterns:
                        matches = re.findall(pattern, page_content)
                        if matches:
                            callback_mechanisms.append(
                                {
                                    "url": interface_url,
                                    "pattern": pattern,
                                    "matches": matches,
                                }
                            )

            except requests.RequestException:
                continue

        # Document DevExpress findings
        for finding in devexpress_findings:
            self.ajax_analyzer.document_finding(
                "DevExpress Controls",
                f"DevExpress controls found on {finding['url']}",
                finding,
            )

        for mechanism in callback_mechanisms:
            self.ajax_analyzer.document_finding(
                "Callback Mechanism",
                f"Callback pattern found: {mechanism['pattern']}",
                mechanism,
            )

        summary = {
            "pages_with_devexpress": len(devexpress_findings),
            "total_callback_mechanisms": len(callback_mechanisms),
            "unique_control_types": list(
                set(
                    [
                        ctrl
                        for finding in devexpress_findings
                        for ctrl in finding["controls_found"]
                    ]
                )
            ),
        }

        self.ajax_analyzer.document_finding(
            "DevExpress Analysis Summary",
            "DevExpress callback mechanism analysis complete",
            summary,
        )

        logger.info(f"DevExpress analysis complete")
        assert True  # Always passes, documents findings

    def test_network_pattern_analysis(self):
        """
        Test 1.6d: Analyze network request patterns in page content.

        Examines page content for patterns that indicate dynamic data loading
        and asynchronous network requests.
        """
        all_network_patterns = []

        for interface_url in self.ajax_analyzer.target_interfaces:
            try:
                response = requests.get(interface_url, timeout=15)

                if response.status_code == 200:
                    network_analysis = self.ajax_analyzer.analyze_network_patterns(
                        response.text
                    )
                    network_analysis["url"] = interface_url
                    all_network_patterns.append(network_analysis)

                    self.ajax_analyzer.document_finding(
                        "Network Pattern Analysis",
                        f"Network patterns analyzed for {interface_url}",
                        {
                            "async_patterns_count": len(
                                network_analysis["async_patterns_found"]
                            ),
                            "loading_indicators_count": len(
                                network_analysis["data_loading_indicators"]
                            ),
                            "json_structures_count": len(
                                network_analysis["json_data_structures"]
                            ),
                        },
                    )

            except requests.RequestException:
                continue

        # Compile summary statistics
        all_async_patterns = []
        all_loading_indicators = []
        all_json_structures = []

        for analysis in all_network_patterns:
            all_async_patterns.extend(analysis["async_patterns_found"])
            all_loading_indicators.extend(analysis["data_loading_indicators"])
            all_json_structures.extend(analysis["json_data_structures"])

        summary = {
            "pages_analyzed": len(all_network_patterns),
            "unique_async_patterns": list(set(all_async_patterns)),
            "unique_loading_indicators": list(set(all_loading_indicators)),
            "total_json_structures_found": len(all_json_structures),
        }

        self.ajax_analyzer.document_finding(
            "Network Pattern Summary",
            "Network request pattern analysis complete",
            summary,
        )

        logger.info(f"Network pattern analysis complete")
        assert True  # Always passes, documents findings

    def teardown_method(self):
        """Save comprehensive AJAX endpoint analysis results."""
        if hasattr(self, "ajax_analyzer") and self.ajax_analyzer.findings:
            # Generate AJAX endpoint analysis report
            report_lines = []
            report_lines.append("# BSEE AJAX/JSON Endpoint Analysis Report")
            report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")

            # Executive Summary
            total_endpoints = len(self.ajax_analyzer.discovered_endpoints)
            total_ajax_calls = len(self.ajax_analyzer.ajax_calls_found)
            total_callbacks = len(self.ajax_analyzer.callback_mechanisms)

            report_lines.append("## Executive Summary")
            report_lines.append(f"- AJAX calls discovered: {total_ajax_calls}")
            report_lines.append(f"- JSON endpoints discovered: {total_endpoints}")
            report_lines.append(f"- Callback mechanisms found: {total_callbacks}")
            report_lines.append(
                f"- Total research findings: {len(self.ajax_analyzer.findings)}"
            )
            report_lines.append("")

            # Discovered Endpoints
            if self.ajax_analyzer.discovered_endpoints:
                report_lines.append("## Discovered AJAX/JSON Endpoints")
                unique_endpoints = list(set(self.ajax_analyzer.discovered_endpoints))
                for endpoint in unique_endpoints[:20]:
                    report_lines.append(f"- {endpoint}")
                report_lines.append("")

            # AJAX Calls Found
            if self.ajax_analyzer.ajax_calls_found:
                report_lines.append("## AJAX Calls Found")
                for ajax_call in self.ajax_analyzer.ajax_calls_found[:10]:
                    report_lines.append(f"- **Pattern**: {ajax_call['pattern']}")
                    report_lines.append(f"  - **Matches**: {ajax_call['matches']}")
                    report_lines.append("")

            # Callback Mechanisms
            if self.ajax_analyzer.callback_mechanisms:
                report_lines.append("## Callback Mechanisms")
                for callback in self.ajax_analyzer.callback_mechanisms[:10]:
                    report_lines.append(
                        f"- **Type**: {callback.get('type', 'unknown')}"
                    )
                    report_lines.append(
                        f"  - **Target**: {callback.get('target', callback.get('mechanism', 'N/A'))}"
                    )
                    report_lines.append("")

            # Detailed Findings
            report_lines.append("## Detailed Findings")

            categories = {}
            for finding in self.ajax_analyzer.findings:
                cat = finding["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(finding)

            for category, findings in categories.items():
                report_lines.append(f"### {category}")
                for finding in findings:
                    report_lines.append(
                        f"- **{finding['timestamp']}**: {finding['description']}"
                    )
                    if finding["details"]:
                        for key, value in finding["details"].items():
                            if isinstance(value, list) and len(value) > 0:
                                report_lines.append(
                                    f"  - {key}: {', '.join(map(str, value[:5]))}"
                                )
                            elif not isinstance(value, (list, dict)):
                                report_lines.append(f"  - {key}: {value}")
                report_lines.append("")

            report = "\n".join(report_lines)

            # Save report
            report_path = "tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/results/ajax_endpoint_analysis.md"
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"AJAX endpoint analysis report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Could not save report: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
