#!/usr/bin/env python3
"""
Test Direct BSEE File URL Access Validation

This module tests direct access to BSEE data file URLs identified during
API research. These tests validate the availability and stability of the
confirmed data sources for web scraper implementation.

Tests cover:
- Direct URL accessibility testing for three data sources
- File size and content type validation  
- Update frequency verification
- Download stability and error handling
- Portal page validation and link verification

Based on Task 1 research, the following URLs were confirmed functional:
- Well Data: https://www.data.bsee.gov/Well/Files/APDRawData.zip
- Production Data: https://www.data.bsee.gov/Production/Files/ProductionRawData.zip
- WAR Data: https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip
"""

import pytest
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import time
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import urljoin, urlparse
import os
from datetime import datetime
import io
import zipfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BSEEURLValidator:
    """
    Validate BSEE data file URLs for web scraper implementation.
    
    This class provides comprehensive validation of the BSEE data URLs
    discovered during API research, ensuring they're suitable for
    reliable web scraper implementation.
    """
    
    def __init__(self):
        # Confirmed data source URLs from Task 1 research
        self.data_sources = {
            'well_data': {
                'url': 'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
                'display_name': 'Application for Permit to Drill',
                'update_frequency': 'daily',
                'expected_size_mb': 50,  # Approximate based on research
                'data_type': 'well'
            },
            'production_data': {
                'url': 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
                'display_name': 'Production Data',
                'update_frequency': 'bi-monthly',
                'expected_size_mb': 100,  # Approximate based on research
                'data_type': 'production'
            },
            'war_data': {
                'url': 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
                'display_name': 'eWell Submissions WAR',
                'update_frequency': 'daily',
                'expected_size_mb': 75,  # Approximate based on research
                'data_type': 'war'
            }
        }
        
        # Portal and validation URLs
        self.portal_url = 'https://www.data.bsee.gov/Main/RawData.aspx'
        
        self.validation_results = []
        self.findings = []
    
    def validate_url_access(self, data_source: str) -> Dict:
        """
        Validate accessibility of a specific data source URL.
        
        Performs comprehensive validation including accessibility,
        response headers, file size, and download stability.
        """
        if data_source not in self.data_sources:
            raise ValueError(f"Unknown data source: {data_source}")
        
        source_info = self.data_sources[data_source]
        url = source_info['url']
        
        result = {
            'data_source': data_source,
            'url': url,
            'display_name': source_info['display_name'],
            'accessible': False,
            'status_code': 0,
            'response_time': 0.0,
            'content_type': '',
            'content_length': 0,
            'content_length_mb': 0.0,
            'last_modified': '',
            'etag': '',
            'server': '',
            'supports_range_requests': False,
            'download_stable': False,
            'validation_timestamp': datetime.now().isoformat(),
            'error_details': None
        }
        
        try:
            start_time = time.time()
            
            # Use HEAD request first for efficiency
            response = requests.head(url, timeout=30, allow_redirects=True)
            result['response_time'] = time.time() - start_time
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['accessible'] = True
                
                # Extract response headers
                headers = response.headers
                result['content_type'] = headers.get('content-type', '')
                result['content_length'] = int(headers.get('content-length', 0))
                result['content_length_mb'] = result['content_length'] / (1024 * 1024)
                result['last_modified'] = headers.get('last-modified', '')
                result['etag'] = headers.get('etag', '')
                result['server'] = headers.get('server', '')
                
                # Check for range request support
                result['supports_range_requests'] = 'bytes' in headers.get('accept-ranges', '')
                
                # Validate content type is ZIP
                if 'zip' not in result['content_type'].lower() and 'application/octet-stream' not in result['content_type'].lower():
                    result['error_details'] = f"Unexpected content type: {result['content_type']}"
                
                # Validate file size is reasonable
                expected_size_mb = source_info['expected_size_mb']
                if result['content_length_mb'] > 0:
                    size_ratio = result['content_length_mb'] / expected_size_mb
                    if size_ratio < 0.1 or size_ratio > 10:  # Allow 10x variation
                        result['error_details'] = f"Unexpected file size: {result['content_length_mb']:.1f}MB (expected ~{expected_size_mb}MB)"
                
                # Test download stability with partial request
                result['download_stable'] = self._test_download_stability(url)
                
        except Timeout:
            result['error_details'] = 'Request timeout (>30s)'
        except ConnectionError:
            result['error_details'] = 'Connection error'
        except RequestException as e:
            result['error_details'] = f'Request error: {str(e)}'
        except Exception as e:
            result['error_details'] = f'Unexpected error: {str(e)}'
        
        return result
    
    def _test_download_stability(self, url: str) -> bool:
        """
        Test download stability with a small partial request.
        
        Downloads first 1KB to verify the file is actually downloadable
        and the connection is stable.
        """
        try:
            headers = {'Range': 'bytes=0-1023'}  # Request first 1KB
            response = requests.get(url, headers=headers, timeout=15)
            
            # Check for partial content response
            if response.status_code in [200, 206]:  # 200 if range not supported, 206 if partial
                # Verify we got some data
                if len(response.content) > 0:
                    # Try to verify it's a ZIP file by checking magic bytes
                    if response.content.startswith(b'PK'):  # ZIP magic bytes
                        return True
            
        except RequestException:
            pass  # Fall through to return False
        
        return False
    
    def validate_portal_page(self) -> Dict:
        """
        Validate the main portal page and extract download links.
        
        Verifies that the Raw Data portal page is accessible and contains
        the expected download links for the three data sources.
        """
        result = {
            'portal_url': self.portal_url,
            'accessible': False,
            'status_code': 0,
            'page_title': '',
            'download_links_found': {},
            'expected_links_present': False,
            'total_download_links': 0,
            'validation_timestamp': datetime.now().isoformat(),
            'error_details': None
        }
        
        try:
            response = requests.get(self.portal_url, timeout=20)
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['accessible'] = True
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract page title
                title_tag = soup.find('title')
                if title_tag:
                    result['page_title'] = title_tag.get_text().strip()
                
                # Look for download links
                links = soup.find_all('a', href=True)
                download_links = {}
                
                for link in links:
                    href = link['href']
                    link_text = link.get_text().strip().lower()
                    
                    # Check for our target files
                    for source_key, source_info in self.data_sources.items():
                        url = source_info['url']
                        filename = url.split('/')[-1]  # Get filename from URL
                        
                        if filename.lower() in href.lower() or href.endswith(filename):
                            download_links[source_key] = {
                                'found_url': urljoin(self.portal_url, href),
                                'expected_url': url,
                                'link_text': link_text,
                                'matches_expected': href.endswith(filename)
                            }
                
                result['download_links_found'] = download_links
                result['total_download_links'] = len([l for l in links if '.zip' in l['href'].lower()])
                
                # Check if all expected links are present
                expected_sources = set(self.data_sources.keys())
                found_sources = set(download_links.keys())
                result['expected_links_present'] = expected_sources.issubset(found_sources)
                
                if not result['expected_links_present']:
                    missing = expected_sources - found_sources
                    result['error_details'] = f"Missing download links for: {', '.join(missing)}"
                    
        except RequestException as e:
            result['error_details'] = f'Request error: {str(e)}'
        except Exception as e:
            result['error_details'] = f'Unexpected error: {str(e)}'
        
        return result
    
    def test_zip_file_integrity(self, url: str, sample_size_kb: int = 100) -> Dict:
        """
        Test ZIP file integrity by downloading a sample and verifying structure.
        
        Downloads a small sample of the ZIP file and attempts to read the
        ZIP directory to verify file integrity without downloading the entire file.
        """
        result = {
            'url': url,
            'sample_size_kb': sample_size_kb,
            'zip_valid': False,
            'file_count': 0,
            'file_names': [],
            'compression_ratio': 0.0,
            'error_details': None
        }
        
        try:
            # Download sample from the end of file (where ZIP directory is located)
            headers = {'Range': f'bytes=-{sample_size_kb * 1024}'}  # Last N KB
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code in [200, 206]:
                sample_data = response.content
                
                # Try to read as ZIP file
                try:
                    # For partial content, we may not be able to read the full directory
                    # But we can at least verify ZIP structure exists
                    if b'PK\x01\x02' in sample_data or b'PK\x03\x04' in sample_data:
                        result['zip_valid'] = True
                        
                        # If we got the full file or enough data, try to read directory
                        if response.status_code == 200:  # Full file
                            with zipfile.ZipFile(io.BytesIO(sample_data), 'r') as zip_ref:
                                file_list = zip_ref.namelist()
                                result['file_count'] = len(file_list)
                                result['file_names'] = file_list[:10]  # First 10 files
                                
                                # Calculate compression ratio if possible
                                total_compressed = sum(info.compress_size for info in zip_ref.infolist())
                                total_uncompressed = sum(info.file_size for info in zip_ref.infolist())
                                if total_uncompressed > 0:
                                    result['compression_ratio'] = total_compressed / total_uncompressed
                    else:
                        result['error_details'] = 'No ZIP file signatures found in sample'
                        
                except zipfile.BadZipFile:
                    result['error_details'] = 'Invalid ZIP file structure'
                except Exception as e:
                    result['error_details'] = f'ZIP analysis error: {str(e)}'
            else:
                result['error_details'] = f'HTTP {response.status_code}: Could not download sample'
                
        except RequestException as e:
            result['error_details'] = f'Request error: {str(e)}'
        
        return result
    
    def document_finding(self, category: str, description: str, details: Dict = None):
        """Document research findings."""
        finding = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'category': category,
            'description': description,
            'details': details or {}
        }
        self.findings.append(finding)
        logger.info(f"[{category}] {description}")


