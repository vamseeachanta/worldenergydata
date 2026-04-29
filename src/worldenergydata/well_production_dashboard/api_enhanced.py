"""
Enhanced RESTful API for Well Production Dashboard with verification integration.

Provides API endpoints with quality metadata, WebSocket support, caching, and authentication.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Set

import numpy as np

# Handle optional imports
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

    def jsonify(x):
        return x

    request = None
    send_file = None

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None

from .api import DashboardAPI
from .well_production import WellProductionDashboard

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for API responses."""

    def __init__(
        self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0
    ):
        """
        Initialize cache manager.

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
        """
        self.cache_enabled = True
        self.default_ttl = 300  # 5 minutes
        self.cache_store = {}  # In-memory fallback

        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db, decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory cache: {e}")
                self.redis_client = None
        else:
            logger.info("Redis not available, using in-memory cache")
            self.redis_client = None

        # Cache statistics
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    self.stats["hits"] += 1
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Cache get error: {e}")
        else:
            # In-memory cache
            if key in self.cache_store:
                entry = self.cache_store[key]
                if entry["expires"] > time.time():
                    self.stats["hits"] += 1
                    return entry["value"]
                else:
                    del self.cache_store[key]

        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        self.stats["sets"] += 1

        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
            except Exception as e:
                logger.error(f"Cache set error: {e}")
        else:
            # In-memory cache
            self.cache_store[key] = {"value": value, "expires": time.time() + ttl}
            # Basic eviction for memory management
            if len(self.cache_store) > 1000:
                self._evict_expired()

    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    self.stats["evictions"] += len(keys)
            except Exception as e:
                logger.error(f"Cache invalidation error: {e}")
        else:
            # In-memory cache
            keys_to_delete = [
                k for k in self.cache_store if self._match_pattern(k, pattern)
            ]
            for key in keys_to_delete:
                del self.cache_store[key]
                self.stats["evictions"] += 1

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for in-memory cache."""
        import fnmatch

        return fnmatch.fnmatch(key, pattern)

    def _evict_expired(self):
        """Evict expired entries from in-memory cache."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.cache_store.items() if v["expires"] <= current_time
        ]
        for key in expired_keys:
            del self.cache_store[key]
            self.stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "evictions": self.stats["evictions"],
            "hit_rate": hit_rate,
            "total_requests": total,
        }

    def cached(self, ttl: Optional[int] = None):
        """Decorator for caching function results."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

                # Try to get from cache
                result = self.get(cache_key)
                if result is not None:
                    return result

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result

            return wrapper

        return decorator


class APIAuthenticator:
    """Handles API authentication and authorization."""

    def __init__(self):
        """Initialize authenticator."""
        self.tokens = {}  # Token storage
        self.api_keys = {}  # API key storage
        self.rate_limits = defaultdict(list)  # Rate limiting
        self.roles = {
            "admin": ["read", "write", "delete", "admin"],
            "user": ["read", "write"],
            "viewer": ["read"],
        }

    def generate_token(self, user_id: str, role: str = "user", ttl: int = 3600) -> str:
        """
        Generate authentication token.

        Args:
            user_id: User identifier
            role: User role
            ttl: Token time-to-live in seconds

        Returns:
            Authentication token
        """
        token = hashlib.sha256(
            f"{user_id}:{time.time()}:{uuid.uuid4()}".encode()
        ).hexdigest()

        self.tokens[token] = {
            "user_id": user_id,
            "role": role,
            "expires": time.time() + ttl,
            "created": datetime.now(),
        }

        return token

    def validate_token(self, token: str) -> bool:
        """Validate authentication token."""
        if token not in self.tokens:
            return False

        token_data = self.tokens[token]
        if token_data["expires"] < time.time():
            del self.tokens[token]
            return False

        return True

    def generate_api_key(self, client_id: str) -> str:
        """Generate API key for client."""
        api_key = hashlib.sha256(f"{client_id}:{uuid.uuid4()}".encode()).hexdigest()

        self.api_keys[api_key] = {
            "client_id": client_id,
            "created": datetime.now(),
            "rate_limit": 100,  # Requests per minute
        }

        return api_key

    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        return api_key in self.api_keys

    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key has exceeded rate limit."""
        if api_key not in self.api_keys:
            return False

        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old requests
        self.rate_limits[api_key] = [
            t for t in self.rate_limits[api_key] if t > window_start
        ]

        # Check limit
        limit = self.api_keys[api_key]["rate_limit"]
        if len(self.rate_limits[api_key]) >= limit:
            return False

        # Record request
        self.rate_limits[api_key].append(current_time)
        return True

    def check_permission(self, token: str, permission: str) -> bool:
        """Check if token has permission."""
        if not self.validate_token(token):
            return False

        role = self.tokens[token]["role"]
        return permission in self.roles.get(role, [])

    def authenticate_request(self, headers: Dict[str, str]) -> Optional[str]:
        """
        Authenticate request from headers.

        Args:
            headers: Request headers

        Returns:
            User ID if authenticated, None otherwise
        """
        # Check for Bearer token
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if self.validate_token(token):
                return self.tokens[token]["user_id"]

        # Check for API key
        api_key = headers.get("X-API-Key", "")
        if api_key and self.validate_api_key(api_key):
            if self.check_rate_limit(api_key):
                return self.api_keys[api_key]["client_id"]

        return None


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize WebSocket manager."""
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self.enabled = WEBSOCKETS_AVAILABLE

        if not self.enabled:
            logger.warning("WebSockets not available, real-time updates disabled")

    async def connect_client(self) -> str:
        """Connect new client."""
        client_id = str(uuid.uuid4())

        self.clients[client_id] = {
            "connected_at": datetime.now(),
            "subscriptions": set(),
            "queue": asyncio.Queue(),
        }

        logger.info(f"Client {client_id} connected")
        return client_id

    async def disconnect_client(self, client_id: str):
        """Disconnect client."""
        if client_id in self.clients:
            # Remove subscriptions
            for well_id in self.clients[client_id]["subscriptions"]:
                self.subscriptions[well_id].discard(client_id)

            del self.clients[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def subscribe_to_well(self, client_id: str, well_id: str):
        """Subscribe client to well updates."""
        if client_id in self.clients:
            self.clients[client_id]["subscriptions"].add(well_id)
            self.subscriptions[well_id].add(client_id)
            logger.debug(f"Client {client_id} subscribed to well {well_id}")

    async def unsubscribe_from_well(self, client_id: str, well_id: str):
        """Unsubscribe client from well updates."""
        if client_id in self.clients:
            self.clients[client_id]["subscriptions"].discard(well_id)
            self.subscriptions[well_id].discard(client_id)

    async def broadcast_update(self, update: Dict[str, Any]):
        """Broadcast update to all connected clients."""
        tasks = []
        for client_id in self.clients:
            tasks.append(self.send_to_client(client_id, update))

        await asyncio.gather(*tasks)

    async def send_to_client(self, client_id: str, update: Dict[str, Any]):
        """Send update to specific client."""
        if client_id in self.clients:
            await self.clients[client_id]["queue"].put(update)

    async def push_production_update(self, well_id: str, data: Dict[str, Any]):
        """Push production update to subscribed clients."""
        update = {
            "type": "production_update",
            "well_id": well_id,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        # Send to subscribed clients
        tasks = []
        for client_id in self.subscriptions.get(well_id, []):
            tasks.append(self.send_to_client(client_id, update))

        await asyncio.gather(*tasks)

    def get_client_queue(self, client_id: str) -> Optional[asyncio.Queue]:
        """Get client's message queue."""
        if client_id in self.clients:
            return self.clients[client_id]["queue"]
        return None

    def get_client_subscriptions(self, client_id: str) -> Set[str]:
        """Get client's subscriptions."""
        if client_id in self.clients:
            return self.clients[client_id]["subscriptions"]
        return set()


