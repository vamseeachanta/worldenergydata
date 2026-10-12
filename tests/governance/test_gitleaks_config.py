"""Regression contract for the standalone secret-scanner configuration."""

import re
import unittest
from pathlib import Path

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 uses pytest's TOML parser dependency.
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[2]


class GitleaksConfigContract(unittest.TestCase):
    def test_default_detection_rules_are_loaded(self):
        config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
        self.assertIs(config["extend"]["useDefault"], True)

    def test_hook_uses_repo_local_config(self):
        config = yaml.safe_load(
            (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        )
        repo = next(
            repo
            for repo in config["repos"]
            if any(hook["id"] == "gitleaks" for hook in repo["hooks"])
        )
        hook = next(hook for hook in repo["hooks"] if hook["id"] == "gitleaks")
        self.assertEqual(hook["args"], ["--config", ".gitleaks.toml"])
        self.assertFalse(hook["args"][1].startswith("../"))
        self.assertEqual(repo["rev"], "v8.21.2")

    def assert_path_anchors(self, paths):
        own_paths = [
            pattern for pattern in paths if re.search(pattern, ".gitleaks.toml")
        ]
        self.assertEqual(len(own_paths), 1)
        self.assertTrue(own_paths[0].endswith("$"))
        for pattern in paths:
            self.assertTrue(pattern.startswith("^"), "Path allowance must start with ^")

    def test_path_allowances_are_anchored(self):
        config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
        self.assert_path_anchors(config["allowlist"]["paths"])

    def test_unanchored_paths_are_rejected(self):
        invalid_paths = (
            [r"\.gitleaks\.toml$"],
            [r"^\.gitleaks\.toml"],
            [r"^\.gitleaks\.toml$", "tests/"],
        )
        for paths in invalid_paths:
            with self.subTest(paths=paths), self.assertRaises(AssertionError):
                self.assert_path_anchors(paths)
