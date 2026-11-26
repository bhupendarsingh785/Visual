"""Reproducible, bounded PyTorch inference benchmark utility."""
import statistics
import time


def benchmark_torch_callable(fn, *, warmup=5, iterations=30, synchronize=None):
    """Benchmark a caller-provided callable; no model or data is downloaded."""
    warmup = int(warmup)
    iterations = int(iterations)
    if not 0 <= warmup <= 1000:
        raise ValueError("warmup must be in [0, 1000]")
    if not 1 <= iterations <= 10000:
        raise ValueError("iterations must be in [1, 10000]")
    sync = synchronize or (lambda: None)
    for _ in range(warmup):
        fn()
    sync()
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        sync()
        samples.append((time.perf_counter() - start) * 1000.0)
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered)) - 1))
    return {
        "iterations": iterations,
        "warmup": warmup,
        "median_latency_ms": statistics.median(samples),
        "p95_latency_ms": ordered[p95_index],
        "min_latency_ms": min(samples),
        "max_latency_ms": max(samples),
        "throughput_per_second": 1000.0 / statistics.mean(samples),
        "measurement": "synchronized wall-clock callable latency",
    }
