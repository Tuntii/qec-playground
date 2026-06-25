"""Lattice surgery program and schedule representation (SWIPER-SIM behavioral model).

Schedules describe parallel T-gate injection chains, patch merge/split, and blocking
Conditional-S instructions as used in Li & Martonosi (arXiv:2606.24048) experiments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

SCHEDULES_DIR = Path(__file__).resolve().parent.parent / "examples"


class PatchOpType(str, Enum):
    T_INJECTION = "t_injection"
    MERGE = "merge"
    SPLIT = "split"
    CONDITIONAL_S = "conditional_s"


@dataclass(frozen=True)
class LatticePatch:
    """Active surface-code patch participating in lattice surgery."""

    patch_id: int
    chain_id: int
    label: str = ""


@dataclass(frozen=True)
class ProgramOp:
    """Single lattice-surgery instruction at a QEC round."""

    op_type: PatchOpType
    round: int
    patch_ids: tuple[int, ...]
    blocks_until_window_index: int | None = None
    target_patch_id: int | None = None


@dataclass(frozen=True)
class LatticeSurgeryProgram:
    """Round-level lattice surgery program: patches + spatial/temporal ops."""

    patches: tuple[LatticePatch, ...]
    ops: tuple[ProgramOp, ...]

    def patch_by_id(self, patch_id: int) -> LatticePatch:
        for patch in self.patches:
            if patch.patch_id == patch_id:
                return patch
        raise KeyError(f"Unknown patch id: {patch_id}")

    def ops_at_round(self, round_idx: int) -> tuple[ProgramOp, ...]:
        return tuple(op for op in self.ops if op.round == round_idx)

    def blocking_ops(self) -> tuple[ProgramOp, ...]:
        return tuple(op for op in self.ops if op.op_type == PatchOpType.CONDITIONAL_S)


@dataclass(frozen=True)
class LatticeSurgerySchedule:
    """Lattice surgery workload with optional rich program model."""

    id: str
    name: str
    description: str
    parallelism: int
    windows_per_chain: int
    blocking_window_index: int
    source: str = "template"
    program: LatticeSurgeryProgram | None = None
    slide_stride_rounds: int = 1

    def total_windows(self) -> int:
        return self.parallelism * self.windows_per_chain

    def has_program(self) -> bool:
        return self.program is not None and len(self.program.patches) > 0


def _program_from_dict(data: dict[str, Any]) -> LatticeSurgeryProgram | None:
    if "patches" not in data and "ops" not in data:
        return None
    patches = tuple(
        LatticePatch(
            patch_id=int(p["id"]),
            chain_id=int(p.get("chain", p["id"])),
            label=str(p.get("label", "")),
        )
        for p in data.get("patches", [])
    )
    ops: list[ProgramOp] = []
    for raw in data.get("ops", []):
        op_type = PatchOpType(str(raw["type"]))
        patch_ids = tuple(int(x) for x in raw.get("patches", raw.get("patch_ids", [])))
        if not patch_ids and "patch" in raw:
            patch_ids = (int(raw["patch"]),)
        ops.append(
            ProgramOp(
                op_type=op_type,
                round=int(raw["round"]),
                patch_ids=patch_ids,
                blocks_until_window_index=(
                    int(raw["blocks_until_window_index"])
                    if raw.get("blocks_until_window_index") is not None
                    else None
                ),
                target_patch_id=int(raw["into"]) if raw.get("into") is not None else None,
            )
        )
    return LatticeSurgeryProgram(patches=patches, ops=tuple(ops))


def default_three_t_injection() -> LatticeSurgerySchedule:
    """Paper default: three parallel T-gate injection circuits."""
    program = LatticeSurgeryProgram(
        patches=tuple(
            LatticePatch(patch_id=c, chain_id=c, label=f"T-chain-{c}")
            for c in range(3)
        ),
        ops=tuple(
            ProgramOp(
                op_type=PatchOpType.T_INJECTION,
                round=0,
                patch_ids=(c,),
            )
            for c in range(3)
        )
        + tuple(
            ProgramOp(
                op_type=PatchOpType.CONDITIONAL_S,
                round=5 * 1,
                patch_ids=(c,),
                blocks_until_window_index=4,
            )
            for c in range(3)
        ),
    )
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
        program=program,
    )


def merge_split_example() -> LatticeSurgerySchedule:
    """Two chains merge mid-program, then split; blocking Conditional-S on merged patch."""
    program = LatticeSurgeryProgram(
        patches=(
            LatticePatch(0, 0, "left"),
            LatticePatch(1, 1, "right"),
            LatticePatch(2, 0, "merged"),
        ),
        ops=(
            ProgramOp(PatchOpType.T_INJECTION, 0, (0,)),
            ProgramOp(PatchOpType.T_INJECTION, 0, (1,)),
            ProgramOp(PatchOpType.MERGE, 12, (0, 1), target_patch_id=2),
            ProgramOp(
                PatchOpType.CONDITIONAL_S,
                18,
                (2,),
                blocks_until_window_index=6,
            ),
            ProgramOp(PatchOpType.SPLIT, 28, (2,), target_patch_id=0),
        ),
    )
    return LatticeSurgerySchedule(
        id="merge_split_t",
        name="Merge / split T injection",
        description=(
            "Representative merge-split lattice surgery: two T injections merge, "
            "blocking Conditional-S on merged patch, then split."
        ),
        parallelism=2,
        windows_per_chain=12,
        blocking_window_index=7,
        program=program,
        slide_stride_rounds=2,
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
    if schedule_id == "merge_split_t":
        return merge_split_example()
    raise KeyError(f"Unknown schedule id: {schedule_id}")


def schedule_from_dict(data: dict[str, Any], source: str = "template") -> LatticeSurgerySchedule:
    program = _program_from_dict(data)
    if "parallelism" in data:
        return LatticeSurgerySchedule(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            parallelism=int(data["parallelism"]),
            windows_per_chain=int(data["windows_per_chain"]),
            blocking_window_index=int(data["blocking_window_index"]),
            source=source,
            program=program,
            slide_stride_rounds=int(data.get("slide_stride_rounds", 1)),
        )
    return LatticeSurgerySchedule(
        id=str(data["id"]),
        name=str(data["name"]),
        description=str(data.get("description", "Legacy template mapped to lattice schedule")),
        parallelism=1,
        windows_per_chain=max(6, int(data.get("window_size", 4)) + 4),
        blocking_window_index=max(3, int(data.get("window_size", 4))),
        source=source,
        program=program,
    )