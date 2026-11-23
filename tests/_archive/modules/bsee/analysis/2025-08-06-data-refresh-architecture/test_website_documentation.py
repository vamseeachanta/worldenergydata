#!/usr/bin/env python3
"""
Test BSEE Website Documentation Sections for API Information

This module systematically tests BSEE websites for API documentation sections,
developer guides, technical documentation, and any references to programmatic
data access methods.

Tests cover:
- Documentation section discovery
- Developer portal identification
- Technical guide analysis
- API reference detection
- Swagger/OpenAPI documentation search
- Help and support section analysis

Based on research findings, BSEE appears to lack traditional API documentation
but provides extensive web-based query interfaces and GIS REST services.
"""

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


class BSEEDocumentationTester:
    """
    Test BSEE websites for API documentation and technical resources.

    This class systematically searches BSEE websites for any documentation
    that might reveal API endpoints or programmatic access methods.
    """

    def __init__(self):
        self.base_urls = [
            "https://www.bsee.gov",
            "https://www.data.bsee.gov",
            "https://gis.boem.gov",
        ]

        # Common documentation section patterns
        self.doc_sections = [
            "/api/",
            "/docs/",
            "/documentation/",
            "/developer/",
            "/dev/",
            "/technical/",
            "/help/",
            "/support/",
            "/guide/",
            "/manual/",
            "/reference/",
            "/swagger/",
            "/openapi/",
            "/api-docs/",
            "/developer-docs/",
            "/tech-docs/",
        ]

        # API-related keywords to search for in content
        self.api_keywords = [
            "api",
            "rest",
            "json",
            "xml",
            "endpoint",
            "web service",
            "programmatic",
            "developer",
            "integration",
            "swagger",
            "openapi",
            "curl",
            "http request",
            "authentication",
        ]

        # BSEE-specific technical keywords
        self.bsee_tech_keywords = [
            "data access",
            "query interface",
            "web service",
            "download api",
            "bulk data",
            "automated access",
            "system integration",
            "data export",
            "file api",
            "batch processing",
        ]

        self.findings = []
        self.discovered_links = set()

    def test_documentation_section(self, base_url: str, section: str) -> Dict:
        """
        Test a specific documentation section for API information.

        Returns comprehensive analysis of the documentation section.
        """
        test_url = urljoin(base_url, section)
        result = {
            "url": test_url,
            "base_url": base_url,
            "section": section,
            "accessible": False,
            "status_code": 0,
            "content_type": "",
            "page_title": "",
            "api_keywords_found": [],
            "bsee_tech_keywords_found": [],
            "links_discovered": [],
            "potential_api_refs": [],
            "documentation_type": "unknown",
            "has_code_examples": False,
            "has_technical_specs": False,
            "error_details": None,
        }

        try:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "BSEE-Documentation-Research/1.0",
            }

            response = requests.get(test_url, timeout=15, headers=headers)
            result["accessible"] = True
            result["status_code"] = response.status_code
            result["content_type"] = response.headers.get("content-type", "")

            if response.status_code == 200:
                self._analyze_documentation_content(response, result)

        except requests.exceptions.Timeout:
            result["error_details"] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result["error_details"] = "Connection error"
        except requests.RequestException as e:
            result["error_details"] = str(e)

        return result

    def _analyze_documentation_content(self, response, result):
        """Analyze documentation page content for API information."""
        content = response.text.lower()

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract page title
            title_tag = soup.find("title")
            if title_tag:
                result["page_title"] = title_tag.get_text().strip()

            # Look for API keywords
            found_api_keywords = [
                keyword for keyword in self.api_keywords if keyword in content
            ]
            result["api_keywords_found"] = found_api_keywords

            # Look for BSEE technical keywords
            found_bsee_keywords = [
                keyword for keyword in self.bsee_tech_keywords if keyword in content
            ]
            result["bsee_tech_keywords_found"] = found_bsee_keywords

            # Look for code examples
            code_indicators = [
                "<code>",
                "<pre>",
                "curl",
                "http://",
                "https://",
                "json",
                "xml",
                "<?xml",
                "application/json",
            ]
            result["has_code_examples"] = any(
                indicator in content for indicator in code_indicators
            )

            # Look for technical specifications
            tech_indicators = [
                "specification",
                "protocol",
                "format",
                "schema",
                "parameter",
                "response",
                "request",
                "header",
            ]
            result["has_technical_specs"] = any(
                indicator in content for indicator in tech_indicators
            )

            # Extract relevant links
            self._extract_relevant_links(soup, result)

            # Determine documentation type
            self._classify_documentation_type(content, result)

        except Exception as e:
            logger.warning(f"Error parsing HTML content: {e}")

    def _extract_relevant_links(self, soup, result):
        """Extract links that might lead to API documentation."""
        relevant_patterns = [
            r"api",
            r"rest",
            r"developer",
            r"docs",
            r"technical",
            r"integration",
            r"service",
            r"data.*access",
            r"query",
        ]

        links = soup.find_all("a", href=True)
        relevant_links = []

        for link in links:
            href = link["href"]
            link_text = link.get_text().lower().strip()

            # Check if link text or href matches relevant patterns
            for pattern in relevant_patterns:
                if re.search(pattern, link_text) or re.search(pattern, href.lower()):
                    full_url = urljoin(result["url"], href)
                    relevant_links.append(
                        {"url": full_url, "text": link_text, "href": href}
                    )
                    self.discovered_links.add(full_url)
                    break

        result["links_discovered"] = relevant_links

    def _classify_documentation_type(self, content, result):
        """Classify the type of documentation found."""
        if any(word in content for word in ["swagger", "openapi", "api reference"]):
            result["documentation_type"] = "api_reference"
        elif any(word in content for word in ["developer guide", "integration guide"]):
            result["documentation_type"] = "developer_guide"
        elif any(word in content for word in ["technical specification", "protocol"]):
            result["documentation_type"] = "technical_spec"
        elif any(word in content for word in ["help", "support", "how to"]):
            result["documentation_type"] = "user_help"
        elif any(word in content for word in ["query", "search", "data access"]):
            result["documentation_type"] = "data_interface"
        else:
            result["documentation_type"] = "general"

    def search_content_for_api_references(self, base_url: str) -> Dict:
        """
        Search main website content for any API references.

        Performs content analysis of main pages looking for API mentions.
        """
        result = {
            "url": base_url,
            "searched": False,
            "api_mentions": [],
            "technical_sections": [],
            "developer_resources": [],
            "contact_info": [],
            "error_details": None,
        }

        try:
            response = requests.get(base_url, timeout=15)

            if response.status_code == 200:
                result["searched"] = True
                soup = BeautifulSoup(response.text, "html.parser")

                # Look for API mentions in text
                text_content = soup.get_text().lower()
                api_patterns = [
                    r"api\b",
                    r"application programming interface",
                    r"web service",
                    r"rest service",
                    r"json service",
                    r"programmatic access",
                    r"automated access",
                ]

                for pattern in api_patterns:
                    matches = re.findall(f".{{0,50}}{pattern}.{{0,50}}", text_content)
                    if matches:
                        result["api_mentions"].extend(matches)

                # Look for technical/developer sections in navigation
                nav_links = soup.find_all(["nav", "menu"]) + soup.find_all("a")
                for link in nav_links:
                    link_text = link.get_text().lower()
                    if any(
                        word in link_text
                        for word in ["developer", "technical", "api", "integration"]
                    ):
                        href = link.get("href", "")
                        result["developer_resources"].append(
                            {"text": link_text.strip(), "href": href}
                        )

        except requests.RequestException as e:
            result["error_details"] = str(e)

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


