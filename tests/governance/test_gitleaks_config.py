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

    def assert_no_regex_allowances(self, config):
        def visit(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {"allowlist", "allowlists"}:
                        allowances = value if isinstance(value, list) else [value]
                        for allowance in allowances:
                            self.assertFalse(allowance.get("regexes"))
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(config)

    def test_no_regex_allowances(self):
        config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
        self.assert_no_regex_allowances(config)

    def test_regex_allowances_are_rejected(self):
        allowance = {"regexes": ["forbidden"]}
        for config in (
            {"allowlist": allowance},
            {"allowlists": [allowance]},
            {"rules": [{"allowlist": allowance}]},
            {"rules": [{"allowlists": [allowance]}]},
        ):
            with self.subTest(config=config), self.assertRaises(AssertionError):
                self.assert_no_regex_allowances(config)

    def assert_fingerprints(self, text):
        previous = ""
        pattern = re.compile(
            r"(?:(?P<commit>[0-9a-f]{40}):)?"
            r"(?P<path>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*):"
            r"(?P<rule>[a-z][a-z0-9-]*):(?P<line>[1-9][0-9]*)"
        )
        count = 0
        for line in text.splitlines():
            if line and not line.startswith("#"):
                match = pattern.fullmatch(line)
                self.assertIsNotNone(match, "Invalid fingerprint format")
                fields = match.groupdict()
                self.assertNotIn("..", fields["path"].split("/"))
                comment = re.fullmatch(
                    r"# ([a-z][a-z0-9-]*)  (.+):([1-9][0-9]*)  "
                    r"(synthetic-fixture|placeholder|not-a-secret)",
                    previous,
                )
                self.assertIsNotNone(comment, "Missing classification comment")
                self.assertEqual(
                    comment.groups()[:3],
                    (fields["rule"], fields["path"], fields["line"]),
                )
                count += 1
            previous = line
        self.assertGreater(count, 0, "Fingerprint file must not be empty")

    def test_ignore_entries_are_classified_fingerprints(self):
        self.assert_fingerprints((ROOT / ".gitleaksignore").read_text(encoding="utf-8"))

    def test_invalid_fingerprints_are_rejected(self):
        comment = "# generic-api-key  tests/unit/check.py:12  synthetic-fixture\n"
        fingerprint = "tests/unit/check.py:generic-api-key:12"
        invalid = (
            fingerprint,
            comment + fingerprint + " extra",
            comment + fingerprint + ":unexpected",
            comment.replace("synthetic-fixture", "looks-real") + fingerprint,
            comment.replace(":12", ":13") + fingerprint,
            comment + "\n" + fingerprint,
            comment + fingerprint.replace(":12", ":0"),
            comment + "a" * 500,
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(AssertionError):
                self.assert_fingerprints(text)

    def test_history_fingerprint_format_is_supported(self):
        comment = "# generic-api-key  tests/unit/check.py:12  placeholder\n"
        self.assert_fingerprints(
            comment + "a" * 40 + ":tests/unit/check.py:generic-api-key:12"
        )
