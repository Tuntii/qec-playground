"""Lattice surgery schedule template loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.schedule import LatticeSurgerySchedule, schedule_from_dict

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@dataclass(frozen=True)
class ScheduleTemplate:
    schedule: LatticeSurgerySchedule
    default_processor_count: int = 4
    default_cycle_time_us: float = 1.0
    default_speculation_accuracy: float = 0.9
    default_decoder_latency_rounds: int = 2
    default_ordering_strategy: str = "shallow_first"
    default_window_strategy: str = "parallel"

    @property
    def id(self) -> str:
        return self.schedule.id

    @property
    def name(self) -> str:
        return self.schedule.name

    @property
    def description(self) -> str:
        return self.schedule.description


def list_templates() -> list[ScheduleTemplate]:
    templates: list[ScheduleTemplate] = []
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        templates.append(load_template_file(path))
    return templates


def load_template_file(path: Path) -> ScheduleTemplate:
    data = json.loads(path.read_text(encoding="utf-8"))
    schedule = schedule_from_dict(data, source=path.name)
    return ScheduleTemplate(
        schedule=schedule,
        default_processor_count=int(data.get("default_processor_count", 4)),
        default_cycle_time_us=float(data.get("default_cycle_time_us", 1.0)),
        default_speculation_accuracy=float(data.get("default_speculation_accuracy", 0.9)),
        default_decoder_latency_rounds=int(data.get("default_decoder_latency_rounds", 2)),
        default_ordering_strategy=str(data.get("default_ordering_strategy", "shallow_first")),
        default_window_strategy=str(data.get("default_window_strategy", "parallel")),
    )


def load_template_by_id(template_id: str) -> ScheduleTemplate:
    for template in list_templates():
        if template.id == template_id:
            return template
    raise KeyError(f"Unknown schedule template id: {template_id}")