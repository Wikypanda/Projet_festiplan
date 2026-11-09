"""Vérifie la règle de dépendance de l'architecture hexagonale :
le domaine et l'application n'importent aucune technologie, ni les adaptateurs."""
import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
FORBIDDEN = ("fastapi", "sqlalchemy", "pydantic", "app.adapters", "app.bootstrap", "app.config")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("path", sorted((APP / "domain").rglob("*.py")) + sorted((APP / "application").rglob("*.py")),
                         ids=lambda p: str(p.relative_to(APP)))
def test_core_does_not_depend_on_technical_details(path):
    bad = {m for m in imported_modules(path) if m.startswith(FORBIDDEN)}
    assert not bad, f"{path.name} importe {bad}"


@pytest.mark.parametrize("path", sorted((APP / "domain").rglob("*.py")), ids=lambda p: str(p.relative_to(APP)))
def test_domain_does_not_depend_on_application(path):
    assert not {m for m in imported_modules(path) if m.startswith("app.application")}
