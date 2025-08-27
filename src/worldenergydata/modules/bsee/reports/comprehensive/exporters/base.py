"""
Base classes for report export functionality.

Provides abstract base class and supporting structures for exporting
reports to various formats.
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime


class ExportFormat(Enum):
    """Supported export formats."""
    EXCEL = "excel"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    POWERPOINT = "powerpoint"


@dataclass
class ExportConfig:
    """Configuration for report export."""
    format: ExportFormat
    output_path: Path
    template_name: Optional[str] = None
    include_charts: bool = True
    include_raw_data: bool = False
    compression: bool = False
    page_size: str = "A4"  # For PDF
    orientation: str = "portrait"  # For PDF
    excel_options: Optional[Dict] = None
    pdf_options: Optional[Dict] = None
    
    def __post_init__(self):
        """Ensure path is a Path object."""
        if not isinstance(self.output_path, Path):
            self.output_path = Path(self.output_path)
        
        # Initialize format-specific options
        if self.excel_options is None:
            self.excel_options = {}
        if self.pdf_options is None:
            self.pdf_options = {}


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    file_path: Optional[Path] = None
    file_size: int = 0
    export_time: float = 0.0
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def get_summary(self) -> str:
        """Get a summary of the export result."""
        if self.success:
            summary = f"Export successful: {self.file_path}"
            if self.file_size:
                summary += f" ({self.file_size:,} bytes)"
            if self.export_time:
                summary += f" in {self.export_time:.2f}s"
        else:
            summary = f"Export failed: {self.message}"
            if self.errors:
                summary += f" Errors: {', '.join(self.errors)}"
        
        if self.warnings:
            summary += f" Warnings: {', '.join(self.warnings)}"
        
        return summary


class ReportExporter(ABC):
    """
    Abstract base class for report exporters.
    
    All format-specific exporters should inherit from this class
    and implement the required methods.
    """
    
    def __init__(self):
        """Initialize the exporter."""
        self.supported_format = None
        self.max_file_size = 100 * 1024 * 1024  # 100MB default limit
    
    @abstractmethod
    def export(self, data: Dict[str, Any], config: ExportConfig) -> ExportResult:
        """
        Export report data to the specified format.
        
        Args:
            data: Report data to export
            config: Export configuration
            
        Returns:
            ExportResult object with export details
        """
        pass
    
    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate that the data can be exported.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """
        Get list of supported features for this exporter.
        
        Returns:
            List of feature names
        """
        pass
    
    def prepare_output_directory(self, output_path: Path) -> bool:
        """
        Ensure output directory exists.
        
        Args:
            output_path: Path to output file
            
        Returns:
            True if directory is ready, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Failed to create output directory: {e}")
            return False
    
    def check_file_size_limit(self, file_path: Path) -> bool:
        """
        Check if exported file is within size limits.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if within limits, False otherwise
        """
        if file_path.exists():
            file_size = file_path.stat().st_size
            return file_size <= self.max_file_size
        return True
    
    def format_timestamp(self, dt: datetime = None) -> str:
        """
        Format timestamp for file naming.
        
        Args:
            dt: Datetime to format (uses now if None)
            
        Returns:
            Formatted timestamp string
        """
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%Y%m%d_%H%M%S")
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        import re
        # Remove invalid characters for Windows/Unix filesystems
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(sanitized) > 200:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            sanitized = f"{name[:195]}...{ext}" if ext else name[:200]
        return sanitized
    
    def get_file_extension(self) -> str:
        """
        Get the file extension for this export format.
        
        Returns:
            File extension with dot (e.g., '.xlsx')
        """
        extensions = {
            ExportFormat.EXCEL: '.xlsx',
            ExportFormat.PDF: '.pdf',
            ExportFormat.HTML: '.html',
            ExportFormat.JSON: '.json',
            ExportFormat.POWERPOINT: '.pptx'
        }
        return extensions.get(self.supported_format, '')
    
    def add_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add export metadata to the data.
        
        Args:
            data: Original data
            
        Returns:
            Data with metadata added
        """
        metadata = {
            'export_timestamp': datetime.now().isoformat(),
            'export_format': self.supported_format.value if self.supported_format else 'unknown',
            'exporter_version': '1.0.0'
        }
        
        if 'metadata' in data:
            data['metadata'].update(metadata)
        else:
            data['metadata'] = metadata
        
        return data