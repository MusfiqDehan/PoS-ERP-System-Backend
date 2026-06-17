from pathlib import Path
import re

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = [BACKEND_ROOT / "shared", BACKEND_ROOT / "config", BACKEND_ROOT / "apps"]

FORBIDDEN_UTILS_IMPORT = re.compile(r"^\s*(from utils\.|import utils\b)")


def _project_python_files():
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if path.name == "test_no_utils_imports.py":
                continue
            yield path


@pytest.mark.parametrize(
    "path",
    list(_project_python_files()),
    ids=lambda p: str(p.relative_to(BACKEND_ROOT)),
)
def test_no_project_utils_imports(path: Path):
    violations = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.strip().startswith("#"):
            continue
        if FORBIDDEN_UTILS_IMPORT.match(line):
            violations.append(
                f"{path.relative_to(BACKEND_ROOT)}:{line_no}: {line.strip()}"
            )

    assert not violations, "Forbidden utils imports found:\n" + "\n".join(violations)


def test_utils_package_does_not_exist():
    assert not (BACKEND_ROOT / "utils").exists()
