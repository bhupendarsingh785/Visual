"""Bounded optional PyTorch profiler utility for VISUAL."""
from __future__ import annotations

from pathlib import Path


def profile_callable(run_steps, *, trace_dir, wait=1, warmup=1, active=3,
                     repeat=1, record_shapes=True, profile_memory=True,
                     with_stack=False):
    """Profile a zero-argument step callback; callback must call profiler.step().

    Returns a compact summary and Chrome trace paths. Profiling is opt-in and
    must be run separately from benchmark comparisons because it adds overhead.
    """
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is required for profiling") from exc
    for name, value in (("wait", wait), ("warmup", warmup), ("active", active),
                        ("repeat", repeat)):
        if int(value) < 0 or (name in {"active", "repeat"} and int(value) < 1):
            raise ValueError(f"invalid profiler {name}")
    root = Path(trace_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    activities = [torch.profiler.ProfilerActivity.CPU]
    if torch.cuda.is_available():
        activities.append(torch.profiler.ProfilerActivity.CUDA)
    traces = []

    def handler(prof):
        path = root / f"visual-trace-{len(traces)+1}.json"
        prof.export_chrome_trace(str(path))
        traces.append(str(path))

    schedule = torch.profiler.schedule(wait=int(wait), warmup=int(warmup),
                                       active=int(active), repeat=int(repeat))
    with torch.profiler.profile(
        activities=activities, schedule=schedule, on_trace_ready=handler,
        record_shapes=bool(record_shapes), profile_memory=bool(profile_memory),
        with_stack=bool(with_stack)
    ) as prof:
        for _ in range(int(wait + warmup + active) * int(repeat)):
            run_steps()
            prof.step()
    summary = prof.key_averages().table(sort_by="self_cpu_time_total", row_limit=30)
    return {"status": "completed", "trace_files": traces,
            "activities": [str(x).split(".")[-1] for x in activities],
            "summary": summary, "note": "Profiler overhead makes this unsuitable as an unprofiled performance benchmark."}
