"""
RESTful API for Well Production Dashboard.

Provides API endpoints for dashboard data access and manipulation.
"""

try:
    from flask import Flask, jsonify, request, send_file
    from flask_cors import CORS

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

    # Mock classes for when Flask is not installed
    class Flask:
        def __init__(self, *args, **kwargs):
            pass

        def route(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator

        def run(self, *args, **kwargs):
            pass

    class CORS:
        def __init__(self, *args, **kwargs):
            pass

    jsonify = lambda x: x
    request = None
    send_file = None

import io
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from worldenergydata.common import get_logger

from .well_production import WellDashboardConfig, WellProductionDashboard

logger = get_logger(__name__)


class DashboardAPI:
    """RESTful API for dashboard operations."""

    def __init__(
        self, dashboard: Optional[WellProductionDashboard] = None, port: int = 5000
    ):
        """
        Initialize API.

        Args:
            dashboard: Dashboard instance
            port: API port
        """
        self.app = Flask(__name__)
        self.dashboard = dashboard or WellProductionDashboard()
        self.port = port

        # Enable CORS
        CORS(self.app)

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register API routes."""

        @self.app.route("/api/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            return jsonify(
                {"status": "healthy", "timestamp": datetime.now().isoformat()}
            )

        @self.app.route("/api/wells", methods=["GET"])
        def get_wells():
            """Get list of wells."""
            if self.dashboard.well_data is None:
                return jsonify({"wells": []})

            wells = self.dashboard.well_data["well_id"].unique().tolist()
            return jsonify({"wells": wells})

        @self.app.route("/api/wells/<well_id>", methods=["GET"])
        def get_well(well_id):
            """Get specific well data."""
            if self.dashboard.well_data is None:
                return jsonify({"error": "No data loaded"}), 404

            well_data = self.dashboard.well_data[
                self.dashboard.well_data["well_id"] == well_id
            ]

            if well_data.empty:
                return jsonify({"error": f"Well {well_id} not found"}), 404

            return jsonify({"well_id": well_id, "data": well_data.to_dict("records")})

        @self.app.route("/api/dashboard/data", methods=["GET"])
        def get_dashboard_data():
            """Get complete dashboard data."""
            data = self.dashboard.get_dashboard_data()
            return jsonify(data)

        @self.app.route("/api/dashboard/export", methods=["POST"])
        def export_dashboard():
            """Export dashboard."""
            format = request.json.get("format", "pdf")

            try:
                content = self.dashboard.export_dashboard(format)

                if format == "pdf":
                    mimetype = "application/pdf"
                    filename = "dashboard.pdf"
                else:
                    mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    filename = "dashboard.xlsx"

                return send_file(
                    io.BytesIO(content),
                    mimetype=mimetype,
                    as_attachment=True,
                    download_name=filename,
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/dashboard/metrics/<well_id>", methods=["GET"])
        def get_well_metrics(well_id):
            """Get economic metrics for a well."""
            metrics = self.dashboard.create_economic_metrics(well_id)

            if not metrics:
                return jsonify({"error": f"No metrics for well {well_id}"}), 404

            return jsonify({"well_id": well_id, "metrics": metrics})

        @self.app.route("/api/dashboard/decline/<well_id>", methods=["GET"])
        def get_decline_curve(well_id):
            """Get decline curve analysis for a well."""
            decline = self.dashboard.create_decline_curve(well_id)

            if not decline:
                return (
                    jsonify({"error": f"No decline analysis for well {well_id}"}),
                    404,
                )

            return jsonify({"well_id": well_id, "decline_analysis": decline})

        @self.app.route("/api/fields", methods=["GET"])
        def get_fields():
            """Get list of fields."""
            if (
                self.dashboard.well_data is None
                or "field" not in self.dashboard.well_data
            ):
                return jsonify({"fields": []})

            fields = self.dashboard.well_data["field"].unique().tolist()
            return jsonify({"fields": fields})

        @self.app.route("/api/fields/<field_name>", methods=["GET"])
        def get_field(field_name):
            """Get field aggregated data."""
            if self.dashboard.well_data is None:
                return jsonify({"error": "No data loaded"}), 404

            field_data = self.dashboard.well_data[
                self.dashboard.well_data.get("field") == field_name
            ]

            if field_data.empty:
                return jsonify({"error": f"Field {field_name} not found"}), 404

            # Aggregate field data
            from .well_production import FieldAggregator

            aggregator = FieldAggregator()
            aggregated = aggregator.aggregate_field_data(field_data, field_name)

            return jsonify({"field": field_name, "data": aggregated.to_dict("records")})

        @self.app.route("/api/verification/<well_id>", methods=["GET"])
        def get_verification(well_id):
            """Get verification results for a well."""
            if well_id not in self.dashboard.verification_results:
                return jsonify({"error": f"No verification for well {well_id}"}), 404

            results = self.dashboard.verification_results[well_id]
            indicators = self.dashboard.get_quality_indicators(well_id)

            return jsonify(
                {"well_id": well_id, "verification": results, "indicators": indicators}
            )

        @self.app.route("/api/verification/<well_id>", methods=["POST"])
        def run_verification(well_id):
            """Run verification for a well."""
            if self.dashboard.well_data is None:
                return jsonify({"error": "No data loaded"}), 404

            well_data = self.dashboard.well_data[
                self.dashboard.well_data["well_id"] == well_id
            ]

            if well_data.empty:
                return jsonify({"error": f"Well {well_id} not found"}), 404

            results = self.dashboard.verify_well_data(well_data)

            return jsonify({"well_id": well_id, "verification": results})

        @self.app.route("/api/dashboard/filters", methods=["GET"])
        def get_filters():
            """Get available filters."""
            return jsonify({"filters": self.dashboard.filters})

        @self.app.route("/api/dashboard/filters", methods=["POST"])
        def apply_filters():
            """Apply filters to dashboard."""
            filters = request.json.get("filters", {})

            for filter_name, filter_value in filters.items():
                self.dashboard.add_filter(filter_name, filter_value)

            filtered_data = self.dashboard.apply_filters()

            return jsonify(
                {
                    "filters": filters,
                    "row_count": len(filtered_data),
                    "data": filtered_data.head(100).to_dict(
                        "records"
                    ),  # Return first 100 rows
                }
            )

        @self.app.route("/api/dashboard/performance", methods=["GET"])
        def get_performance():
            """Get dashboard performance metrics."""
            metrics = self.dashboard.get_performance_metrics()
            return jsonify(metrics)

        @self.app.route("/api/dashboard/audit/<well_id>", methods=["GET"])
        def get_audit_trail(well_id):
            """Get audit trail for a well."""
            trail = self.dashboard.get_audit_trail(well_id)

            if trail.empty:
                return jsonify({"audit_trail": []})

            return jsonify(
                {"well_id": well_id, "audit_trail": trail.to_dict("records")}
            )

    def run(self, host: str = "127.0.0.1", debug: bool = False):
        """
        Run the API server.

        Args:
            host: Host to bind to
            debug: Enable debug mode
        """
        logger.info(f"Starting API server on http://{host}:{self.port}")
        self.app.run(host=host, port=self.port, debug=debug)

    def get_app(self):
        """Get Flask app instance for testing."""
        return self.app
