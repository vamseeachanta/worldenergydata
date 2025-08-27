"""
PDF exporter for comprehensive reports.

Exports report data to PDF format with professional formatting and charts.
"""
import io
import time
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .base import ReportExporter, ExportFormat, ExportConfig, ExportResult


class PDFExporter(ReportExporter):
    """
    Exporter for PDF format using weasyprint.
    
    Converts HTML to PDF with professional styling and embedded charts.
    """
    
    def __init__(self):
        """Initialize PDF exporter."""
        super().__init__()
        self.supported_format = ExportFormat.PDF
        self.html_content = ""
        self.css_styles = ""
    
    def export(self, data: Dict[str, Any], config: ExportConfig) -> ExportResult:
        """
        Export report data to PDF format.
        
        Args:
            data: Report data to export
            config: Export configuration
            
        Returns:
            ExportResult with export details
        """
        if not WEASYPRINT_AVAILABLE:
            return ExportResult(
                success=False,
                message="weasyprint library not available. Install with: pip install weasyprint",
                errors=["Missing dependency: weasyprint"]
            )
        
        start_time = time.time()
        result = ExportResult(success=True)
        
        # Validate data
        if not self.validate_data(data):
            result.success = False
            result.message = "Invalid data structure for PDF export"
            return result
        
        # Prepare output directory
        if not self.prepare_output_directory(config.output_path):
            result.success = False
            result.message = "Failed to create output directory"
            return result
        
        try:
            # Generate HTML content
            self.html_content = self.generate_html(data)
            
            # Get CSS styles
            self.css_styles = self.get_pdf_styles()
            
            # Add page layout CSS
            page_css = self._get_page_layout_css(config)
            self.css_styles += page_css
            
            # Convert HTML to PDF
            html_doc = HTML(string=self.html_content)
            css_doc = CSS(string=self.css_styles)
            
            # Write PDF
            html_doc.write_pdf(
                str(config.output_path),
                stylesheets=[css_doc]
            )
            
            # Update result
            result.file_path = config.output_path
            result.file_size = config.output_path.stat().st_size
            result.export_time = time.time() - start_time
            result.message = "PDF export completed successfully"
            
            # Check file size
            if result.file_size > 5 * 1024 * 1024:  # 5MB warning
                result.add_warning(f"Large PDF size: {result.file_size / (1024*1024):.1f}MB")
            
        except Exception as e:
            result.success = False
            result.message = f"PDF export failed: {str(e)}"
            result.add_error(str(e))
        
        return result
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate data structure for PDF export.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Minimum requirement: some content to export
        if not data:
            return False
        
        # Check for exportable content
        required_sections = ['report_metadata', 'content', 'summary']
        optional_sections = ['tables', 'charts', 'kpis']
        
        has_required = any(section in data for section in required_sections)
        has_content = any(section in data for section in optional_sections)
        
        return has_required or has_content
    
    def get_supported_features(self) -> List[str]:
        """
        Get list of supported features.
        
        Returns:
            List of feature names
        """
        return [
            'html_to_pdf',
            'css_styling',
            'page_headers',
            'page_footers',
            'page_numbers',
            'table_of_contents',
            'embedded_charts',
            'professional_layout',
            'print_ready'
        ]
    
    def generate_html(self, data: Dict[str, Any]) -> str:
        """
        Generate HTML content from report data.
        
        Args:
            data: Report data
            
        Returns:
            HTML string
        """
        html_parts = []
        
        # Start HTML document
        html_parts.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
        </head>
        <body>
        """.format(title=data.get('report_metadata', {}).get('title', 'Report')))
        
        # Add cover page
        if 'report_metadata' in data:
            html_parts.append(self._generate_cover_page(data['report_metadata']))
        
        # Add table of contents
        html_parts.append(self._generate_toc(data))
        
        # Add executive summary
        if 'executive_summary' in data.get('content', {}):
            html_parts.append(self._generate_section(
                'Executive Summary',
                data['content']['executive_summary']
            ))
        
        # Add key findings
        if 'key_findings' in data.get('content', {}):
            html_parts.append(self._generate_list_section(
                'Key Findings',
                data['content']['key_findings']
            ))
        
        # Add KPIs section
        if 'kpis' in data:
            html_parts.append(self._generate_kpi_section(data['kpis']))
        
        # Add production data
        if 'production_data' in data:
            html_parts.append(self._generate_table_section(
                'Production Data',
                data['production_data']
            ))
        
        # Add financial analysis
        if 'financial_data' in data:
            html_parts.append(self._generate_financial_section(data['financial_data']))
        
        # Add charts
        if 'charts' in data:
            html_parts.append(self._generate_charts_section(data['charts']))
        
        # Add recommendations
        if 'recommendations' in data.get('content', {}):
            html_parts.append(self._generate_list_section(
                'Recommendations',
                data['content']['recommendations']
            ))
        
        # Add appendix
        if 'appendix' in data:
            html_parts.append(self._generate_appendix(data['appendix']))
        
        # Close HTML document
        html_parts.append("""
        </body>
        </html>
        """)
        
        return ''.join(html_parts)
    
    def get_pdf_styles(self) -> str:
        """
        Get CSS styles for PDF.
        
        Returns:
            CSS string
        """
        return """
        /* General styles */
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        /* Headers */
        h1 {
            font-size: 24pt;
            color: #2c3e50;
            margin: 20pt 0 15pt 0;
            border-bottom: 2pt solid #3498db;
            padding-bottom: 10pt;
            page-break-after: avoid;
        }
        
        h2 {
            font-size: 18pt;
            color: #34495e;
            margin: 15pt 0 10pt 0;
            page-break-after: avoid;
        }
        
        h3 {
            font-size: 14pt;
            color: #34495e;
            margin: 10pt 0 8pt 0;
            page-break-after: avoid;
        }
        
        /* Cover page */
        .cover-page {
            page-break-after: always;
            text-align: center;
            padding-top: 200pt;
        }
        
        .cover-title {
            font-size: 36pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20pt;
        }
        
        .cover-subtitle {
            font-size: 18pt;
            color: #7f8c8d;
            margin-bottom: 10pt;
        }
        
        .cover-date {
            font-size: 14pt;
            color: #95a5a6;
        }
        
        /* Table of contents */
        .toc {
            page-break-after: always;
        }
        
        .toc-item {
            margin: 5pt 0;
            padding-left: 20pt;
        }
        
        .toc-page {
            float: right;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15pt 0;
            page-break-inside: avoid;
        }
        
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
            padding: 8pt;
            text-align: left;
            border: 1pt solid #2980b9;
        }
        
        td {
            padding: 6pt;
            border: 1pt solid #bdc3c7;
        }
        
        tr:nth-child(even) {
            background-color: #ecf0f1;
        }
        
        /* KPI cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10pt;
            margin: 15pt 0;
        }
        
        .kpi-card {
            border: 1pt solid #bdc3c7;
            border-radius: 5pt;
            padding: 10pt;
            text-align: center;
            page-break-inside: avoid;
        }
        
        .kpi-value {
            font-size: 24pt;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .kpi-label {
            font-size: 10pt;
            color: #7f8c8d;
            margin-top: 5pt;
        }
        
        .kpi-status-green {
            color: #27ae60;
        }
        
        .kpi-status-yellow {
            color: #f39c12;
        }
        
        .kpi-status-red {
            color: #e74c3c;
        }
        
        /* Lists */
        ul, ol {
            margin: 10pt 0;
            padding-left: 20pt;
        }
        
        li {
            margin: 5pt 0;
        }
        
        /* Page breaks */
        .page-break {
            page-break-after: always;
        }
        
        .no-break {
            page-break-inside: avoid;
        }
        
        /* Charts */
        .chart-container {
            text-align: center;
            margin: 15pt 0;
            page-break-inside: avoid;
        }
        
        .chart-image {
            max-width: 100%;
            height: auto;
        }
        
        /* Footer */
        .footer {
            position: fixed;
            bottom: 0;
            width: 100%;
            text-align: center;
            font-size: 9pt;
            color: #7f8c8d;
            border-top: 1pt solid #bdc3c7;
            padding-top: 5pt;
        }
        """
    
    def _get_page_layout_css(self, config: ExportConfig) -> str:
        """Get page layout CSS based on configuration."""
        orientation = config.orientation or 'portrait'
        size = config.page_size or 'A4'
        
        return f"""
        @page {{
            size: {size} {orientation};
            margin: 2.5cm;
            
            @bottom-right {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #7f8c8d;
            }}
            
            @bottom-center {{
                content: "{config.output_path.stem}";
                font-size: 9pt;
                color: #7f8c8d;
            }}
        }}
        """
    
    def _generate_cover_page(self, metadata: Dict) -> str:
        """Generate cover page HTML."""
        return f"""
        <div class="cover-page">
            <div class="cover-title">{metadata.get('title', 'Report')}</div>
            <div class="cover-subtitle">{metadata.get('organization', '')}</div>
            <div class="cover-date">{metadata.get('date', datetime.now().strftime('%B %Y'))}</div>
        </div>
        """
    
    def _generate_toc(self, data: Dict) -> str:
        """Generate table of contents."""
        toc_html = '<div class="toc"><h1>Table of Contents</h1>'
        
        sections = []
        if 'executive_summary' in data.get('content', {}):
            sections.append('Executive Summary')
        if 'key_findings' in data.get('content', {}):
            sections.append('Key Findings')
        if 'kpis' in data:
            sections.append('Key Performance Indicators')
        if 'production_data' in data:
            sections.append('Production Data')
        if 'financial_data' in data:
            sections.append('Financial Analysis')
        if 'charts' in data:
            sections.append('Charts and Visualizations')
        if 'recommendations' in data.get('content', {}):
            sections.append('Recommendations')
        
        for i, section in enumerate(sections, 1):
            toc_html += f'<div class="toc-item">{i}. {section}</div>'
        
        toc_html += '</div>'
        return toc_html
    
    def _generate_section(self, title: str, content: str) -> str:
        """Generate a text section."""
        return f"""
        <div class="section">
            <h1>{title}</h1>
            <p>{content}</p>
        </div>
        """
    
    def _generate_list_section(self, title: str, items: List[str]) -> str:
        """Generate a list section."""
        html = f'<div class="section"><h1>{title}</h1><ul>'
        for item in items:
            html += f'<li>{item}</li>'
        html += '</ul></div>'
        return html
    
    def _generate_kpi_section(self, kpis: List[Dict]) -> str:
        """Generate KPI section with cards."""
        html = '<div class="section"><h1>Key Performance Indicators</h1><div class="kpi-grid">'
        
        for kpi in kpis[:6]:  # Show top 6 KPIs
            status_class = f"kpi-status-{kpi.get('status', 'gray')}"
            html += f"""
            <div class="kpi-card">
                <div class="kpi-value {status_class}">{kpi.get('value', 'N/A')}</div>
                <div class="kpi-label">{kpi.get('name', 'KPI')}</div>
            </div>
            """
        
        html += '</div></div>'
        return html
    
    def _generate_table_section(self, title: str, data: List[Dict]) -> str:
        """Generate table section."""
        if not data:
            return ''
        
        html = f'<div class="section"><h1>{title}</h1>'
        html += self.render_table(self._dict_list_to_table(data))
        html += '</div>'
        return html
    
    def _generate_financial_section(self, financial_data: Dict) -> str:
        """Generate financial analysis section."""
        html = '<div class="section"><h1>Financial Analysis</h1><table>'
        
        for key, value in financial_data.items():
            formatted_key = key.replace('_', ' ').title()
            formatted_value = self._format_currency(value) if isinstance(value, (int, float, Decimal)) else str(value)
            html += f"""
            <tr>
                <td><strong>{formatted_key}</strong></td>
                <td style="text-align: right">{formatted_value}</td>
            </tr>
            """
        
        html += '</table></div>'
        return html
    
    def _generate_charts_section(self, charts: Dict) -> str:
        """Generate charts section."""
        html = '<div class="section"><h1>Charts and Visualizations</h1>'
        
        for chart_name, chart_data in charts.items():
            # Convert chart to base64 image
            chart_base64 = self.chart_to_base64(chart_data)
            if chart_base64:
                html += f"""
                <div class="chart-container">
                    <h3>{chart_name.replace('_', ' ').title()}</h3>
                    <img src="data:image/png;base64,{chart_base64}" class="chart-image">
                </div>
                """
        
        html += '</div>'
        return html
    
    def _generate_appendix(self, appendix_data: Any) -> str:
        """Generate appendix section."""
        return f"""
        <div class="section page-break">
            <h1>Appendix</h1>
            <pre>{str(appendix_data)}</pre>
        </div>
        """
    
    def render_table(self, table_data: List[List]) -> str:
        """
        Render table as HTML.
        
        Args:
            table_data: Table data as list of lists
            
        Returns:
            HTML table string
        """
        if not table_data:
            return ''
        
        html = '<table>'
        
        # Header row
        html += '<tr>'
        for header in table_data[0]:
            html += f'<th>{header}</th>'
        html += '</tr>'
        
        # Data rows
        for row in table_data[1:]:
            html += '<tr>'
            for cell in row:
                html += f'<td>{cell}</td>'
            html += '</tr>'
        
        html += '</table>'
        return html
    
    def chart_to_base64(self, chart_data: Any) -> Optional[str]:
        """
        Convert chart to base64 encoded image.
        
        Args:
            chart_data: Chart object or data
            
        Returns:
            Base64 string or None
        """
        try:
            # If it's already a base64 string, return it
            if isinstance(chart_data, str) and chart_data.startswith('data:image'):
                return chart_data.split(',')[1]
            
            # If matplotlib is available, try to convert
            if MATPLOTLIB_AVAILABLE and hasattr(chart_data, 'savefig'):
                buffer = io.BytesIO()
                chart_data.savefig(buffer, format='png', bbox_inches='tight')
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode()
            
            # For plotly figures
            if hasattr(chart_data, 'to_image'):
                img_bytes = chart_data.to_image(format='png')
                return base64.b64encode(img_bytes).decode()
            
            return None
        except Exception:
            return None
    
    def embed_chart_as_image(self, chart_data: Any) -> str:
        """
        Embed chart as image in HTML.
        
        Args:
            chart_data: Chart object
            
        Returns:
            HTML img tag
        """
        base64_data = self.chart_to_base64(chart_data)
        if base64_data:
            return f'<img src="data:image/png;base64,{base64_data}" class="chart-image">'
        return '<p>Chart not available</p>'
    
    def generate_header(self, metadata: Dict) -> str:
        """
        Generate PDF header.
        
        Args:
            metadata: Report metadata
            
        Returns:
            Header HTML
        """
        return f"""
        <div class="header">
            <span>{metadata.get('title', 'Report')}</span>
            <span style="float: right">{metadata.get('date', '')}</span>
        </div>
        """
    
    def generate_footer(self, page_number: int, total_pages: int) -> str:
        """
        Generate PDF footer.
        
        Args:
            page_number: Current page number
            total_pages: Total number of pages
            
        Returns:
            Footer HTML
        """
        return f"""
        <div class="footer">
            Page {page_number} of {total_pages}
        </div>
        """
    
    def get_page_layout(self) -> Dict:
        """
        Get page layout configuration.
        
        Returns:
            Layout configuration dictionary
        """
        return {
            'size': 'A4',
            'margin': '2.5cm',
            'orientation': 'portrait',
            'header_height': '1.5cm',
            'footer_height': '1cm'
        }
    
    def _dict_list_to_table(self, data: List[Dict]) -> List[List]:
        """Convert list of dicts to table format."""
        if not data:
            return []
        
        headers = list(data[0].keys())
        table = [headers]
        
        for record in data:
            row = [str(record.get(h, '')) for h in headers]
            table.append(row)
        
        return table
    
    def _format_currency(self, value: Union[int, float, Decimal]) -> str:
        """Format value as currency."""
        return f"${float(value):,.2f}"