class TestBSEEWebsiteDocumentation:
    """Test suite for BSEE website documentation analysis."""

    def setup_method(self):
        """Initialize documentation tester for each test."""
        self.doc_tester = BSEEDocumentationTester()

    def test_documentation_section_discovery(self):
        """
        Test 1.4a: Discover documentation sections across BSEE websites.

        Systematically tests common documentation section URLs to identify
        any API documentation or developer resources.
        """
        doc_sections_found = []
        total_sections_tested = 0

        for base_url in self.doc_tester.base_urls:
            for section in self.doc_tester.doc_sections:
                result = self.doc_tester.test_documentation_section(base_url, section)
                total_sections_tested += 1

                if result["accessible"] and result["status_code"] == 200:
                    doc_sections_found.append(result)

                    self.doc_tester.document_finding(
                        "Documentation Section Found",
                        f"Accessible documentation: {result['url']}",
                        {
                            "page_title": result["page_title"],
                            "documentation_type": result["documentation_type"],
                            "api_keywords": result["api_keywords_found"],
                            "technical_keywords": result["bsee_tech_keywords_found"],
                        },
                    )

        # Analyze findings
        api_relevant_sections = [
            section
            for section in doc_sections_found
            if section["api_keywords_found"]
            or section["documentation_type"] in ["api_reference", "developer_guide"]
        ]

        summary = {
            "total_sections_tested": total_sections_tested,
            "accessible_sections": len(doc_sections_found),
            "api_relevant_sections": len(api_relevant_sections),
            "documentation_types_found": list(
                set(section["documentation_type"] for section in doc_sections_found)
            ),
        }

        self.doc_tester.document_finding(
            "Documentation Discovery Summary",
            f"Documentation section discovery complete",
            summary,
        )

        logger.info(
            f"Found {len(doc_sections_found)} accessible documentation sections"
        )
        assert True  # Always passes, documents findings

    def test_main_website_content_analysis(self):
        """
        Test 1.4b: Analyze main website content for API references.

        Searches main BSEE website pages for any mentions of APIs,
        web services, or programmatic access methods.
        """
        content_analysis_results = []

        for base_url in self.doc_tester.base_urls:
            result = self.doc_tester.search_content_for_api_references(base_url)
            content_analysis_results.append(result)

            if result["searched"]:
                self.doc_tester.document_finding(
                    "Content Analysis",
                    f"Analyzed main content: {result['url']}",
                    {
                        "api_mentions_count": len(result["api_mentions"]),
                        "api_mentions": result["api_mentions"][:5],  # First 5 matches
                        "developer_resources": result["developer_resources"],
                    },
                )

        # Compile all API mentions
        all_api_mentions = []
        all_developer_resources = []

        for result in content_analysis_results:
            all_api_mentions.extend(result.get("api_mentions", []))
            all_developer_resources.extend(result.get("developer_resources", []))

        summary = {
            "websites_analyzed": len(
                [r for r in content_analysis_results if r["searched"]]
            ),
            "total_api_mentions": len(all_api_mentions),
            "developer_resources_found": len(all_developer_resources),
            "unique_api_contexts": list(set(all_api_mentions))[:10],  # First 10 unique
        }

        self.doc_tester.document_finding(
            "Content Analysis Summary",
            "Main website content analysis complete",
            summary,
        )

        logger.info(
            f"Content analysis complete: {len(all_api_mentions)} API mentions found"
        )
        assert True  # Always passes, documents findings

    def test_discovered_links_analysis(self):
        """
        Test 1.4c: Follow and analyze discovered links for API information.

        Tests links discovered during documentation section analysis
        that might lead to additional API resources.
        """
        if not hasattr(self, "doc_tester"):
            pytest.skip("Documentation tester not initialized")

        # First run documentation discovery to populate discovered_links
        for base_url in self.doc_tester.base_urls:
            for section in ["/docs/", "/api/", "/developer/"]:  # Test key sections
                self.doc_tester.test_documentation_section(base_url, section)

        analyzed_links = []

        # Analyze discovered links (limit to prevent excessive testing)
        for link_url in list(self.doc_tester.discovered_links)[:20]:
            try:
                response = requests.get(link_url, timeout=10)

                analysis = {
                    "url": link_url,
                    "accessible": response.status_code == 200,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "api_relevant": False,
                }

                if response.status_code == 200:
                    content = response.text.lower()
                    # Check for API-relevant content
                    api_indicators = [
                        "api",
                        "rest",
                        "json",
                        "xml",
                        "endpoint",
                        "service",
                    ]
                    analysis["api_relevant"] = any(
                        indicator in content for indicator in api_indicators
                    )

                analyzed_links.append(analysis)

                if analysis["api_relevant"]:
                    self.doc_tester.document_finding(
                        "API-Relevant Link Found",
                        f"Discovered API-relevant content: {link_url}",
                        analysis,
                    )

            except requests.RequestException:
                pass  # Skip inaccessible links

        summary = {
            "total_links_discovered": len(self.doc_tester.discovered_links),
            "links_analyzed": len(analyzed_links),
            "accessible_links": len([l for l in analyzed_links if l["accessible"]]),
            "api_relevant_links": len([l for l in analyzed_links if l["api_relevant"]]),
        }

        self.doc_tester.document_finding(
            "Discovered Links Summary", "Discovered links analysis complete", summary
        )

        logger.info(f"Analyzed {len(analyzed_links)} discovered links")
        assert True  # Always passes, documents findings

    def test_search_functionality_analysis(self):
        """
        Test 1.4d: Analyze website search functionality for API documentation.

        Tests BSEE website search features to look for API-related content.
        """
        search_terms = [
            "api",
            "web service",
            "rest",
            "json",
            "developer",
            "programmatic access",
            "integration",
            "technical documentation",
        ]

        search_results = []

        # Test search on main BSEE sites
        search_bases = ["https://www.bsee.gov", "https://www.data.bsee.gov"]

        for base_url in search_bases:
            for term in search_terms[
                :3
            ]:  # Limit search terms to prevent excessive requests
                try:
                    # Common search URL patterns
                    search_patterns = [
                        f"{base_url}/search?q={term}",
                        f"{base_url}/search.aspx?q={term}",
                        f"http://search.usa.gov/search?affiliate=bsee&query={term}",
                    ]

                    for search_url in search_patterns:
                        response = requests.get(search_url, timeout=10)

                        if response.status_code == 200:
                            search_result = {
                                "search_url": search_url,
                                "term": term,
                                "accessible": True,
                                "content_length": len(response.content),
                                "has_results": "no results"
                                not in response.text.lower(),
                            }

                            search_results.append(search_result)

                            if search_result["has_results"]:
                                self.doc_tester.document_finding(
                                    "Search Results Found",
                                    f"Search results for '{term}': {search_url}",
                                    search_result,
                                )
                            break  # Found working search, move to next term

                except requests.RequestException:
                    continue

        summary = {
            "search_terms_tested": len(search_terms[:3]),
            "search_urls_tested": len(search_results),
            "successful_searches": len([r for r in search_results if r["accessible"]]),
            "searches_with_results": len(
                [r for r in search_results if r.get("has_results", False)]
            ),
        }

        self.doc_tester.document_finding(
            "Search Functionality Summary", "Website search analysis complete", summary
        )

        logger.info(f"Search functionality testing complete")
        assert True  # Always passes, documents findings

    def teardown_method(self):
        """Save comprehensive website documentation analysis results."""
        if hasattr(self, "doc_tester") and self.doc_tester.findings:
            # Generate website documentation analysis report
            report_lines = []
            report_lines.append("# BSEE Website Documentation Analysis Report")
            report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")

            # Executive Summary
            total_findings = len(self.doc_tester.findings)
            api_relevant_findings = len(
                [
                    f
                    for f in self.doc_tester.findings
                    if "api" in f["description"].lower()
                    or "developer" in f["description"].lower()
                ]
            )

            report_lines.append("## Executive Summary")
            report_lines.append(f"- Total documentation findings: {total_findings}")
            report_lines.append(f"- API-relevant findings: {api_relevant_findings}")
            report_lines.append(
                f"- Links discovered: {len(self.doc_tester.discovered_links)}"
            )
            report_lines.append("")

            # Key Findings
            report_lines.append("## Key Findings")

            # Group findings by category
            categories = {}
            for finding in self.doc_tester.findings:
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

            # Discovered Links
            if self.doc_tester.discovered_links:
                report_lines.append("## Discovered Links")
                for link in list(self.doc_tester.discovered_links)[:20]:
                    report_lines.append(f"- {link}")
                report_lines.append("")

            report = "\n".join(report_lines)

            # Save report
            report_path = "tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/results/website_documentation_analysis.md"
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(
                    f"Website documentation analysis report saved to {report_path}"
                )
            except Exception as e:
                logger.warning(f"Could not save report: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
