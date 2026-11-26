"""Multi-CPU / multi-GPU worker topology for VISUAL.

Logical workers are software processes, not fabricated hardware. GPU replicas
share the physical device's compute and VRAM; only distinct detected devices
can be counted as independent GPUs.
"""
import importlib.util
import os


def build_parallel_fabric(cpu_workers=0, gpu_workers_per_device=1,
                          max_gpu_workers_per_device=2):
    cpu_count = max(1, os.cpu_count() or 1)
    requested_cpu = int(cpu_workers or 0)
    per_gpu = int(gpu_workers_per_device or 1)
    max_per_gpu = int(max_gpu_workers_per_device or 2)
    if requested_cpu < 0 or requested_cpu > 256:
        raise ValueError("cpu_workers must be between 0 and 256")
    if per_gpu < 1 or per_gpu > 8:
        raise ValueError("gpu_workers_per_device must be between 1 and 8")
    if max_per_gpu < 1 or max_per_gpu > 8 or per_gpu > max_per_gpu:
        raise ValueError("GPU worker count must not exceed the configured safe cap")

    cpu_total = min(requested_cpu or max(1, cpu_count - 1), max(1, cpu_count - 1), 64)
    gpu_devices = []
    torch_installed = importlib.util.find_spec("torch") is not None
    if torch_installed:
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    gpu_devices.append({
                        "device": f"cuda:{i}", "name": props.name,
                        "memory_bytes": getattr(props, "total_memory", None),
                    })
            if not gpu_devices:
                mps = getattr(getattr(torch.backends, "mps", None), "is_available", lambda: False)
                if mps():
                    gpu_devices.append({"device": "mps", "name": "Apple Metal", "memory_bytes": None})
            if not gpu_devices:
                xpu = getattr(torch, "xpu", None)
                if xpu is not None and xpu.is_available():
                    for i in range(xpu.device_count()):
                        gpu_devices.append({"device": f"xpu:{i}", "name": "Intel XPU", "memory_bytes": None})
        except Exception:
            gpu_devices = []

    workers = []
    for i in range(cpu_total):
        workers.append({"id": f"cpu-worker-{i}", "role": "data-preprocess",
                        "device": "cpu", "process": "bounded"})
    for gpu in gpu_devices:
        for replica in range(per_gpu):
            workers.append({
                "id": f"{gpu['device']}-worker-{replica}",
                "role": "model-compute-replica", "device": gpu["device"],
                "replica": replica,
                "note": "Shares this physical GPU and its VRAM; not an additional GPU."
            })
    return {
        "topology": "cpu-data-pipeline-plus-gpu-replicas",
        "physical_gpu_count": len(gpu_devices),
        "logical_gpu_worker_count": len(gpu_devices) * per_gpu,
        "cpu_worker_count": cpu_total,
        "cpu_workers": workers[:cpu_total],
        "gpu_devices": gpu_devices,
        "gpu_workers": workers[cpu_total:],
        "distributed_training_ready": False,
        "distributed_training_note": (
            "This is a worker topology plan only. Multi-GPU gradient synchronization "
            "requires a validated torch.distributed launcher/backend and DDP integration."
        ),
        "limits": {"max_cpu_workers": 64, "max_gpu_workers_per_device": max_per_gpu},
    }


def distributed_training_preflight():
    """Report whether this process is inside a valid torchrun-style distributed job."""
    if importlib.util.find_spec("torch") is None:
        return {"ready": False, "reason": "PyTorch is not installed"}
    try:
        import torch
        import torch.distributed as dist
        world_size = int(os.environ.get("WORLD_SIZE", "1"))
        local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        available = dist.is_available()
        backends = []
        if available:
            if dist.is_nccl_available():
                backends.append("nccl")
            if dist.is_gloo_available():
                backends.append("gloo")
        cuda_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
        backend = "nccl" if cuda_count and "nccl" in backends else ("gloo" if "gloo" in backends else None)
        return {
            "ready": bool(available and backend and world_size > 1),
            "distributed_available": available, "world_size": world_size,
            "local_rank": local_rank, "backend_candidates": backends,
            "selected_backend": backend,
            "physical_cuda_devices": cuda_count,
            "reason": "torchrun environment and backend are ready" if available and backend and world_size > 1
                      else "Launch multiple processes with torchrun and verify the communication backend first",
        }
    except Exception as exc:
        return {"ready": False, "reason": str(exc)[:240]}
