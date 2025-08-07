"""
BSEE Web Scraper Module

This module handles downloading BSEE data files directly from their URLs
into memory, avoiding the need to store large zip files in the repository.
"""

import io
import requests
from typing import Optional, ByteString
from loguru import logger
import time
from urllib.parse import urlparse


class BSEEWebScraper:
    """
    Web scraper for BSEE data files.
    
    Downloads zip files directly into memory for processing without
    storing them on disk, solving the GitHub file size limit issue.
    """
    
    # BSEE data source URLs
    URLS = {
        'well': 'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
        'production': 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
        'war': 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
        'portal': 'https://www.data.bsee.gov/Main/RawData.aspx'
    }
    
    # Request configuration
    TIMEOUT = 300  # 5 minutes for large files
    CHUNK_SIZE = 8192  # 8KB chunks for streaming
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self):
        """Initialize the web scraper with session management."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WorldEnergyData/1.0 (BSEE Data Refresh)',
            'Accept': 'application/zip, application/octet-stream, */*'
        })
    
    def download_zip_to_memory(self, url: str, max_retries: int = None) -> Optional[ByteString]:
        """
        Download a zip file directly into memory.
        
        Args:
            url: URL of the zip file to download
            max_retries: Maximum number of retry attempts
            
        Returns:
            Bytes of the zip file content or None if failed
        """
        max_retries = max_retries or self.MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading from {url} (attempt {attempt + 1}/{max_retries})")
                
                # Stream the download to handle large files efficiently
                response = self.session.get(url, stream=True, timeout=self.TIMEOUT)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                if 'zip' not in content_type.lower() and 'octet-stream' not in content_type.lower():
                    logger.warning(f"Unexpected content type: {content_type}")
                
                # Get file size if available
                file_size = int(response.headers.get('Content-Length', 0))
                if file_size > 0:
                    logger.info(f"File size: {file_size / (1024*1024):.2f} MB")
                
                # Download in chunks to memory
                chunks = []
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        
                        # Progress logging for large files
                        if file_size > 0 and downloaded % (10 * 1024 * 1024) == 0:  # Every 10MB
                            progress = (downloaded / file_size) * 100
                            logger.info(f"Download progress: {progress:.1f}%")
                
                # Combine all chunks
                data = b''.join(chunks)
                logger.info(f"Successfully downloaded {len(data) / (1024*1024):.2f} MB")
                
                return data
                
            except requests.exceptions.Timeout:
                logger.error(f"Timeout downloading from {url}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error downloading from {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
                    
            except Exception as e:
                logger.error(f"Unexpected error downloading from {url}: {str(e)}")
                break
        
        logger.error(f"Failed to download from {url} after {max_retries} attempts")
        return None
    
    def download_well_data(self) -> Optional[ByteString]:
        """
        Download well APD data.
        
        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE well data (APD)")
        return self.download_zip_to_memory(self.URLS['well'])
    
    def download_production_data(self) -> Optional[ByteString]:
        """
        Download production data.
        
        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE production data")
        return self.download_zip_to_memory(self.URLS['production'])
    
    def download_war_data(self) -> Optional[ByteString]:
        """
        Download WAR (Well Activity Report) data.
        
        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE WAR data")
        return self.download_zip_to_memory(self.URLS['war'])
    
    def verify_url_accessibility(self, url: str) -> bool:
        """
        Verify that a URL is accessible.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            response = self.session.head(url, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking URL {url}: {str(e)}")
            return False
    
    def verify_all_sources(self) -> dict:
        """
        Verify accessibility of all BSEE data sources.
        
        Returns:
            Dictionary with URL accessibility status
        """
        logger.info("Verifying BSEE data source accessibility")
        results = {}
        
        for name, url in self.URLS.items():
            accessible = self.verify_url_accessibility(url)
            results[name] = {
                'url': url,
                'accessible': accessible
            }
            logger.info(f"{name}: {'✓' if accessible else '✗'} {url}")
        
        return results
    
    def get_file_info(self, url: str) -> dict:
        """
        Get information about a file without downloading it.
        
        Args:
            url: URL of the file
            
        Returns:
            Dictionary with file information
        """
        try:
            response = self.session.head(url, timeout=30)
            response.raise_for_status()
            
            info = {
                'url': url,
                'content_type': response.headers.get('Content-Type', 'unknown'),
                'content_length': int(response.headers.get('Content-Length', 0)),
                'last_modified': response.headers.get('Last-Modified', 'unknown'),
                'etag': response.headers.get('ETag', 'unknown')
            }
            
            if info['content_length'] > 0:
                info['size_mb'] = info['content_length'] / (1024 * 1024)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting file info for {url}: {str(e)}")
            return {'url': url, 'error': str(e)}
    
    def close(self):
        """Close the session."""
        self.session.close()