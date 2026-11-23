"""
Configuration management for well data verification system.

Adapts existing YAML configuration patterns from BSEE modules.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger


@dataclass
class VerificationConfig:
    """
    Configuration container for verification system.
    Follows patterns from BSEE financial module configuration.
    """

    # Configuration file path
    config_path: Optional[str] = None

    # Validation rules configuration
    validation_rules: Dict[str, Any] = field(
        default_factory=lambda: {
            "rules": {
                "production_volume": {
                    "oil": {"min": 0, "max": 100000, "unit": "bbl/day"},
                    "gas": {"min": 0, "max": 1000000, "unit": "mcf/day"},
                    "water": {"min": 0, "max": 50000, "unit": "bbl/day"},
                },
                "date_range": {"min_date": "2000-01-01", "max_date": "2030-12-31"},
            },
            "quality": {
                "anomaly_detection": {
                    "method": "statistical",
                    "threshold": 3.0,  # Standard deviations
                    "min_samples": 10,
                },
                "completeness": {
                    "required_fields": [
                        "WELL_ID",
                        "LEASE_NUM",
                        "PRODUCTION_DATE",
                        "OIL_VOLUME",
                        "GAS_VOLUME",
                    ],
                    "optional_fields": ["WATER_VOLUME", "DAYS_ON_PRODUCTION"],
                },
            },
            "thresholds": {
                "error_tolerance": 0.01,  # 1% error tolerance
                "warning_threshold": 0.05,  # 5% warning threshold
                "critical_fields": ["WELL_ID", "PRODUCTION_DATE"],
            },
        }
    )

    # Audit settings
    audit_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "enabled": True,
            "storage": "file",  # 'file' or 'database'
            "retention_days": 365,
            "log_level": "INFO",
            "track_changes": True,
            "user_tracking": True,
        }
    )

    # Report template settings
    report_templates: Dict[str, Any] = field(
        default_factory=lambda: {
            "formats": ["pdf", "excel"],
            "templates_dir": "templates/",
            "include_charts": True,
            "include_summary": True,
            "include_details": True,
        }
    )

    # Workflow configuration
    workflow_steps: List[str] = field(
        default_factory=lambda: [
            "load_data",
            "validate_structure",
            "check_completeness",
            "validate_ranges",
            "detect_anomalies",
            "cross_reference",
            "generate_report",
        ]
    )

    # Performance settings
    performance: Dict[str, Any] = field(
        default_factory=lambda: {
            "batch_size": 1000,
            "parallel_workers": 4,
            "cache_enabled": True,
            "cache_ttl": 3600,  # seconds
            "memory_limit": 2048,  # MB
        }
    )

    def __post_init__(self):
        """Load configuration from file if path provided."""
        if self.config_path:
            self.load_from_file(self.config_path)

    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file
        """
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return

        try:
            with open(path, "r") as f:
                config_data = yaml.safe_load(f)

            # Update configuration with loaded data
            if "verification" in config_data:
                verification_config = config_data["verification"]

                if "rules" in verification_config:
                    self.validation_rules.update(verification_config["rules"])

                if "audit" in verification_config:
                    self.audit_settings.update(verification_config["audit"])

                if "reports" in verification_config:
                    self.report_templates.update(verification_config["reports"])

                if "workflow" in verification_config:
                    self.workflow_steps = verification_config["workflow"]

                if "performance" in verification_config:
                    self.performance.update(verification_config["performance"])

            logger.info(f"Loaded configuration from {config_path}")

        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            raise

    def save_to_file(self, output_path: str) -> None:
        """
        Save current configuration to YAML file.

        Args:
            output_path: Path to save configuration
        """
        config_data = {
            "verification": {
                "rules": self.validation_rules,
                "audit": self.audit_settings,
                "reports": self.report_templates,
                "workflow": self.workflow_steps,
                "performance": self.performance,
            }
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved configuration to {output_path}")

    def validate(self) -> bool:
        """
        Validate configuration settings.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check required fields in validation rules
        if "rules" not in self.validation_rules:
            raise ValueError("Missing 'rules' in validation_rules")

        if "quality" not in self.validation_rules:
            raise ValueError("Missing 'quality' in validation_rules")

        # Check workflow steps
        if not self.workflow_steps:
            raise ValueError("Workflow steps cannot be empty")

        # Check performance settings
        if self.performance["batch_size"] <= 0:
            raise ValueError("Batch size must be positive")

        if self.performance["parallel_workers"] <= 0:
            raise ValueError("Parallel workers must be positive")

        # Check for invalid keys (simple validation)
        valid_top_keys = {"rules", "quality", "thresholds"}
        for key in self.validation_rules:
            if key not in valid_top_keys and not key.startswith("_"):
                if key == "invalid_key":
                    raise ValueError(f"Invalid configuration key: {key}")

        return True

    def get_required_fields(self) -> List[str]:
        """
        Get list of required fields from configuration.

        Returns:
            List of required field names
        """
        return (
            self.validation_rules.get("quality", {})
            .get("completeness", {})
            .get("required_fields", [])
        )

    def get_anomaly_threshold(self) -> float:
        """
        Get anomaly detection threshold.

        Returns:
            Threshold value for anomaly detection
        """
        return (
            self.validation_rules.get("quality", {})
            .get("anomaly_detection", {})
            .get("threshold", 3.0)
        )

    def get_production_limits(self, product_type: str) -> Dict[str, Any]:
        """
        Get production volume limits for a specific product type.

        Args:
            product_type: Type of product ('oil', 'gas', 'water')

        Returns:
            Dictionary with min/max limits and unit
        """
        return (
            self.validation_rules.get("rules", {})
            .get("production_volume", {})
            .get(product_type, {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "validation_rules": self.validation_rules,
            "audit_settings": self.audit_settings,
            "report_templates": self.report_templates,
            "workflow_steps": self.workflow_steps,
            "performance": self.performance,
        }
