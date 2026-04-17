#!/usr/bin/env python3
"""
Test Data.gov Catalog Integration for BSEE API Discovery

This module tests Data.gov catalog and federal API registry to identify
any BSEE-related APIs, datasets, or web services available through
the federal data catalog system.

Tests cover:
- Data.gov catalog search for BSEE datasets
- Federal API registry search
- BSEE dataset metadata analysis
- API endpoint discovery through catalog
- Data format and access method identification
- Download URL and API endpoint validation

The Data.gov catalog is the central repository for federal government
datasets and API information, making it a critical resource for
discovering official BSEE data access methods.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import pytest
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataGovCatalogTester:
    """
    Test Data.gov catalog for BSEE-related APIs and datasets.

    This class systematically searches the Data.gov catalog system
    to identify official government APIs and datasets related to BSEE.
    """

    def __init__(self):
        # Data.gov API endpoints
        self.catalog_api_base = "https://catalog.data.gov/api/3"
        self.data_gov_base = "https://www.data.gov"

        # Federal API registry (if available)
        self.api_registry_endpoints = [
            "https://api.data.gov",
            "https://catalog.data.gov/api",
            "https://www.data.gov/developers",
        ]

        # BSEE-related search terms
        self.bsee_search_terms = [
            "bsee",
            "bureau safety environmental enforcement",
            "offshore energy",
            "oil gas safety",
            "boem bsee",
            "offshore drilling",
            "platform safety",
            "well data",
            "production data",
            "offshore leases",
        ]

        self.findings = []
        self.discovered_datasets = []
        self.discovered_apis = []

    def search_catalog_datasets(self, search_term: str, limit: int = 20) -> Dict:
        """
        Search Data.gov catalog for datasets matching search term.

        Returns comprehensive dataset information including access methods.
        """
        result = {
            "search_term": search_term,
            "query_successful": False,
            "total_datasets": 0,
            "bsee_datasets": [],
            "api_datasets": [],
            "download_datasets": [],
            "error_details": None,
        }

        try:
            # CKAN API search endpoint
            search_url = f"{self.catalog_api_base}/action/package_search"
            params = {"q": search_term, "rows": limit, "sort": "score desc"}

            response = requests.get(search_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                result["query_successful"] = True
                result["total_datasets"] = data.get("result", {}).get("count", 0)

                # Analyze datasets
                datasets = data.get("result", {}).get("results", [])

                for dataset in datasets:
                    dataset_info = self._analyze_dataset(dataset)

                    # Check if BSEE-related
                    if self._is_bsee_related(dataset_info):
                        result["bsee_datasets"].append(dataset_info)
                        self.discovered_datasets.append(dataset_info)

                    # Check for API access
                    if dataset_info.get("has_api", False):
                        result["api_datasets"].append(dataset_info)
                        self.discovered_apis.extend(
                            dataset_info.get("api_endpoints", [])
                        )

                    # Check for download access
                    if dataset_info.get("has_downloads", False):
                        result["download_datasets"].append(dataset_info)

        except requests.RequestException as e:
            result["error_details"] = str(e)
        except json.JSONDecodeError as e:
            result["error_details"] = f"JSON decode error: {str(e)}"

        return result

    def _analyze_dataset(self, dataset: Dict) -> Dict:
        """Analyze individual dataset for API and access information."""
        dataset_info = {
            "id": dataset.get("id", ""),
            "name": dataset.get("name", ""),
            "title": dataset.get("title", ""),
            "organization": dataset.get("organization", {}).get("name", ""),
            "description": dataset.get("notes", ""),
            "tags": [tag.get("name", "") for tag in dataset.get("tags", [])],
            "resources": [],
            "has_api": False,
            "has_downloads": False,
            "api_endpoints": [],
            "download_urls": [],
            "data_formats": [],
        }

        # Analyze resources
        resources = dataset.get("resources", [])
        for resource in resources:
            resource_info = {
                "id": resource.get("id", ""),
                "name": resource.get("name", ""),
                "url": resource.get("url", ""),
                "format": resource.get("format", "").upper(),
                "description": resource.get("description", ""),
                "resource_type": resource.get("resource_type", ""),
            }

            dataset_info["resources"].append(resource_info)

            # Check for API indicators
            if any(
                indicator in resource_info["url"].lower()
                for indicator in ["api", "rest", "service", "json"]
            ):
                dataset_info["has_api"] = True
                dataset_info["api_endpoints"].append(resource_info["url"])

            # Check for download formats
            if resource_info["format"] in ["CSV", "JSON", "XML", "ZIP", "XLSX"]:
                dataset_info["has_downloads"] = True
                dataset_info["download_urls"].append(resource_info["url"])

            if resource_info["format"]:
                dataset_info["data_formats"].append(resource_info["format"])

        # Remove duplicates
        dataset_info["data_formats"] = list(set(dataset_info["data_formats"]))

        return dataset_info

    def _is_bsee_related(self, dataset_info: Dict) -> bool:
        """Check if dataset is BSEE-related."""
        # Check organization
        org_name = dataset_info.get("organization", "").lower()
        if "bsee" in org_name or "safety environmental enforcement" in org_name:
            return True

        # Check title and description
        text_fields = [
            dataset_info.get("title", ""),
            dataset_info.get("description", ""),
            dataset_info.get("name", ""),
        ]

        combined_text = " ".join(text_fields).lower()

        bsee_indicators = [
            "bsee",
            "bureau of safety",
            "environmental enforcement",
            "offshore safety",
            "oil gas safety",
            "drilling safety",
            "platform data",
            "well safety",
            "offshore energy",
        ]

        return any(indicator in combined_text for indicator in bsee_indicators)

    def test_api_registry_endpoints(self) -> Dict:
        """
        Test federal API registry endpoints for BSEE APIs.

        Checks various federal API registry locations for BSEE-related APIs.
        """
        result = {
            "registries_tested": 0,
            "accessible_registries": [],
            "apis_found": [],
            "bsee_apis": [],
            "error_details": [],
        }

        for registry_url in self.api_registry_endpoints:
            try:
                response = requests.get(registry_url, timeout=15)
                result["registries_tested"] += 1

                if response.status_code == 200:
                    result["accessible_registries"].append(registry_url)

                    # Look for API listings or catalogs
                    content = response.text.lower()

                    # Search for BSEE-related API mentions
                    if any(term in content for term in ["bsee", "offshore", "safety"]):
                        api_info = {
                            "registry_url": registry_url,
                            "content_length": len(response.content),
                            "has_bsee_content": True,
                        }
                        result["bsee_apis"].append(api_info)

            except requests.RequestException as e:
                result["error_details"].append(f"{registry_url}: {str(e)}")

        return result

    def validate_discovered_apis(self) -> Dict:
        """
        Validate APIs discovered through Data.gov catalog.

        Tests discovered API endpoints for accessibility and functionality.
        """
        result = {
            "total_apis": len(self.discovered_apis),
            "tested_apis": 0,
            "working_apis": [],
            "failed_apis": [],
            "api_details": [],
        }

        for api_url in self.discovered_apis[:10]:  # Limit to prevent excessive testing
            try:
                response = requests.get(api_url, timeout=10)
                result["tested_apis"] += 1

                api_details = {
                    "url": api_url,
                    "accessible": response.status_code == 200,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "has_json": False,
                    "api_indicators": [],
                }

                if response.status_code == 200:
                    result["working_apis"].append(api_url)

                    # Check for JSON response
                    try:
                        response.json()
                        api_details["has_json"] = True
                    except ValueError:
                        pass

                    # Look for API indicators
                    content = response.text.lower()
                    indicators = ["api", "endpoint", "service", "rest"]
                    api_details["api_indicators"] = [
                        ind for ind in indicators if ind in content
                    ]
                else:
                    result["failed_apis"].append(api_url)

                result["api_details"].append(api_details)

            except requests.RequestException as e:
                result["failed_apis"].append(api_url)
                result["api_details"].append(
                    {"url": api_url, "accessible": False, "error": str(e)}
                )

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


class TestDataGovCatalogIntegration:
    """Test suite for Data.gov catalog integration and BSEE API discovery."""

    def setup_method(self):
        """Initialize Data.gov catalog tester for each test."""
        self.catalog_tester = DataGovCatalogTester()

    def test_catalog_dataset_search(self):
        """
        Test 1.5a: Search Data.gov catalog for BSEE datasets.

        Systematically searches the federal data catalog for BSEE-related
        datasets and analyzes their access methods.
        """
        all_bsee_datasets = []
        all_api_datasets = []
        total_searches = 0

        for search_term in self.catalog_tester.bsee_search_terms:
            result = self.catalog_tester.search_catalog_datasets(search_term)
            total_searches += 1

            if result["query_successful"]:
                self.catalog_tester.document_finding(
                    "Catalog Search",
                    f"Search '{search_term}': {result['total_datasets']} datasets found",
                    {
                        "search_term": search_term,
                        "total_datasets": result["total_datasets"],
                        "bsee_datasets": len(result["bsee_datasets"]),
                        "api_datasets": len(result["api_datasets"]),
                    },
                )

                all_bsee_datasets.extend(result["bsee_datasets"])
                all_api_datasets.extend(result["api_datasets"])
            else:
                self.catalog_tester.document_finding(
                    "Catalog Search Failed",
                    f"Failed to search for '{search_term}'",
                    {"error": result["error_details"]},
                )

        # Remove duplicates
        unique_bsee_datasets = []
        seen_ids = set()
        for dataset in all_bsee_datasets:
            if dataset["id"] not in seen_ids:
                unique_bsee_datasets.append(dataset)
                seen_ids.add(dataset["id"])

        summary = {
            "total_searches": total_searches,
            "total_bsee_datasets_found": len(unique_bsee_datasets),
            "total_api_datasets_found": len(all_api_datasets),
            "unique_organizations": list(
                set(d["organization"] for d in unique_bsee_datasets)
            ),
            "data_formats_available": list(
                set([fmt for d in unique_bsee_datasets for fmt in d["data_formats"]])
            ),
        }

        self.catalog_tester.document_finding(
            "Catalog Search Summary", f"Data.gov catalog search complete", summary
        )

        logger.info(f"Found {len(unique_bsee_datasets)} BSEE-related datasets")
        assert True  # Always passes, documents findings

    def test_federal_api_registry(self):
        """
        Test 1.5b: Test federal API registry for BSEE APIs.

        Checks federal API registry endpoints for any official
        BSEE APIs or web services.
        """
        registry_result = self.catalog_tester.test_api_registry_endpoints()

        self.catalog_tester.document_finding(
            "API Registry Test",
            f"Tested {registry_result['registries_tested']} API registries",
            {
                "accessible_registries": len(registry_result["accessible_registries"]),
                "registries_with_bsee_content": len(registry_result["bsee_apis"]),
                "accessible_registry_urls": registry_result["accessible_registries"],
            },
        )

        if registry_result["bsee_apis"]:
            for api_info in registry_result["bsee_apis"]:
                self.catalog_tester.document_finding(
                    "BSEE API Registry Content",
                    f"BSEE content found in registry: {api_info['registry_url']}",
                    api_info,
                )

        logger.info(f"API registry testing complete")
        assert True  # Always passes, documents findings

    def test_discovered_api_validation(self):
        """
        Test 1.5c: Validate APIs discovered through Data.gov catalog.

        Tests functionality of any APIs discovered through the catalog
        search process.
        """
        # First ensure we have discovered APIs by running searches
        if not self.catalog_tester.discovered_apis:
            # Run a quick search to populate discovered APIs
            for term in self.catalog_tester.bsee_search_terms[:2]:
                self.catalog_tester.search_catalog_datasets(term, limit=10)

        validation_result = self.catalog_tester.validate_discovered_apis()

        self.catalog_tester.document_finding(
            "API Validation",
            f"Validated {validation_result['tested_apis']} discovered APIs",
            {
                "total_apis_discovered": validation_result["total_apis"],
                "apis_tested": validation_result["tested_apis"],
                "working_apis": len(validation_result["working_apis"]),
                "failed_apis": len(validation_result["failed_apis"]),
                "working_api_urls": validation_result["working_apis"],
            },
        )

        # Document working APIs
        for api_details in validation_result["api_details"]:
            if api_details.get("accessible", False):
                self.catalog_tester.document_finding(
                    "Working API Found",
                    f"Functional API endpoint: {api_details['url']}",
                    api_details,
                )

        logger.info(
            f"API validation complete: {len(validation_result['working_apis'])} working APIs"
        )
        assert True  # Always passes, documents findings

    def test_dataset_access_methods(self):
        """
        Test 1.5d: Analyze access methods for discovered BSEE datasets.

        Examines the access methods (download URLs, APIs, web services)
        available for BSEE-related datasets found in Data.gov.
        """
        access_methods = {
            "download_urls": [],
            "api_endpoints": [],
            "web_services": [],
            "data_formats": {},
            "organizations": set(),
        }

        for dataset in self.catalog_tester.discovered_datasets:
            access_methods["organizations"].add(dataset["organization"])

            # Collect download URLs
            access_methods["download_urls"].extend(dataset.get("download_urls", []))

            # Collect API endpoints
            access_methods["api_endpoints"].extend(dataset.get("api_endpoints", []))

            # Count data formats
            for fmt in dataset.get("data_formats", []):
                access_methods["data_formats"][fmt] = (
                    access_methods["data_formats"].get(fmt, 0) + 1
                )

        # Remove duplicates from URLs
        access_methods["download_urls"] = list(set(access_methods["download_urls"]))
        access_methods["api_endpoints"] = list(set(access_methods["api_endpoints"]))
        access_methods["organizations"] = list(access_methods["organizations"])

        summary = {
            "datasets_analyzed": len(self.catalog_tester.discovered_datasets),
            "total_download_urls": len(access_methods["download_urls"]),
            "total_api_endpoints": len(access_methods["api_endpoints"]),
            "data_formats": dict(access_methods["data_formats"]),
            "organizations": access_methods["organizations"],
        }

        self.catalog_tester.document_finding(
            "Dataset Access Methods",
            f"Analyzed access methods for {len(self.catalog_tester.discovered_datasets)} datasets",
            summary,
        )

        # Test sample download URLs
        working_downloads = []
        for url in access_methods["download_urls"][:5]:  # Test first 5
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    working_downloads.append(url)
            except requests.RequestException:
                pass

        if working_downloads:
            self.catalog_tester.document_finding(
                "Working Download URLs",
                f"Validated {len(working_downloads)} working download URLs",
                {"working_urls": working_downloads},
            )

        logger.info(f"Access methods analysis complete")
        assert True  # Always passes, documents findings

    def teardown_method(self):
        """Save comprehensive Data.gov catalog integration results."""
        if hasattr(self, "catalog_tester") and self.catalog_tester.findings:
            # Generate Data.gov integration report
            report_lines = []
            report_lines.append("# Data.gov Catalog Integration Report")
            report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")

            # Executive Summary
            total_datasets = len(self.catalog_tester.discovered_datasets)
            total_apis = len(self.catalog_tester.discovered_apis)

            report_lines.append("## Executive Summary")
            report_lines.append(f"- BSEE datasets discovered: {total_datasets}")
            report_lines.append(f"- API endpoints discovered: {total_apis}")
            report_lines.append(
                f"- Total research findings: {len(self.catalog_tester.findings)}"
            )
            report_lines.append("")

            # Discovered Datasets
            if self.catalog_tester.discovered_datasets:
                report_lines.append("## Discovered BSEE Datasets")
                for dataset in self.catalog_tester.discovered_datasets[:10]:
                    report_lines.append(f"### {dataset['title']}")
                    report_lines.append(
                        f"- **Organization**: {dataset['organization']}"
                    )
                    report_lines.append(
                        f"- **Data Formats**: {', '.join(dataset['data_formats'])}"
                    )
                    report_lines.append(f"- **Has API**: {dataset['has_api']}")
                    report_lines.append(
                        f"- **Has Downloads**: {dataset['has_downloads']}"
                    )
                    if dataset["description"]:
                        report_lines.append(
                            f"- **Description**: {dataset['description'][:200]}..."
                        )
                    report_lines.append("")

            # API Endpoints
            if self.catalog_tester.discovered_apis:
                report_lines.append("## Discovered API Endpoints")
                for api_url in self.catalog_tester.discovered_apis[:10]:
                    report_lines.append(f"- {api_url}")
                report_lines.append("")

            # Detailed Findings
            report_lines.append("## Detailed Findings")

            categories = {}
            for finding in self.catalog_tester.findings:
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
            report_path = "tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/results/data_gov_catalog_report.md"
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Data.gov catalog report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Could not save report: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
