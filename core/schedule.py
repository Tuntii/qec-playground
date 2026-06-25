"""Lattice surgery schedule representation for Li & Martonosi (arXiv:2606.24048).

Schedules model parallel T-gate injection chains with blocking Conditional-S
rounds as described in the paper's SWIPER-SIM-style experiments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEDULES_DIR = Path(__file__).resolve().parent.parent / "examples"


@dataclass(frozen=True)
class LatticeSurgerySchedule:
    """Parallel T-gate injection chains with a blocking conditional round."""

    id: str
    name: str
    description: str
    parallelism: int
    windows_per_chain: int
    blocking_window_index: int
    source: str = "template"

    def total_windows(self) -> int:
        return self.parallelism * self.windows_per_chain


def default_three_t_injection() -> LatticeSurgerySchedule:
    """Paper default: three parallel T-gate injection circuits."""
    return LatticeSurgerySchedule(
        id="three_t_injection",
        name="Three parallel T-gate injections",
        description=(
            "Default lattice surgery workload from Li & Martonosi (arXiv:2606.24048): "
            "three T-gate injection circuits on separate logical qubits with blocking "
            "Conditional-S instructions."
        ),
        parallelism=3,
        windows_per_chain=10,
        blocking_window_index=5,
    )


def list_schedules() -> list[LatticeSurgerySchedule]:
    schedules: list[LatticeSurgerySchedule] = []
    for path in sorted(SCHEDULES_DIR.glob("*.json")):
        schedules.append(load_schedule_file(path))
    return schedules


def load_schedule_file(path: Path) -> LatticeSurgerySchedule:
    data = json.loads(path.read_text(encoding="utf-8"))
    return schedule_from_dict(data, source=path.name)


def load_schedule_by_id(schedule_id: str) -> LatticeSurgerySchedule:
    for schedule in list_schedules():
        if schedule.id == schedule_id:
            return schedule
    raise KeyError(f"Unknown schedule id: {schedule_id}")


def schedule_from_dict(data: dict[str, Any], source: str = "template") -> LatticeSurgerySchedule:
    if "parallelism" in data:
        return LatticeSurgerySchedule(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            parallelism=int(data["parallelism"]),
            windows_per_chain=int(data["windows_per_chain"]),
            blocking_window_index=int(data["blocking_window_index"]),
            source=source,
        )
    # Legacy GKP template JSON — map to a single-chain schedule.
    return LatticeSurgerySchedule(
        id=str(data["id"]),
        name=str(data["name"]),
        description=str(data.get("description", "Legacy template mapped to lattice schedule")),
        parallelism=1,
        windows_per_chain=max(6, int(data.get("window_size", 4)) + 4),
        blocking_window_index=max(3, int(data.get("window_size", 4))),
        source=source,
    )