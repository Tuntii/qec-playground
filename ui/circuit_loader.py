"""Circuit template loading and minimal QASM parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@dataclass(frozen=True)
class CircuitTemplate:
    id: str
    name: str
    description: str
    surface_distance: int
    window_size: int
    default_squeezing_db: float
    default_noise_p: float
    qasm: str
    source: str = "template"


def list_templates() -> list[CircuitTemplate]:
    """Load all built-in JSON circuit templates from examples/."""
    templates: list[CircuitTemplate] = []
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        templates.append(load_template_file(path))
    return templates


def load_template_file(path: Path) -> CircuitTemplate:
    """Load a single template JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return _template_from_dict(data, source=str(path.name))


def load_template_by_id(template_id: str) -> CircuitTemplate:
    """Load a template by its id field."""
    for template in list_templates():
        if template.id == template_id:
            return template
    raise KeyError(f"Unknown template id: {template_id}")


def parse_qasm(qasm_text: str) -> CircuitTemplate:
    """
    Parse minimal metadata from OpenQASM 2.0 text.

    Extracts qubit register size to infer surface distance and window size.
    """
    if not qasm_text.strip():
        raise ValueError("QASM text is empty")

    qreg_match = re.search(r"qreg\s+(\w+)\s*\[(\d+)\]", qasm_text)
    num_qubits = int(qreg_match.group(2)) if qreg_match else 5
    surface_distance = max(3, min(7, int(num_qubits**0.5) | 1))
    window_size = max(3, min(8, surface_distance))

    return CircuitTemplate(
        id="qasm_import",
        name="Imported QASM circuit",
        description="User-provided OpenQASM 2.0 circuit",
        surface_distance=surface_distance,
        window_size=window_size,
        default_squeezing_db=10.0,
        default_noise_p=0.02,
        qasm=qasm_text,
        source="qasm",
    )


def _template_from_dict(data: dict[str, Any], source: str) -> CircuitTemplate:
    required = (
        "id",
        "name",
        "description",
        "surface_distance",
        "window_size",
        "default_squeezing_db",
        "default_noise_p",
        "qasm",
    )
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Template missing keys: {missing}")

    return CircuitTemplate(
        id=str(data["id"]),
        name=str(data["name"]),
        description=str(data["description"]),
        surface_distance=int(data["surface_distance"]),
        window_size=int(data["window_size"]),
        default_squeezing_db=float(data["default_squeezing_db"]),
        default_noise_p=float(data["default_noise_p"]),
        qasm=str(data["qasm"]),
        source=source,
    )