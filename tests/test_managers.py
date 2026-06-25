"""Unit tests for SWIPER-SIM behavioral model manager modules (direct invocation)."""

import numpy as np

from core.decoder_manager import BoundaryPredictor, DecoderManager
from core.device_manager import DeviceManager
from core.schedule import default_three_t_injection, merge_split_example
from core.swiper_sim import SwiperConfig, run_swiper_simulation
from core.syndrome_graph import true_predecessor_logical
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


def test_active_patches_remap_after_merge_round(capsys):
    schedule = merge_split_example()
    device = DeviceManager(schedule=schedule, seed=0)
    before = {chain: pid for pid, chain in device.active_patches_at(11)}
    after = {chain: pid for pid, chain in device.active_patches_at(12)}
    print(f"before={before} after={after}")
    assert before.get(0) == 0
    assert before.get(1) == 1
    assert after.get(0) == 2
    assert after.get(1) == 2


def test_boundary_predictor_tracks_accuracy(capsys):
    pred = BoundaryPredictor(accuracy=1.0, seed=0)
    rng = np.random.default_rng(99)
    true_val = 1
    hits = sum(1 for _ in range(50) if pred.predict_boundary(true_val, rng) == true_val)
    print(f"hits={hits}")
    assert hits == 50
    pred_lo = BoundaryPredictor(accuracy=0.0, seed=0)
    rng2 = np.random.default_rng(99)
    misses = sum(1 for _ in range(50) if pred_lo.predict_boundary(0, rng2) != 0)
    assert misses == 50


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


def test_merge_split_blocking_increases_nonspec_runtime(capsys):
    schedule = merge_split_example()
    spec = run_swiper_simulation(schedule, SwiperConfig(speculative=True, seed=7))["metrics"]
    nonspec = run_swiper_simulation(schedule, SwiperConfig(speculative=False, seed=7))["metrics"]
    device = DeviceManager(schedule=schedule, seed=7)
    device.sync_window_patches(WindowBuilder(schedule, 1).build(), 12)
    merged_patch = device.patch_id_for_chain(12, 0)
    print(
        f"merged_patch={merged_patch} spec_time={spec['total_decoding_time_us']} "
        f"nonspec_time={nonspec['total_decoding_time_us']} nonspec_wait={nonspec['average_conditional_wait_time_us']}"
    )
    assert merged_patch == 2
    assert nonspec["average_conditional_wait_time_us"] > 0.0
    assert spec["total_decoding_time_us"] <= nonspec["total_decoding_time_us"]


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
    assert "active_patches" in run["program_trace"][0]


def test_conditional_wait_not_double_counted(capsys):
    """Each blocked stall round counted exactly once (not batch + per-round)."""
    schedule = default_three_t_injection()
    device = DeviceManager(schedule=schedule, seed=0)
    chain = device.chains[0]
    block_idx = schedule.blocking_window_index
    dep_idx = block_idx - 1

    for round_idx in range(5, 10):
        chain.blocked = True
        chain.block_start = 5
        device.account_conditional_stalls(
            [],
            round_idx,
            speculative=False,
            window_verified={(0, dep_idx): False},
        )

    device.update_blocking(
        10,
        window_appeared={(0, block_idx): True},
        window_verified={(0, dep_idx): True},
    )
    device.account_conditional_stalls(
        [],
        10,
        speculative=False,
        window_verified={(0, dep_idx): True},
    )
    print(f"cond_wait={chain.cond_wait_rounds}")
    assert chain.cond_wait_rounds == 5


def test_blocking_stalls_nonspec_appearance(capsys):
    schedule = default_three_t_injection()
    device = DeviceManager(schedule=schedule, seed=42)
    wm = WindowManager(schedule=schedule, strategy="parallel", interval=1)
    w = next(x for x in wm.windows if x.index_in_chain == schedule.blocking_window_index)
    allowed = device.appearance_allowed(
        w,
        w.gen_round,
        speculative=False,
        window_verified={},
    )
    print(f"allowed_without_dep={allowed}")
    assert allowed is False