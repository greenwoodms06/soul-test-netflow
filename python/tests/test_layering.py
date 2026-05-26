"""Architectural-layering enforcement.

The core (``netflow.core``) must not import from plugins or any
domain-specific library. Plugins must not reach into private names
(``_`` prefixed) of ``netflow.core``.

If this test fails, the load-bearing wall of the design has cracked —
revisit the layering rather than silencing the test.
"""

from __future__ import annotations

import ast
import pathlib

import pytest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE_DIR = PROJECT_ROOT / "netflow" / "core"
THERMAL_DIR = PROJECT_ROOT / "netflow" / "plugins" / "thermal"
HYDRAULIC_DIR = PROJECT_ROOT / "netflow" / "plugins" / "hydraulic"
NEUTRONICS_DIR = PROJECT_ROOT / "netflow" / "plugins" / "neutronics"

# Anything outside this allowlist is a domain or plugin dependency
# that the core must not pull in.
CORE_ALLOWED_IMPORTS = {
    "numpy", "scipy", "logging", "warnings", "time", "math",
    "typing", "dataclasses", "abc", "collections",
    "netflow.core", "netflow.core.node", "netflow.core.edge",
    "netflow.core.network", "netflow.core.assembly",
    "netflow.core.solver", "netflow.core.result",
    "netflow.core.exceptions",
}


def _collect_imports(path: pathlib.Path) -> set[str]:
    """Return the set of top-level module names imported by ``path``."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                names.add(node.module)
    return names


def _iter_python_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.rglob("*.py") if p.name != "__pycache__")


def test_core_has_no_domain_imports():
    """Every import in ``netflow.core`` resolves to allowed infrastructure."""
    offenders: list[tuple[pathlib.Path, str]] = []
    for path in _iter_python_files(CORE_DIR):
        for imported in _collect_imports(path):
            top = imported.split(".")[0]
            # Allow stdlib, numpy/scipy, and intra-core imports.
            if (imported in CORE_ALLOWED_IMPORTS
                    or top in {"numpy", "scipy", "logging", "warnings",
                               "time", "math", "typing", "dataclasses",
                               "abc", "collections", "ast", "__future__"}):
                continue
            if imported.startswith("netflow.core"):
                continue
            offenders.append((path, imported))
    assert not offenders, (
        "netflow.core imports a non-allowed module:\n"
        + "\n".join(f"  {p}: imports {m}" for p, m in offenders)
    )


def test_thermal_plugin_only_imports_core_public_api():
    """The thermal plugin must not reach into private names in netflow.core.

    A 'private name' is any ``from netflow.core.X import _foo`` or
    attribute access ``netflow.core.X._foo``. We allow imports of
    public surfaces (``Node``, ``Edge``, ``Network``, ``Result``,
    ``exceptions``) and of submodules.
    """
    offenders: list[tuple[pathlib.Path, str]] = []
    for path in _iter_python_files(THERMAL_DIR):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("netflow.core"):
                    for alias in node.names:
                        if alias.name.startswith("_"):
                            offenders.append((path, f"{node.module}.{alias.name}"))
    assert not offenders, (
        "thermal plugin imports a private name from netflow.core:\n"
        + "\n".join(f"  {p}: imports {m}" for p, m in offenders)
    )


def test_thermal_plugin_does_not_import_other_plugins():
    """Plugins must be peers; the thermal plugin cannot reach into other plugins."""
    offenders: list[tuple[pathlib.Path, str]] = []
    for path in _iter_python_files(THERMAL_DIR):
        for imported in _collect_imports(path):
            if (imported.startswith("netflow.plugins.")
                    and not imported.startswith("netflow.plugins.thermal")):
                offenders.append((path, imported))
    assert not offenders, (
        "thermal plugin imports another plugin:\n"
        + "\n".join(f"  {p}: imports {m}" for p, m in offenders)
    )


def test_hydraulic_plugin_only_imports_core_public_api():
    """The hydraulic plugin (genericity proof) must not reach into core privates."""
    offenders: list[tuple[pathlib.Path, str]] = []
    for path in _iter_python_files(HYDRAULIC_DIR):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("netflow.core"):
                    for alias in node.names:
                        if alias.name.startswith("_"):
                            offenders.append((path, f"{node.module}.{alias.name}"))
    assert not offenders, (
        "hydraulic plugin imports a private name from netflow.core:\n"
        + "\n".join(f"  {p}: imports {m}" for p, m in offenders)
    )


def test_hydraulic_plugin_does_not_import_other_plugins():
    """The hydraulic plugin must not reach into other plugins (peer isolation)."""
    offenders: list[tuple[pathlib.Path, str]] = []
    for path in _iter_python_files(HYDRAULIC_DIR):
        for imported in _collect_imports(path):
            if (imported.startswith("netflow.plugins.")
                    and not imported.startswith("netflow.plugins.hydraulic")):
                offenders.append((path, imported))
    assert not offenders, (
        "hydraulic plugin imports another plugin:\n"
        + "\n".join(f"  {p}: imports {m}" for p, m in offenders)
    )


def test_neutronics_plugin_isolation():
    """Neutronics plugin: no core privates, no other plugins."""
    offenders: list[tuple[pathlib.Path, str]] = []
    for path in _iter_python_files(NEUTRONICS_DIR):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("netflow.core"):
                    for alias in node.names:
                        if alias.name.startswith("_"):
                            offenders.append((path, f"{node.module}.{alias.name}"))
        for imported in _collect_imports(path):
            if (imported.startswith("netflow.plugins.")
                    and not imported.startswith("netflow.plugins.neutronics")):
                offenders.append((path, imported))
    assert not offenders, (
        "neutronics plugin violates isolation:\n"
        + "\n".join(f"  {p}: imports {m}" for p, m in offenders)
    )
