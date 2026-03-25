#!/usr/bin/env python3
"""
ABOUTME: Script to integrate optimized HTML template into generate_incident_report.py
ABOUTME: Replaces the massive HTML generation loop with CSV-based client-side loading
"""

import re

# Optimized HTML template
OPTIMIZED_TEMPLATE = '''    # Build column headers based on incident type
    if incident_type == 'hatch':
        table_headers = '<th>Incident ID</th><th>Date</th><th>Vessel</th><th>Description</th><th>Severity</th>'
    elif incident_type == 'foundering':
        table_headers = '<th>Incident ID</th><th>Date</th><th>Vessel</th><th>Description</th><th>Fatalities</th>'
    elif incident_type == 'fatality':
        table_headers = '<th>Incident ID</th><th>Date</th><th>Vessel</th><th>Description</th><th>Cause of Death</th>'
    else:
        table_headers = '<th>Incident ID</th><th>Date</th><th>Vessel</th><th>Description</th>'

    html = f\'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Detailed Analysis</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; font-size: 1.1em; opacity: 0.9; }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1e3c72;
            border-bottom: 3px solid #1e3c72;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .plot-container {{ margin: 30px 0; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #1e3c72;
            color: white;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .description-cell {{
            max-width: 600px;
            cursor: pointer;
        }}
        .description-summary {{
            font-size: 0.95em;
            color: #333;
            line-height: 1.4;
        }}
        .view-full-btn {{
            display: inline-block;
            margin-left: 8px;
            padding: 4px 12px;
            background: #2a5298;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
        }}
        .view-full-btn:hover {{ background: #1e3c72; }}

        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.6);
        }}
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 0;
            border-radius: 10px;
            width: 80%;
            max-width: 800px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .modal-header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 20px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-header h2 {{ margin: 0; }}
        .close {{
            color: white;
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close:hover {{ color: #ffdd44; }}
        .modal-body {{ padding: 30px; }}
        .incident-meta {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2a5298;
        }}
        .incident-meta p {{ margin: 8px 0; font-size: 0.95em; }}
        .incident-meta strong {{
            color: #1e3c72;
            margin-right: 10px;
            min-width: 100px;
            display: inline-block;
        }}
        .incident-description {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }}
        .incident-description h3 {{
            color: #1e3c72;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}

        /* Pagination styles */
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
            gap: 10px;
        }}
        .pagination button {{
            padding: 8px 16px;
            background: #2a5298;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        }}
        .pagination button:hover {{ background: #1e3c72; }}
        .pagination button:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        .pagination-info {{
            font-size: 0.9em;
            color: #666;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Detailed Analysis Report</p>
        <p>Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
    </div>

    <!-- Modal for full incident details -->
    <div id="incidentModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Incident Details</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="modalBodyContent"></div>
        </div>
    </div>

    <div class="section">
        <h2>Interactive Visualizations</h2>
\'''

    # Add visualization placeholders
    for viz_name, fig in visualizations:
        html += f'        <div class="plot-container" id="plot-{viz_name}"></div>\\n'

    html += \'''    </div>

    <div class="section">
        <h2>Incident Details</h2>
        <div class="loading" id="loadingMessage">Loading incident data...</div>
        <div id="tableContainer" style="display:none;">
            <table id="incidentTable">
                <thead>
                    <tr>
\'''
    html += f'                        {table_headers}\\n'
    html += \'''                    </tr>
                </thead>
                <tbody id="tableBody">
                </tbody>
            </table>

            <!-- Pagination controls -->
            <div class="pagination">
                <button onclick="changePage(-1)" id="prevButton">← Previous</button>
                <span class="pagination-info" id="pageInfo">Page 1</span>
                <button onclick="changePage(1)" id="nextButton">Next →</button>
            </div>
        </div>
    </div>

    <script>
        let allIncidents = [];
        let currentPage = 1;
        const itemsPerPage = 25;

        // Load CSV data
        Papa.parse('\''' + csv_relative_path + '''\', {
            download: true,
            header: true,
            complete: function(results) {
                allIncidents = results.data;
                document.getElementById('loadingMessage').style.display = 'none';
                document.getElementById('tableContainer').style.display = 'block';
                renderPage();
            },
            error: function(error) {
                document.getElementById('loadingMessage').innerHTML =
                    '<span style="color: #ff4444;">Error loading data: ' + error.message + '</span>';
            }
        });

        function renderPage() {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';

            const start = (currentPage - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const pageData = allIncidents.slice(start, end);

            pageData.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.incident_id || 'N/A'}</td>
                    <td>${row.date || 'Unknown'}</td>
                    <td>${row.vessel_name || 'Unknown'}</td>
                    <td class="description-cell">
                        <div class="description-summary">${truncateText(row.description, 150)}</div>
                        <button class="view-full-btn" onclick='showIncidentDetails(${{JSON.stringify(row).replace(/'/g, "&#39;")}})'>View Full Details</button>
                    </td>
                    <td>${getExtraColumn(row)}</td>
                `;
                tbody.appendChild(tr);
            });

            updatePaginationInfo();
        }

        function getExtraColumn(row) {
            const type = '{incident_type}';
            if (type === 'hatch') return row.severity || 'N/A';
            if (type === 'foundering') return row.fatalities || '0';
            if (type === 'fatality') return row.incident_type || 'Unknown';
            return '';
        }}

        function truncateText(text, maxLength) {{
            if (!text) return 'No description available';
            text = String(text);
            if (text.length <= maxLength) return text;
            return text.substring(0, maxLength - 3) + '...';
        }}

        function changePage(delta) {{
            const totalPages = Math.ceil(allIncidents.length / itemsPerPage);
            currentPage = Math.max(1, Math.min(currentPage + delta, totalPages));
            renderPage();
        }}

        function updatePaginationInfo() {{
            const totalPages = Math.ceil(allIncidents.length / itemsPerPage);
            document.getElementById('pageInfo').textContent =
                `Page ${{currentPage}} of ${{totalPages}} (${{allIncidents.length}} total incidents)`;
            document.getElementById('prevButton').disabled = currentPage === 1;
            document.getElementById('nextButton').disabled = currentPage === totalPages;
        }}

        function showIncidentDetails(incident) {{
            const modal = document.getElementById('incidentModal');
            const modalBody = document.getElementById('modalBodyContent');

            modalBody.innerHTML = `
                <div class="incident-meta">
                    <p><strong>Incident ID:</strong> ${{incident.incident_id || 'N/A'}}</p>
                    <p><strong>Date:</strong> ${{incident.date || 'Unknown'}}</p>
                    <p><strong>Vessel:</strong> ${{incident.vessel_name || 'Unknown'}}</p>
                    <p><strong>Location:</strong> ${{incident.location || 'N/A'}}</p>
                    <p><strong>Data Source:</strong> ${{incident.source || 'N/A'}}</p>
                    ${{incident.severity ? '<p><strong>Severity:</strong> ' + incident.severity + '</p>' : ''}}
                    ${{incident.fatalities ? '<p><strong>Fatalities:</strong> ' + incident.fatalities + '</p>' : ''}}
                    ${{incident.injuries ? '<p><strong>Injuries:</strong> ' + incident.injuries + '</p>' : ''}}
                </div>
                <div class="incident-description">
                    <h3>Full Incident Description</h3>
                    <p>${{incident.description || 'No description available'}}</p>
                </div>
            `;

            modal.style.display = 'block';
        }}

        function closeModal() {{
            document.getElementById('incidentModal').style.display = 'none';
        }}

        // Close modal when clicking outside
        window.onclick = function(event) {{
            const modal = document.getElementById('incidentModal');
            if (event.target == modal) {{
                modal.style.display = 'none';
            }}
        }}

        // Close modal with Escape key
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                closeModal();
            }}
        }});
\'''

    # Add visualization scripts
    for viz_name, fig in visualizations:
        plot_json = fig.to_json()
        html += f"\\n        Plotly.newPlot('plot-{viz_name}', {plot_json});\\n"

    html += \'''    </script>
</body>
</html>\'''

    output_file = output_dir / f'{incident_type}_analysis.html'
    output_file.write_text(html)
    logger.info(f"✓ Generated optimized report: {output_file}")'''

# Read the current file
with open('scripts/marine_safety/generate_incident_report.py', 'r') as f:
    content = f.read()

# Find the section to replace
start_marker = '    html = f"""'
end_marker = '    logger.info(f"Detailed report saved to {output_file}")'

start_pos = content.find(start_marker)
end_pos = content.find(end_marker)

if start_pos == -1 or end_pos == -1:
    print(f'ERROR: Could not find markers')
    exit(1)

# Replace the section
new_content = content[:start_pos] + OPTIMIZED_TEMPLATE + content[end_pos:]

# Write back
with open('scripts/marine_safety/generate_incident_report.py', 'w') as f:
    f.write(new_content)

print("✓ Successfully integrated optimized HTML template")
print(f"  - Replaced {len(content) - len(new_content)} characters")
print(f"  - Added PapaParse library for CSV loading")
print(f"  - Implemented pagination (25 records/page)")
print(f"  - Added modal dialogs for incident drilldown")