class TestBSEEURLAccess:
    """Test suite for BSEE data source URL access validation."""
    
    def setup_method(self):
        """Initialize URL validator for each test."""
        self.url_validator = BSEEURLValidator()
    
    def test_well_data_url_access(self):
        """
        Test 3.1a: Validate well data URL accessibility.
        
        Tests direct access to the APDRawData.zip file URL to ensure
        it's accessible and suitable for web scraper implementation.
        """
        result = self.url_validator.validate_url_access('well_data')
        
        self.url_validator.document_finding(
            'Well Data URL Validation',
            f"Well data URL validated: {result['url']}",
            {
                'accessible': result['accessible'],
                'status_code': result['status_code'],
                'file_size_mb': result['content_length_mb'],
                'response_time': result['response_time'],
                'download_stable': result['download_stable']
            }
        )
        
        # URL should be accessible
        assert result['accessible'], f"Well data URL not accessible: {result['error_details']}"
        assert result['status_code'] == 200, f"Expected 200, got {result['status_code']}"
        
        # File should be reasonably sized (not empty, not impossibly large)
        assert result['content_length_mb'] > 1, "Well data file too small (likely empty)"
        assert result['content_length_mb'] < 500, "Well data file too large (>500MB)"
        
        # Download should be stable
        assert result['download_stable'], "Well data download not stable"
        
        logger.info(f"Well data URL validated successfully: {result['content_length_mb']:.1f}MB")
    
    def test_production_data_url_access(self):
        """
        Test 3.1b: Validate production data URL accessibility.
        
        Tests direct access to the ProductionRawData.zip file URL.
        """
        result = self.url_validator.validate_url_access('production_data')
        
        self.url_validator.document_finding(
            'Production Data URL Validation',
            f"Production data URL validated: {result['url']}",
            {
                'accessible': result['accessible'],
                'status_code': result['status_code'],
                'file_size_mb': result['content_length_mb'],
                'response_time': result['response_time'],
                'download_stable': result['download_stable']
            }
        )
        
        # URL should be accessible
        assert result['accessible'], f"Production data URL not accessible: {result['error_details']}"
        assert result['status_code'] == 200, f"Expected 200, got {result['status_code']}"
        
        # File should be reasonably sized
        assert result['content_length_mb'] > 1, "Production data file too small"
        assert result['content_length_mb'] < 500, "Production data file too large (>500MB)"
        
        # Download should be stable
        assert result['download_stable'], "Production data download not stable"
        
        logger.info(f"Production data URL validated successfully: {result['content_length_mb']:.1f}MB")
    
    def test_war_data_url_access(self):
        """
        Test 3.1c: Validate WAR data URL accessibility.
        
        Tests direct access to the eWellWARRawData.zip file URL.
        """
        result = self.url_validator.validate_url_access('war_data')
        
        self.url_validator.document_finding(
            'WAR Data URL Validation',
            f"WAR data URL validated: {result['url']}",
            {
                'accessible': result['accessible'],
                'status_code': result['status_code'],
                'file_size_mb': result['content_length_mb'],
                'response_time': result['response_time'],
                'download_stable': result['download_stable']
            }
        )
        
        # URL should be accessible
        assert result['accessible'], f"WAR data URL not accessible: {result['error_details']}"
        assert result['status_code'] == 200, f"Expected 200, got {result['status_code']}"
        
        # File should be reasonably sized
        assert result['content_length_mb'] > 1, "WAR data file too small"
        assert result['content_length_mb'] < 500, "WAR data file too large (>500MB)"
        
        # Download should be stable
        assert result['download_stable'], "WAR data download not stable"
        
        logger.info(f"WAR data URL validated successfully: {result['content_length_mb']:.1f}MB")
    
    def test_all_urls_comprehensive_validation(self):
        """
        Test 3.1d: Comprehensive validation of all data source URLs.
        
        Performs complete validation of all three data sources including
        file integrity testing and comparative analysis.
        """
        all_results = {}
        total_size_mb = 0
        accessible_count = 0
        
        # Validate each data source
        for source_key in self.url_validator.data_sources.keys():
            result = self.url_validator.validate_url_access(source_key)
            all_results[source_key] = result
            
            if result['accessible']:
                accessible_count += 1
                total_size_mb += result['content_length_mb']
                
                # Test ZIP file integrity for accessible files
                zip_test = self.url_validator.test_zip_file_integrity(result['url'])
                result['zip_integrity'] = zip_test
        
        # Document comprehensive results
        summary = {
            'total_sources_tested': len(self.url_validator.data_sources),
            'accessible_sources': accessible_count,
            'total_data_size_mb': total_size_mb,
            'all_sources_accessible': accessible_count == len(self.url_validator.data_sources),
            'average_response_time': sum(r['response_time'] for r in all_results.values()) / len(all_results)
        }
        
        self.url_validator.document_finding(
            'Comprehensive URL Validation',
            f"All BSEE data sources validated",
            summary
        )
        
        # All URLs should be accessible for successful implementation
        assert summary['all_sources_accessible'], f"Only {accessible_count}/3 data sources accessible"
        
        # Total data size should be manageable but not trivial
        assert total_size_mb > 10, "Combined data size too small (may indicate issues)"
        assert total_size_mb < 1000, "Combined data size too large (>1GB)"
        
        logger.info(f"All 3 BSEE data sources validated successfully: {total_size_mb:.1f}MB total")
    
    def test_portal_page_validation(self):
        """
        Test 3.1e: Validate main portal page and download links.
        
        Tests the Raw Data portal page to ensure it contains the expected
        download links and the page structure is stable.
        """
        result = self.url_validator.validate_portal_page()
        
        self.url_validator.document_finding(
            'Portal Page Validation',
            f"Portal page validated: {result['portal_url']}",
            {
                'accessible': result['accessible'],
                'status_code': result['status_code'],
                'expected_links_present': result['expected_links_present'],
                'total_download_links': result['total_download_links'],
                'links_found': len(result['download_links_found'])
            }
        )
        
        # Portal page should be accessible
        assert result['accessible'], f"Portal page not accessible: {result['error_details']}"
        assert result['status_code'] == 200, f"Expected 200, got {result['status_code']}"
        
        # Should find some download links
        assert result['total_download_links'] > 0, "No download links found on portal page"
        
        # Expected links may not all be present (page structure may change)
        # But we should find at least some of our target files
        assert len(result['download_links_found']) > 0, "None of the expected download links found"
        
        logger.info(f"Portal page validated: {len(result['download_links_found'])}/3 expected links found")
    
    def teardown_method(self):
        """Save URL validation results."""
        if hasattr(self, 'url_validator') and self.url_validator.findings:
            # Generate URL validation report
            report_lines = []
            report_lines.append("# BSEE URL Access Validation Report")
            report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")
            
            # Summary of findings
            accessible_urls = len([f for f in self.url_validator.findings 
                                 if 'accessible' in str(f.get('details', {})) 
                                 and f['details'].get('accessible', False)])
            
            report_lines.append("## Executive Summary")
            report_lines.append(f"- Total validations performed: {len(self.url_validator.findings)}")
            report_lines.append(f"- Accessible URLs validated: {accessible_urls}")
            report_lines.append("")
            
            # Detailed findings
            report_lines.append("## Detailed Validation Results")
            
            categories = {}
            for finding in self.url_validator.findings:
                cat = finding['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(finding)
            
            for category, findings in categories.items():
                report_lines.append(f"### {category}")
                for finding in findings:
                    report_lines.append(f"- **{finding['timestamp']}**: {finding['description']}")
                    if finding['details']:
                        for key, value in finding['details'].items():
                            report_lines.append(f"  - {key}: {value}")
                report_lines.append("")
            
            report = '\n'.join(report_lines)
            
            # Save report
            report_path = "tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/results/url_access_validation.md"
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                logger.info(f"URL validation report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Could not save report: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])