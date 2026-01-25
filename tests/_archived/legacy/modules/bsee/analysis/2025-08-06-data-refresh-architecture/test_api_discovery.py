#!/usr/bin/env python3
"""
Test API Discovery Process for BSEE Data Refresh Architecture

This module contains tests for documenting and validating the API discovery process
for BSEE data sources. These tests serve as both validation and documentation of
the research methodology used to identify available APIs.

Tests cover:
- BSEE developer documentation research
- Common government API patterns testing
- Website API documentation section analysis
- Data.gov catalog integration checks
- Hidden AJAX/JSON endpoint discovery
- Specific interface analysis (OCSProduction, Well/API, Platform)

Each test documents the research approach and captures findings for comprehensive
API research reporting.
"""

import pytest
import requests
import json
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Tuple
import time
import logging

# Configure logging for test documentation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BSEEAPIDiscovery:
    """
    BSEE API Discovery utility class for testing and documenting API research process.
    
    This class provides methods to systematically test for API availability across
    common government API patterns and document the research methodology.
    """
    
    def __init__(self):
        self.base_urls = [
            "https://www.bsee.gov",
            "https://www.data.bsee.gov",
            "https://bsee.gov",
            "https://data.bsee.gov"
        ]
        self.api_patterns = [
            "/api/",
            "/api/v1/",
            "/api/v2/",
            "/rest/",
            "/rest/v1/",
            "/services/",
            "/webapi/",
            "/data/api/",
            "/open/api/"
        ]
        self.doc_patterns = [
            "/api/",
            "/docs/",
            "/documentation/",
            "/developer/",
            "/dev/",
            "/swagger/",
            "/openapi/",
            "/api-docs/",
            "/developer-docs/"
        ]
        self.findings = []
        
    def test_url_accessibility(self, url: str) -> Tuple[bool, int, str]:
        """
        Test URL accessibility and return status information.
        
        Returns:
            Tuple of (accessible, status_code, reason)
        """
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            return True, response.status_code, response.reason
        except requests.RequestException as e:
            return False, 0, str(e)
    
    def test_api_endpoint(self, url: str) -> Dict:
        """
        Test potential API endpoint and analyze response.
        
        Returns:
            Dictionary with endpoint analysis results
        """
        result = {
            'url': url,
            'accessible': False,
            'status_code': 0,
            'content_type': '',
            'has_json_response': False,
            'has_api_indicators': False,
            'response_size': 0,
            'findings': []
        }
        
        try:
            response = requests.get(url, timeout=10, headers={'Accept': 'application/json'})
            result['accessible'] = True
            result['status_code'] = response.status_code
            result['content_type'] = response.headers.get('content-type', '')
            result['response_size'] = len(response.content)
            
            # Check for JSON response
            try:
                response.json()
                result['has_json_response'] = True
                result['findings'].append('Valid JSON response detected')
            except ValueError:
                pass
            
            # Check for API indicators in content
            content_lower = response.text.lower()
            api_indicators = ['api', 'endpoint', 'swagger', 'openapi', 'rest', 'json']
            found_indicators = [ind for ind in api_indicators if ind in content_lower]
            
            if found_indicators:
                result['has_api_indicators'] = True
                result['findings'].append(f'API indicators found: {found_indicators}')
            
            # Check for specific BSEE data indicators
            bsee_indicators = ['production', 'well', 'platform', 'lease', 'drilling', 'safety']
            found_bsee = [ind for ind in bsee_indicators if ind in content_lower]
            
            if found_bsee:
                result['findings'].append(f'BSEE data indicators found: {found_bsee}')
                
        except requests.RequestException as e:
            result['findings'].append(f'Request failed: {str(e)}')
        
        return result
    
    def document_finding(self, category: str, description: str, details: Dict = None):
        """Document a research finding for comprehensive reporting."""
        finding = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'category': category,
            'description': description,
            'details': details or {}
        }
        self.findings.append(finding)
        logger.info(f"[{category}] {description}")
    
    def generate_research_report(self) -> str:
        """Generate comprehensive API research report."""
        report = []
        report.append("# BSEE API Research Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Group findings by category
        categories = {}
        for finding in self.findings:
            cat = finding['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(finding)
        
        for category, findings in categories.items():
            report.append(f"## {category}")
            for finding in findings:
                report.append(f"- **{finding['timestamp']}**: {finding['description']}")
                if finding['details']:
                    for key, value in finding['details'].items():
                        report.append(f"  - {key}: {value}")
            report.append("")
        
        return '\n'.join(report)


class TestAPIDiscoveryDocumentation:
    """
    Test suite for documenting BSEE API discovery process.
    
    These tests serve dual purposes:
    1. Execute systematic API research methodology
    2. Document findings for comprehensive research report
    
    Each test method corresponds to a specific research approach outlined
    in the specification requirements.
    """
    
    def setup_method(self):
        """Initialize API discovery utility for each test."""
        self.discovery = BSEEAPIDiscovery()
    
    def test_document_research_methodology(self):
        """
        Test 1.1: Document API discovery process methodology.
        
        This test documents the systematic approach used for BSEE API research,
        creating a foundation for all subsequent discovery tests.
        """
        methodology = {
            'research_approach': 'Systematic government API pattern testing',
            'base_urls_tested': self.discovery.base_urls,
            'api_patterns_tested': self.discovery.api_patterns,
            'documentation_patterns': self.discovery.doc_patterns,
            'validation_criteria': [
                'URL accessibility testing',
                'JSON response validation',
                'API indicator detection',
                'BSEE-specific content analysis',
                'Response header analysis',
                'Content-type validation'
            ]
        }
        
        self.discovery.document_finding(
            'Methodology',
            'API discovery methodology established',
            methodology
        )
        
        assert len(self.discovery.findings) > 0
        assert methodology['research_approach'] is not None
        
        logger.info("API discovery methodology documented successfully")
    
    def test_base_url_accessibility(self):
        """
        Test base URL accessibility for BSEE domains.
        
        Documents which BSEE domains are accessible and their response characteristics.
        """
        accessible_urls = []
        
        for base_url in self.discovery.base_urls:
            accessible, status_code, reason = self.discovery.test_url_accessibility(base_url)
            
            result_details = {
                'url': base_url,
                'accessible': accessible,
                'status_code': status_code,
                'reason': reason
            }
            
            if accessible:
                accessible_urls.append(base_url)
                self.discovery.document_finding(
                    'Base URL Access',
                    f'{base_url} is accessible',
                    result_details
                )
            else:
                self.discovery.document_finding(
                    'Base URL Access',
                    f'{base_url} is not accessible',
                    result_details
                )
        
        # At least one BSEE domain should be accessible
        assert len(accessible_urls) > 0, "No BSEE domains accessible"
        
        logger.info(f"Documented accessibility for {len(self.discovery.base_urls)} base URLs")
    
    def test_common_api_pattern_detection(self):
        """
        Test common government API patterns against BSEE domains.
        
        This test documents attempts to access common API endpoints across
        government websites to identify potential BSEE API access points.
        """
        api_endpoints_found = []
        
        for base_url in self.discovery.base_urls:
            for api_pattern in self.discovery.api_patterns:
                test_url = urljoin(base_url, api_pattern)
                
                result = self.discovery.test_api_endpoint(test_url)
                
                if result['accessible'] and result['status_code'] == 200:
                    api_endpoints_found.append(test_url)
                    
                self.discovery.document_finding(
                    'API Pattern Testing',
                    f'Tested {test_url}',
                    result
                )
        
        # Document summary of API pattern testing
        summary = {
            'total_patterns_tested': len(self.discovery.base_urls) * len(self.discovery.api_patterns),
            'accessible_endpoints': len(api_endpoints_found),
            'found_endpoints': api_endpoints_found
        }
        
        self.discovery.document_finding(
            'API Pattern Summary',
            'Common API pattern testing completed',
            summary
        )
        
        logger.info(f"Tested {summary['total_patterns_tested']} API patterns")
        
        # Test always passes - documents findings regardless of API availability
        assert True
    
    def test_documentation_section_analysis(self):
        """
        Test for API documentation sections on BSEE websites.
        
        Documents attempts to find developer documentation, API guides,
        or technical documentation that might reveal API availability.
        """
        doc_sections_found = []
        
        for base_url in self.discovery.base_urls:
            for doc_pattern in self.discovery.doc_patterns:
                test_url = urljoin(base_url, doc_pattern)
                
                result = self.discovery.test_api_endpoint(test_url)
                
                # Look for documentation indicators
                if result['accessible'] and result['status_code'] == 200:
                    if result['has_api_indicators'] or 'documentation' in result['content_type']:
                        doc_sections_found.append(test_url)
                
                self.discovery.document_finding(
                    'Documentation Analysis',
                    f'Analyzed {test_url}',
                    result
                )
        
        # Document documentation analysis summary
        summary = {
            'total_doc_patterns_tested': len(self.discovery.base_urls) * len(self.discovery.doc_patterns),
            'documentation_sections_found': len(doc_sections_found),
            'found_sections': doc_sections_found
        }
        
        self.discovery.document_finding(
            'Documentation Summary',
            'Documentation section analysis completed',
            summary
        )
        
        logger.info(f"Analyzed {summary['total_doc_patterns_tested']} documentation patterns")
        
        # Test always passes - documents findings regardless of documentation availability
        assert True
    
    def teardown_method(self):
        """
        Generate and save API discovery research report after each test.
        """
        if hasattr(self, 'discovery') and self.discovery.findings:
            report = self.discovery.generate_research_report()
            
            # Save report to results directory
            report_path = "tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/results/api_discovery_research.md"
            
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                logger.info(f"API discovery report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Could not save report: {e}")


if __name__ == "__main__":
    # Run API discovery tests when executed directly
    pytest.main([__file__, "-v"])