"""Unit tests for SWIPER-SIM behavioral model manager modules (direct invocation)."""

import numpy as np

from core.decoder_manager import BoundaryPredictor, DecoderManager
from core.device_manager import DeviceManager
from core.schedule import default_three_t_injection, merge_split_example
from core.swiper_sim import SwiperConfig, run_swiper_simulation
from core.window_manager import WindowBuilder, WindowManager, WindowStrategy


def test_window_builder_creates_chains(capsys):
    schedule = default_three_t_injection()
    windows = WindowBuilder(schedule, interval=1).build()
    print(f"built={len(windows)} chains={schedule.parallelism}")
    assert len(windows) == schedule.total_windows()
    assert windows[0].pred_id is None
    assert windows[1].pred_id == 0


def test_device_manager_emits_syndrome(capsys):
    schedule = default_three_t_injection()
    device = DeviceManager(schedule=schedule, seed=42)
    active = device.active_patches_at(0)
    print(f"active={active}")
    assert len(active) == schedule.parallelism
    patch = device.emit_syndrome(
        window_id=1,
        patch_id=1,
        chain_id=1,
        pred_id=0,
        pred_verified=False,
        round_idx=0,
    )
    assert patch.syndrome.shape[0] >= 2
    assert patch.hidden_z.shape[0] == patch.syndrome.shape[0] + 1


def test_boundary_predictor_accuracy(capsys):
    pred = BoundaryPredictor(accuracy=1.0, seed=0)
    rng = np.random.default_rng(0)
    hits = sum(1 for _ in range(20) if pred.should_speculate(rng))
    print(f"hits={hits}")
    assert hits == 20


def test_decoder_manager_tracks_concurrency(capsys):
    dm = DecoderManager(
        processor_count=2,
        decoder_latency_rounds=2,
        speculative=True,
        predictor=BoundaryPredictor(0.9, 0),
    )
    dm.record_concurrency(1)
    dm.record_concurrency(2)
    dm.record_concurrency(1)
    print(f"max={dm.max_concurrent_decoders} avg={dm.average_concurrent_decoders}")
    assert dm.max_concurrent_decoders == 2
    assert dm.average_concurrent_decoders == 4 / 3


def test_aligned_strategy_differs_from_parallel(capsys):
    schedule = default_three_t_injection()
    parallel = run_swiper_simulation(
        schedule,
        SwiperConfig(window_strategy=WindowStrategy.PARALLEL.value, seed=42),
    )["metrics"]
    aligned = run_swiper_simulation(
        schedule,
        SwiperConfig(window_strategy=WindowStrategy.ALIGNED.value, seed=42),
    )["metrics"]
    print(
        f"parallel_time={parallel['total_decoding_time_us']} "
        f"aligned_time={aligned['total_decoding_time_us']}"
    )
    assert parallel["total_decoding_time_us"] != aligned["total_decoding_time_us"] or (
        parallel["average_window_backlog"] != aligned["average_window_backlog"]
    )


def test_merge_split_schedule_completes(capsys):
    schedule = merge_split_example()
    run = run_swiper_simulation(schedule, SwiperConfig(seed=7))
    m = run["metrics"]
    print(f"completed={run['completed']} max_dec={m['max_concurrent_decoders']}")
    assert run["completed"] is True
    assert m["max_concurrent_decoders"] >= 0


def test_window_manager_adjacent_dependents(capsys):
    schedule = default_three_t_injection()
    wm = WindowManager(schedule=schedule, strategy="parallel", interval=1)
    child = wm.windows[1]
    child.appeared = True
    child.state = "ready"
    child.speculated = True
    dep = wm.adjacent_dependents(0)
    print(f"deps={len(dep)}")
    assert len(dep) >= 1
    assert all(w.pred_id == 0 for w in dep)


def test_emit_trace_populated(capsys):
    run = run_swiper_simulation(
        default_three_t_injection(),
        SwiperConfig(emit_trace=True, seed=1),
    )
    print(f"trace_len={len(run.get('program_trace', []))}")
    assert "program_trace" in run
    assert len(run["program_trace"]) > 0