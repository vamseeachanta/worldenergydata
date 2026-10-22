"""AST audit of both Landman error hierarchies and their constructor call sites.

The oracle is inspect.signature on each actual constructor, including inherited
constructors. Issue #1255 (2026) documents why exceptions.LandmanError accepts
error_code/details while errors.LandmanError accepts code/context. No numerical
model, tolerance, or external benchmark is involved.
"""

import ast
import importlib
import inspect
from pathlib import Path

import pytest

from worldenergydata.landman import errors, exceptions


def incompatible_keywords(source, namespace):
    """Resolve direct, aliased, qualified and class-factory constructor calls."""
    failures = []

    class Visitor(ast.NodeVisitor):
        current_class = None

        def resolve(self, node):
            if isinstance(node, ast.Name):
                return (
                    self.current_class if node.id == "cls" else namespace.get(node.id)
                )
            if isinstance(node, ast.Attribute):
                parent = self.resolve(node.value)
                return getattr(parent, node.attr, None) if parent is not None else None
            return None

        def visit_ClassDef(self, node):
            previous = self.current_class
            self.current_class = namespace.get(node.name)
            self.generic_visit(node)
            self.current_class = previous

        def visit_Call(self, node):
            target = self.resolve(node.func)
            if inspect.isclass(target) and issubclass(
                target, (exceptions.LandmanError, errors.LandmanError)
            ):
                signature = inspect.signature(target)
                accepts_extra = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in signature.parameters.values()
                )
                accepted = {
                    name
                    for name, p in signature.parameters.items()
                    if p.kind
                    in {
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY,
                    }
                }
                for keyword in node.keywords:
                    # No dynamic keyword dictionaries occur in current source;
                    # require an explicit audit if a future call introduces one.
                    if keyword.arg is None or (
                        not accepts_extra and keyword.arg not in accepted
                    ):
                        failures.append((node.lineno, target.__name__, keyword.arg))
            self.generic_visit(node)

    Visitor().visit(ast.parse(source))
    return failures


PACKAGE = Path(exceptions.__file__).parent
SOURCES = sorted(PACKAGE.rglob("*.py"))


@pytest.mark.parametrize(
    "path", SOURCES, ids=lambda path: str(path.relative_to(PACKAGE))
)
def test_all_landman_error_constructions_accept_their_keywords(path):
    """Audit all source files, including aliases whose names lack 'Landman'."""
    relative = path.relative_to(PACKAGE).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    module = importlib.import_module(".".join(("worldenergydata", "landman", *parts)))
    assert incompatible_keywords(path.read_text(), vars(module)) == []


@pytest.mark.parametrize("keyword", ["code", "context"])
@pytest.mark.parametrize(
    "callee", ["LandmanError", "Alias", "exceptions.LandmanError", "cls"]
)
def test_audit_detects_original_keyword_mismatch(keyword, callee):
    """The historical #1255 keywords must fail for direct and factory calls."""
    namespace = {
        "LandmanError": exceptions.LandmanError,
        "Alias": exceptions.ProviderError,
        "exceptions": exceptions,
    }
    source = f"{callee}('synthetic', {keyword}=None)"
    if callee == "cls":
        namespace["InheritedError"] = type(
            "InheritedError", (exceptions.LandmanError,), {}
        )
        source = (
            f"class InheritedError:\n    def factory(cls):\n        return {source}"
        )
    failures = incompatible_keywords(source, namespace)
    assert [failure[-1] for failure in failures] == [keyword]


def test_audit_distinguishes_legacy_constructor_contract():
    """code/context are valid for the separate errors.py hierarchy."""
    assert (
        incompatible_keywords(
            "LegacyError('synthetic', code='SYNTHETIC', context={})",
            {"LegacyError": errors.LandmanError},
        )
        == []
    )
