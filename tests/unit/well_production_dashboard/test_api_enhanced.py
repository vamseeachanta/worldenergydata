"""
Enhanced tests for Well Production Dashboard API with verification integration.

Tests API endpoints, WebSocket support, caching, and authentication.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

# Mock Flask and related imports
with patch("worldenergydata.well_production_dashboard.api_enhanced.Flask"):
    with patch("worldenergydata.well_production_dashboard.api_enhanced.jsonify"):
        from worldenergydata.well_production_dashboard.api_enhanced import (
            APIAuthenticator,
            CacheManager,
            EnhancedDashboardAPI,
            RealTimeUpdateManager,
            VerificationMetadataAPI,
            WebSocketManager,
        )


class TestEnhancedDashboardAPI:
    """Test enhanced API functionality."""

    @pytest.fixture
    def mock_dashboard(self):
        """Create mock dashboard."""
        dashboard = Mock()
        dashboard.well_data = pd.DataFrame(
            {
                "well_id": ["W001", "W002", "W003"],
                "field": ["Field1", "Field1", "Field2"],
                "oil_rate": [1000, 1500, 2000],
                "gas_rate": [5000, 7500, 10000],
                "water_rate": [100, 150, 200],
                "date": pd.date_range("2024-01-01", periods=3),
                "quality_score": [0.95, 0.88, 0.92],
            }
        )
        dashboard.verification_results = {
            "W001": {"status": "verified", "score": 0.95},
            "W002": {"status": "warning", "score": 0.88},
            "W003": {"status": "verified", "score": 0.92},
        }
        return dashboard

    @pytest.fixture
    def api(self, mock_dashboard):
        """Create API instance."""
        return EnhancedDashboardAPI(dashboard=mock_dashboard)

    def test_init(self, api):
        """Test API initialization."""
        assert api.dashboard is not None
        assert api.cache_manager is not None
        assert api.websocket_manager is not None
        assert api.authenticator is not None

    def test_verified_well_data_endpoint(self, api):
        """Test verified well data endpoints."""
        # Test get verified wells
        response = api.get_verified_wells()
        assert "wells" in response
        assert "quality_metadata" in response
        assert len(response["wells"]) == 2  # Only verified wells

        # Test get well with verification
        response = api.get_well_with_verification("W001")
        assert response["well_id"] == "W001"
        assert "data" in response
        assert "verification" in response
        assert response["verification"]["status"] == "verified"
        assert response["verification"]["score"] == 0.95

    def test_dashboard_data_with_quality(self, api):
        """Test dashboard data API with quality metadata."""
        response = api.get_dashboard_data_with_quality()

        assert "data" in response
        assert "quality_summary" in response
        assert "verification_status" in response
        assert "data_freshness" in response

        quality_summary = response["quality_summary"]
        assert "average_score" in quality_summary
        assert "verified_count" in quality_summary
        assert "warning_count" in quality_summary
        assert "failed_count" in quality_summary

    def test_quality_filtered_data(self, api):
        """Test quality-filtered data retrieval."""
        # Test high quality filter
        response = api.get_quality_filtered_data(min_score=0.9)
        assert len(response["data"]) == 2  # W001 and W003

        # Test with status filter
        response = api.get_quality_filtered_data(status="verified")
        assert len(response["data"]) == 2

        # Test combined filters
        response = api.get_quality_filtered_data(
            min_score=0.9, status="verified", fields=["Field1"]
        )
        assert len(response["data"]) == 1  # Only W001

    def test_real_time_metrics_endpoint(self, api):
        """Test real-time metrics endpoint."""
        response = api.get_real_time_metrics("W001")

        assert "well_id" in response
        assert "current_rates" in response
        assert "trend" in response
        assert "anomaly_detection" in response
        assert "timestamp" in response

        # Check current rates
        rates = response["current_rates"]
        assert "oil" in rates
        assert "gas" in rates
        assert "water" in rates

    def test_batch_verification_endpoint(self, api):
        """Test batch verification endpoint."""
        well_ids = ["W001", "W002", "W003"]
        response = api.run_batch_verification(well_ids)

        assert "results" in response
        assert len(response["results"]) == 3
        assert "summary" in response

        summary = response["summary"]
        assert summary["total"] == 3
        assert summary["verified"] == 2
        assert summary["warnings"] == 1

    def test_export_with_verification(self, api):
        """Test export endpoints with verification metadata."""
        # Test PDF export
        response = api.export_with_verification(
            format="pdf", include_verification=True, include_audit_trail=True
        )
        assert response["status"] == "success"
        assert response["format"] == "pdf"
        assert response["includes_verification"] is True

        # Test Excel export
        response = api.export_with_verification(
            format="excel", include_verification=True, quality_threshold=0.9
        )
        assert response["status"] == "success"
        assert response["filtered_count"] > 0


class TestWebSocketManager:
    """Test WebSocket real-time updates."""

    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_client_connection(self, websocket_manager):
        """Test client connection handling."""
        client_id = await websocket_manager.connect_client()
        assert client_id is not None
        assert client_id in websocket_manager.clients

        # Disconnect client
        await websocket_manager.disconnect_client(client_id)
        assert client_id not in websocket_manager.clients

    @pytest.mark.asyncio
    async def test_broadcast_update(self, websocket_manager):
        """Test broadcasting updates to clients."""
        # Connect multiple clients
        client1 = await websocket_manager.connect_client()
        client2 = await websocket_manager.connect_client()

        # Broadcast update
        update = {
            "type": "production_update",
            "well_id": "W001",
            "data": {"oil_rate": 1100},
        }

        await websocket_manager.broadcast_update(update)

        # Check both clients received update
        assert websocket_manager.get_client_queue(client1).qsize() == 1
        assert websocket_manager.get_client_queue(client2).qsize() == 1

    @pytest.mark.asyncio
    async def test_targeted_update(self, websocket_manager):
        """Test sending update to specific client."""
        client1 = await websocket_manager.connect_client()
        client2 = await websocket_manager.connect_client()

        update = {"type": "personal_notification"}

        await websocket_manager.send_to_client(client1, update)

        # Only client1 should receive update
        assert websocket_manager.get_client_queue(client1).qsize() == 1
        assert websocket_manager.get_client_queue(client2).qsize() == 0

    @pytest.mark.asyncio
    async def test_subscription_management(self, websocket_manager):
        """Test well subscription management."""
        client = await websocket_manager.connect_client()

        # Subscribe to wells
        await websocket_manager.subscribe_to_well(client, "W001")
        await websocket_manager.subscribe_to_well(client, "W002")

        assert "W001" in websocket_manager.get_client_subscriptions(client)
        assert "W002" in websocket_manager.get_client_subscriptions(client)

        # Unsubscribe
        await websocket_manager.unsubscribe_from_well(client, "W001")
        assert "W001" not in websocket_manager.get_client_subscriptions(client)

    @pytest.mark.asyncio
    async def test_real_time_data_push(self, websocket_manager):
        """Test real-time data push mechanism."""
        client = await websocket_manager.connect_client()
        await websocket_manager.subscribe_to_well(client, "W001")

        # Push production update
        await websocket_manager.push_production_update(
            well_id="W001", data={"oil_rate": 1050, "timestamp": datetime.now()}
        )

        # Client should receive update
        queue = websocket_manager.get_client_queue(client)
        assert queue.qsize() == 1
        update = await queue.get()
        assert update["well_id"] == "W001"
        assert update["data"]["oil_rate"] == 1050


class TestCacheManager:
    """Test cache infrastructure."""

    @pytest.fixture
    def cache_manager(self):
        """Create cache manager."""
        return CacheManager()

    def test_cache_initialization(self, cache_manager):
        """Test cache initialization."""
        assert cache_manager.cache_enabled is True
        assert cache_manager.default_ttl == 300  # 5 minutes
        assert cache_manager.cache_store is not None

    def test_cache_set_get(self, cache_manager):
        """Test setting and getting cache values."""
        key = "well:W001:production"
        data = {"oil_rate": 1000, "gas_rate": 5000}

        # Set cache
        cache_manager.set(key, data, ttl=60)

        # Get from cache
        cached = cache_manager.get(key)
        assert cached == data

    def test_cache_expiration(self, cache_manager):
        """Test cache expiration."""
        key = "test:expiration"
        data = {"value": 42}

        # Set with short TTL
        cache_manager.set(key, data, ttl=1)

        # Should exist immediately
        assert cache_manager.get(key) == data

        # Wait for expiration
        import time

        time.sleep(2)

        # Should be expired
        assert cache_manager.get(key) is None

    def test_cache_invalidation(self, cache_manager):
        """Test cache invalidation."""
        # Set multiple related keys
        cache_manager.set("well:W001:production", {"oil": 1000})
        cache_manager.set("well:W001:economics", {"npv": 1000000})
        cache_manager.set("well:W002:production", {"oil": 1500})

        # Invalidate W001 data
        cache_manager.invalidate_pattern("well:W001:*")

        # W001 data should be gone
        assert cache_manager.get("well:W001:production") is None
        assert cache_manager.get("well:W001:economics") is None

        # W002 data should remain
        assert cache_manager.get("well:W002:production") is not None

    def test_cache_stats(self, cache_manager):
        """Test cache statistics."""
        # Perform some operations
        cache_manager.set("key1", "value1")
        cache_manager.get("key1")  # Hit
        cache_manager.get("key2")  # Miss

        stats = cache_manager.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_decorator(self, cache_manager):
        """Test cache decorator."""
        call_count = 0

        @cache_manager.cached(ttl=60)
        def expensive_calculation(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute
        result1 = expensive_calculation(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = expensive_calculation(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different argument - should execute
        result3 = expensive_calculation(10)
        assert result3 == 20
        assert call_count == 2


class TestAPIAuthenticator:
    """Test API authentication."""

    @pytest.fixture
    def authenticator(self):
        """Create authenticator."""
        return APIAuthenticator()

    def test_token_generation(self, authenticator):
        """Test API token generation."""
        user_id = "user123"
        token = authenticator.generate_token(user_id)

        assert token is not None
        assert len(token) >= 32
        assert authenticator.validate_token(token)

    def test_token_validation(self, authenticator):
        """Test token validation."""
        token = authenticator.generate_token("user123")

        # Valid token
        assert authenticator.validate_token(token) is True

        # Invalid token
        assert authenticator.validate_token("invalid_token") is False

    def test_token_expiration(self, authenticator):
        """Test token expiration."""
        token = authenticator.generate_token("user123", ttl=1)

        # Should be valid immediately
        assert authenticator.validate_token(token) is True

        # Wait for expiration
        import time

        time.sleep(2)

        # Should be expired
        assert authenticator.validate_token(token) is False

    def test_api_key_authentication(self, authenticator):
        """Test API key authentication."""
        # Generate API key
        api_key = authenticator.generate_api_key("client_app")

        # Validate API key
        assert authenticator.validate_api_key(api_key) is True

        # Test rate limiting
        for _ in range(100):
            assert authenticator.check_rate_limit(api_key) is True

        # Should hit rate limit
        assert authenticator.check_rate_limit(api_key) is False

    def test_role_based_access(self, authenticator):
        """Test role-based access control."""
        # Create users with different roles
        admin_token = authenticator.generate_token("admin", role="admin")
        user_token = authenticator.generate_token("user", role="user")

        # Check permissions
        assert authenticator.check_permission(admin_token, "write") is True
        assert authenticator.check_permission(user_token, "write") is True
        assert authenticator.check_permission(user_token, "delete") is False
        assert authenticator.check_permission(user_token, "read") is True


class TestVerificationMetadataAPI:
    """Test verification metadata API endpoints."""

    @pytest.fixture
    def verification_api(self):
        """Create verification API."""
        return VerificationMetadataAPI()

    def test_get_quality_scores(self, verification_api):
        """Test getting quality scores."""
        scores = verification_api.get_quality_scores(["W001", "W002"])

        assert len(scores) == 2
        assert "W001" in scores
        assert "W002" in scores
        assert 0 <= scores["W001"] <= 1

    def test_get_verification_history(self, verification_api):
        """Test getting verification history."""
        history = verification_api.get_verification_history("W001")

        assert isinstance(history, list)
        if history:
            record = history[0]
            assert "timestamp" in record
            assert "status" in record
            assert "score" in record
            assert "checks" in record

    def test_get_anomaly_report(self, verification_api):
        """Test getting anomaly report."""
        report = verification_api.get_anomaly_report("W001")

        assert "anomalies" in report
        assert "summary" in report
        assert "recommendations" in report

    def test_get_audit_trail_details(self, verification_api):
        """Test getting detailed audit trail."""
        trail = verification_api.get_audit_trail_details(
            well_id="W001", start_date="2024-01-01", end_date="2024-12-31"
        )

        assert "entries" in trail
        assert "total_count" in trail
        assert "date_range" in trail


class TestRealTimeUpdateManager:
    """Test real-time update management."""

    @pytest.fixture
    def update_manager(self):
        """Create update manager."""
        return RealTimeUpdateManager()

    @pytest.mark.asyncio
    async def test_production_monitoring(self, update_manager):
        """Test production monitoring."""
        # Start monitoring
        await update_manager.start_monitoring("W001")

        # Should receive periodic updates
        update = await update_manager.get_next_update("W001")
        assert update is not None
        assert "well_id" in update
        assert "timestamp" in update
        assert "data" in update

        # Stop monitoring
        await update_manager.stop_monitoring("W001")

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, update_manager):
        """Test real-time anomaly detection."""
        # Configure anomaly detection
        update_manager.configure_anomaly_detection(
            sensitivity="high", methods=["statistical", "ml"]
        )

        # Simulate anomalous data
        anomaly = await update_manager.detect_anomaly(
            {
                "well_id": "W001",
                "oil_rate": 5000,  # Unusually high
                "timestamp": datetime.now(),
            }
        )

        assert anomaly is not None
        assert anomaly["detected"] is True
        assert "severity" in anomaly
        assert "description" in anomaly

    @pytest.mark.asyncio
    async def test_update_batching(self, update_manager):
        """Test update batching for performance."""
        # Add multiple updates
        for i in range(10):
            await update_manager.queue_update(
                {"well_id": f"W00{i}", "data": {"oil_rate": 1000 + i * 100}}
            )

        # Get batched updates
        batch = await update_manager.get_batched_updates(batch_size=5)
        assert len(batch) == 5

        # Remaining updates
        batch2 = await update_manager.get_batched_updates(batch_size=10)
        assert len(batch2) == 5


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @pytest.fixture
    def mock_dashboard(self):
        """Create mock dashboard for integration scenarios."""
        dashboard = Mock()
        dashboard.well_data = pd.DataFrame(
            {
                "well_id": ["W001", "W002", "W003"],
                "field": ["Field1", "Field1", "Field2"],
                "oil_rate": [1000, 1500, 2000],
                "gas_rate": [5000, 7500, 10000],
                "water_rate": [100, 150, 200],
                "date": pd.date_range("2024-01-01", periods=3),
                "quality_score": [0.95, 0.88, 0.92],
            }
        )
        dashboard.verification_results = {
            "W001": {"status": "verified", "score": 0.95},
            "W002": {"status": "warning", "score": 0.88},
            "W003": {"status": "verified", "score": 0.92},
        }
        dashboard.get_dashboard_data.return_value = {"wells": 3}
        dashboard.get_quality_indicators.return_value = {"quality_score": 0.95}
        return dashboard

    @pytest.fixture
    def integrated_api(self, mock_dashboard):
        """Create fully integrated API."""
        api = EnhancedDashboardAPI(dashboard=mock_dashboard)
        api.initialize_all_services()
        return api

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, integrated_api):
        """Test complete workflow from data to real-time updates."""
        # 1. Authenticate
        token = integrated_api.authenticator.generate_token("test_user")

        # 2. Get verified data with caching
        response = integrated_api.get_verified_wells_cached(token)
        assert response["from_cache"] is False  # First call

        response2 = integrated_api.get_verified_wells_cached(token)
        assert response2["from_cache"] is True  # Cached

        # 3. Subscribe to real-time updates
        client_id = await integrated_api.websocket_manager.connect_client()
        await integrated_api.websocket_manager.subscribe_to_well(client_id, "W001")

        # 4. Trigger update
        await integrated_api.trigger_production_update("W001")

        # 5. Verify update received
        queue = integrated_api.websocket_manager.get_client_queue(client_id)
        assert queue.qsize() > 0

    def test_performance_under_load(self, integrated_api):
        """Test API performance under load."""
        import threading
        import time

        def make_request():
            integrated_api.get_dashboard_data_with_quality()

        # Simulate concurrent requests
        threads = []
        start_time = time.time()

        for _ in range(50):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time

        # Should handle 50 concurrent requests in reasonable time
        assert elapsed < 5.0  # Less than 5 seconds

    def test_graceful_degradation(self, integrated_api):
        """Test graceful degradation when services fail."""
        # Disable cache
        integrated_api.cache_manager.cache_enabled = False

        # API should still work
        response = integrated_api.get_dashboard_data_with_quality()
        assert response is not None

        # Disable WebSocket
        integrated_api.websocket_manager.enabled = False

        # API should still work
        response = integrated_api.get_real_time_metrics("W001")
        assert response is not None
        assert "error" not in response