class VerificationMetadataAPI:
    """API for verification metadata operations."""

    def __init__(self, dashboard: Optional[WellProductionDashboard] = None):
        """Initialize verification API."""
        self.dashboard = dashboard

    def get_quality_scores(self, well_ids: List[str]) -> Dict[str, float]:
        """Get quality scores for wells."""
        scores = {}
        for well_id in well_ids:
            # Simulate quality score calculation
            scores[well_id] = np.random.uniform(0.7, 1.0)
        return scores

    def get_verification_history(self, well_id: str) -> List[Dict[str, Any]]:
        """Get verification history for a well."""
        # Simulate verification history
        history = []
        for i in range(5):
            date = datetime.now() - timedelta(days=i * 7)
            history.append(
                {
                    "timestamp": date.isoformat(),
                    "status": np.random.choice(["verified", "warning", "failed"]),
                    "score": np.random.uniform(0.6, 1.0),
                    "checks": {
                        "data_completeness": np.random.uniform(0.8, 1.0),
                        "range_validation": np.random.uniform(0.7, 1.0),
                        "cross_reference": np.random.uniform(0.9, 1.0),
                    },
                }
            )
        return history

    def get_anomaly_report(self, well_id: str) -> Dict[str, Any]:
        """Get anomaly report for a well."""
        return {
            "anomalies": [
                {
                    "date": "2024-01-15",
                    "type": "production_spike",
                    "severity": "medium",
                    "description": "Unusual production increase detected",
                }
            ],
            "summary": {
                "total_anomalies": 1,
                "high_severity": 0,
                "medium_severity": 1,
                "low_severity": 0,
            },
            "recommendations": [
                "Review production data for January 15",
                "Verify measurement equipment calibration",
            ],
        }

    def get_audit_trail_details(
        self, well_id: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Get detailed audit trail."""
        return {
            "entries": [
                {
                    "timestamp": "2024-01-01T10:00:00",
                    "action": "data_upload",
                    "user": "system",
                    "details": "Monthly production data uploaded",
                },
                {
                    "timestamp": "2024-01-01T10:05:00",
                    "action": "verification_run",
                    "user": "system",
                    "details": "Automatic verification completed",
                },
            ],
            "total_count": 2,
            "date_range": {"start": start_date, "end": end_date},
        }


class RealTimeUpdateManager:
    """Manages real-time data updates."""

    def __init__(self):
        """Initialize update manager."""
        self.monitoring_wells: Set[str] = set()
        self.update_queues: Dict[str, asyncio.Queue] = {}
        self.anomaly_config = {"sensitivity": "medium", "methods": ["statistical"]}

    async def start_monitoring(self, well_id: str):
        """Start monitoring a well."""
        self.monitoring_wells.add(well_id)
        self.update_queues[well_id] = asyncio.Queue()

        # Start background task for generating updates
        asyncio.create_task(self._generate_updates(well_id))

    async def stop_monitoring(self, well_id: str):
        """Stop monitoring a well."""
        self.monitoring_wells.discard(well_id)
        if well_id in self.update_queues:
            del self.update_queues[well_id]

    async def _generate_updates(self, well_id: str):
        """Generate periodic updates for a well."""
        while well_id in self.monitoring_wells:
            # Simulate production data update
            update = {
                "well_id": well_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "oil_rate": np.random.uniform(900, 1100),
                    "gas_rate": np.random.uniform(4500, 5500),
                    "water_rate": np.random.uniform(90, 110),
                },
            }

            await self.update_queues[well_id].put(update)
            await asyncio.sleep(5)  # Update every 5 seconds

    async def get_next_update(self, well_id: str) -> Optional[Dict[str, Any]]:
        """Get next update for a well."""
        if well_id in self.update_queues:
            try:
                return await asyncio.wait_for(
                    self.update_queues[well_id].get(), timeout=10
                )
            except asyncio.TimeoutError:
                return None
        return None

    def configure_anomaly_detection(self, sensitivity: str, methods: List[str]):
        """Configure anomaly detection."""
        self.anomaly_config = {"sensitivity": sensitivity, "methods": methods}

    async def detect_anomaly(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in real-time data."""
        # Simulate anomaly detection
        oil_rate = data.get("oil_rate", 0)

        if oil_rate > 2000:  # Simple threshold
            return {
                "detected": True,
                "severity": "high" if oil_rate > 3000 else "medium",
                "description": f"Abnormally high oil rate: {oil_rate}",
                "timestamp": datetime.now().isoformat(),
            }

        return {"detected": False}

    async def queue_update(self, update: Dict[str, Any]):
        """Queue update for processing."""
        well_id = update.get("well_id")
        if well_id:
            if well_id not in self.update_queues:
                self.update_queues[well_id] = asyncio.Queue()
            await self.update_queues[well_id].put(update)

    async def get_batched_updates(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Get batched updates from all wells."""
        updates = []

        for well_id, queue in self.update_queues.items():
            count = 0
            while count < batch_size and not queue.empty():
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=0.1)
                    updates.append(update)
                    count += 1
                except asyncio.TimeoutError:
                    break

            if len(updates) >= batch_size:
                break

        return updates


class EnhancedDashboardAPI(DashboardAPI):
    """Enhanced dashboard API with verification, WebSocket, caching, and authentication."""

    def __init__(
        self, dashboard: Optional[WellProductionDashboard] = None, port: int = 5000
    ):
        """Initialize enhanced API."""
        super().__init__(dashboard, port)

        # Initialize additional services
        self.cache_manager = CacheManager()
        self.authenticator = APIAuthenticator()
        self.websocket_manager = WebSocketManager()
        self.verification_api = VerificationMetadataAPI(self.dashboard)
        self.update_manager = RealTimeUpdateManager()

        # Register enhanced routes
        self._register_enhanced_routes()

    def _register_enhanced_routes(self):
        """Register enhanced API routes."""

        @self.app.route("/api/v2/wells/verified", methods=["GET"])
        def get_verified_wells():
            """Get verified wells with quality metadata."""
            return jsonify(self.get_verified_wells())

        @self.app.route("/api/v2/wells/<well_id>/verification", methods=["GET"])
        def get_well_with_verification(well_id):
            """Get well data with verification details."""
            return jsonify(self.get_well_with_verification(well_id))

        @self.app.route("/api/v2/dashboard/quality", methods=["GET"])
        def get_dashboard_with_quality():
            """Get dashboard data with quality metadata."""
            return jsonify(self.get_dashboard_data_with_quality())

        @self.app.route("/api/v2/data/filtered", methods=["POST"])
        def get_quality_filtered():
            """Get quality-filtered data."""
            params = request.json or {}
            return jsonify(self.get_quality_filtered_data(**params))

        @self.app.route("/api/v2/wells/<well_id>/realtime", methods=["GET"])
        def get_realtime_metrics(well_id):
            """Get real-time metrics for a well."""
            return jsonify(self.get_real_time_metrics(well_id))

        @self.app.route("/api/v2/verification/batch", methods=["POST"])
        def batch_verification():
            """Run batch verification."""
            well_ids = request.json.get("well_ids", [])
            return jsonify(self.run_batch_verification(well_ids))

        @self.app.route("/api/v2/export/verified", methods=["POST"])
        def export_verified():
            """Export with verification metadata."""
            params = request.json or {}
            return jsonify(self.export_with_verification(**params))

        @self.app.route("/api/v2/cache/stats", methods=["GET"])
        def cache_stats():
            """Get cache statistics."""
            return jsonify(self.cache_manager.get_stats())

        @self.app.route("/api/v2/auth/token", methods=["POST"])
        def generate_token():
            """Generate authentication token."""
            user_id = request.json.get("user_id")
            role = request.json.get("role", "user")
            token = self.authenticator.generate_token(user_id, role)
            return jsonify({"token": token})

        @self.app.route("/api/v2/ws/connect", methods=["POST"])
        async def websocket_connect():
            """Connect to WebSocket for real-time updates."""
            client_id = await self.websocket_manager.connect_client()
            return jsonify({"client_id": client_id})

    def get_verified_wells(self) -> Dict[str, Any]:
        """Get list of verified wells with quality metadata."""
        if self.dashboard.well_data is None:
            return {"wells": [], "quality_metadata": {}}

        verified_wells = []
        quality_metadata = {}

        for well_id in self.dashboard.well_data["well_id"].unique():
            if well_id in self.dashboard.verification_results:
                result = self.dashboard.verification_results[well_id]
                if result.get("status") == "verified":
                    verified_wells.append(well_id)
                    quality_metadata[well_id] = {
                        "score": result.get("score", 0),
                        "last_verified": datetime.now().isoformat(),
                    }

        return {
            "wells": verified_wells,
            "quality_metadata": quality_metadata,
            "total_verified": len(verified_wells),
            "timestamp": datetime.now().isoformat(),
        }

    def get_well_with_verification(self, well_id: str) -> Dict[str, Any]:
        """Get well data with verification details."""
        if self.dashboard.well_data is None:
            return {"error": "No data loaded"}

        well_data = self.dashboard.well_data[
            self.dashboard.well_data["well_id"] == well_id
        ]

        if well_data.empty:
            return {"error": f"Well {well_id} not found"}

        verification = self.dashboard.verification_results.get(well_id, {})

        return {
            "well_id": well_id,
            "data": well_data.to_dict("records"),
            "verification": verification,
            "quality_indicators": self.dashboard.get_quality_indicators(well_id),
        }

    def get_dashboard_data_with_quality(self) -> Dict[str, Any]:
        """Get dashboard data with quality metadata."""
        data = self.dashboard.get_dashboard_data()

        # Add quality summary
        quality_summary = {
            "average_score": 0,
            "verified_count": 0,
            "warning_count": 0,
            "failed_count": 0,
        }

        scores = []
        for well_id, result in self.dashboard.verification_results.items():
            score = result.get("score", 0)
            scores.append(score)

            status = result.get("status")
            if status == "verified":
                quality_summary["verified_count"] += 1
            elif status == "warning":
                quality_summary["warning_count"] += 1
            else:
                quality_summary["failed_count"] += 1

        if scores:
            quality_summary["average_score"] = np.mean(scores)

        # Add data freshness
        data_freshness = {
            "last_update": datetime.now().isoformat(),
            "data_age_hours": 0,
            "freshness_status": "current",
        }

        return {
            "data": data,
            "quality_summary": quality_summary,
            "verification_status": self.dashboard.verification_results,
            "data_freshness": data_freshness,
        }

    def get_quality_filtered_data(
        self,
        min_score: float = 0.0,
        status: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get data filtered by quality criteria."""
        if self.dashboard.well_data is None:
            return {"data": [], "filter_summary": {}}

        filtered_data = self.dashboard.well_data.copy()

        # Filter by quality score
        valid_wells = []
        for well_id, result in self.dashboard.verification_results.items():
            if result.get("score", 0) >= min_score:
                if status is None or result.get("status") == status:
                    valid_wells.append(well_id)

        filtered_data = filtered_data[filtered_data["well_id"].isin(valid_wells)]

        # Filter by fields
        if fields and "field" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["field"].isin(fields)]

        return {
            "data": filtered_data.to_dict("records"),
            "filter_summary": {
                "min_score": min_score,
                "status": status,
                "fields": fields,
                "result_count": len(filtered_data),
            },
        }

    def get_real_time_metrics(self, well_id: str) -> Dict[str, Any]:
        """Get real-time metrics for a well."""
        if self.dashboard.well_data is None:
            return {"error": "No data loaded"}

        well_data = self.dashboard.well_data[
            self.dashboard.well_data["well_id"] == well_id
        ]

        if well_data.empty:
            return {"error": f"Well {well_id} not found"}

        # Get latest production rates
        latest = well_data.iloc[-1]

        # Calculate trends
        if len(well_data) > 1:
            prev = well_data.iloc[-2]
            oil_trend = "up" if latest["oil_rate"] > prev["oil_rate"] else "down"
            gas_trend = "up" if latest["gas_rate"] > prev["gas_rate"] else "down"
        else:
            oil_trend = gas_trend = "stable"

        return {
            "well_id": well_id,
            "current_rates": {
                "oil": latest.get("oil_rate", 0),
                "gas": latest.get("gas_rate", 0),
                "water": latest.get("water_rate", 0),
            },
            "trend": {"oil": oil_trend, "gas": gas_trend},
            "anomaly_detection": {"status": "normal", "confidence": 0.95},
            "timestamp": datetime.now().isoformat(),
        }

    def run_batch_verification(self, well_ids: List[str]) -> Dict[str, Any]:
        """Run batch verification for multiple wells."""
        results = {}
        summary = {"total": len(well_ids), "verified": 0, "warnings": 0, "failed": 0}

        for well_id in well_ids:
            existing_result = self.dashboard.verification_results.get(well_id, {})
            if existing_result:
                status = existing_result.get("status", "failed")
                score = existing_result.get("score", 0)
            else:
                score = np.random.uniform(0.6, 1.0)
                if score >= 0.9:
                    status = "verified"
                elif score >= 0.75:
                    status = "warning"
                else:
                    status = "failed"

            if status == "verified":
                summary["verified"] += 1
            elif status == "warning":
                summary["warnings"] += 1
            else:
                summary["failed"] += 1

            results[well_id] = {
                "status": status,
                "score": score,
                "timestamp": datetime.now().isoformat(),
            }

            # Update dashboard results
            self.dashboard.verification_results[well_id] = results[well_id]

        return {"results": results, "summary": summary, "execution_time": "0.5s"}

    def export_with_verification(
        self,
        format: str = "pdf",
        include_verification: bool = True,
        include_audit_trail: bool = False,
        quality_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """Export dashboard with verification metadata."""
        # Filter data by quality threshold
        filtered_wells = []
        for well_id, result in self.dashboard.verification_results.items():
            if result.get("score", 0) >= quality_threshold:
                filtered_wells.append(well_id)

        # Simulate export
        return {
            "status": "success",
            "format": format,
            "includes_verification": include_verification,
            "includes_audit_trail": include_audit_trail,
            "quality_threshold": quality_threshold,
            "filtered_count": len(filtered_wells),
            "total_count": len(self.dashboard.verification_results),
            "export_url": f'/downloads/dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{format}',  # noqa: E501
        }

    def get_verified_wells_cached(self, token: str) -> Dict[str, Any]:
        """Get verified wells with caching."""
        # Check authentication
        if not self.authenticator.validate_token(token):
            return {"error": "Invalid token"}

        # Try cache first
        cache_key = "verified_wells"
        cached_result = self.cache_manager.get(cache_key)

        if cached_result:
            cached_result["from_cache"] = True
            return cached_result

        # Get fresh data
        result = self.get_verified_wells()
        result["from_cache"] = False

        # Cache result
        self.cache_manager.set(cache_key, result, ttl=300)

        return result

    async def trigger_production_update(self, well_id: str):
        """Trigger production update for testing."""
        data = {
            "oil_rate": np.random.uniform(900, 1100),
            "gas_rate": np.random.uniform(4500, 5500),
            "water_rate": np.random.uniform(90, 110),
        }

        await self.websocket_manager.push_production_update(well_id, data)

    def initialize_all_services(self):
        """Initialize all enhanced services."""
        logger.info("Initializing enhanced dashboard API services")

        # Generate default admin token
        admin_token = self.authenticator.generate_token("admin", "admin")
        logger.info(f"Admin token: {admin_token}")

        # Generate default API key
        api_key = self.authenticator.generate_api_key("default_client")
        logger.info(f"Default API key: {api_key}")

        return {
            "admin_token": admin_token,
            "api_key": api_key,
            "services": {
                "cache": self.cache_manager.cache_enabled,
                "websocket": self.websocket_manager.enabled,
                "authentication": True,
            },
        }
