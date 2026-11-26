"""Multi-GPU replica layer for VISUAL.

Creates logical worker roles and, when multiple CUDA devices are truly available,
uses PyTorch DataParallel replicas for a single-process training run. It never
pretends CPU cores are physical GPUs and never creates virtual silicon.
"""
from __future__ import annotations


def multi_gpu_topology(torch_module=None):
    """Describe real CUDA devices and safe logical worker roles."""
    if torch_module is None:
        try:
            import torch as torch_module
        except ImportError:
            return {
                "mode": "cpu_only", "physical_cuda_gpus": [],
                "logical_workers": [{"id": "cpu-control", "role": "orchestration-data-validation"}],
                "multi_gpu_training_ready": False,
                "reason": "PyTorch is not installed; no CUDA device can be verified."
            }
    devices = []
    try:
        if torch_module.cuda.is_available():
            for index in range(torch_module.cuda.device_count()):
                try:
                    props = torch_module.cuda.get_device_properties(index)
                    devices.append({
                        "index": index,
                        "name": props.name,
                        "memory_bytes": getattr(props, "total_memory", None),
                    })
                except Exception as exc:
                    devices.append({"index": index, "name": f"CUDA device {index}",
                                    "inventory_error": str(exc)[:160]})
    except Exception as exc:
        return {"mode": "cpu_only", "physical_cuda_gpus": [],
                "logical_workers": [{"id": "cpu-control", "role": "orchestration-data-validation"}],
                "multi_gpu_training_ready": False, "reason": str(exc)[:200]}
    workers = [{"id": "cpu-control", "role": "orchestration-data-loading-preprocessing-validation"}]
    for item in devices:
        workers.append({
            "id": f"cuda-replica-{item['index']}",
            "device": f"cuda:{item['index']}",
            "role": "data-parallel-model-replica",
            "physical_device_index": item["index"],
        })
    if len(devices) > 1:
        mode = "multi_cuda_data_parallel"
        reason = "Multiple CUDA GPUs detected; DataParallel can replicate the model and split each batch across them."
    elif len(devices) == 1:
        mode = "single_cuda_gpu"
        reason = "Only one CUDA GPU detected; logical role separation does not create additional GPU hardware."
    else:
        mode = "cpu_only"
        reason = "No CUDA GPUs detected; CPU worker remains available. No fake GPU devices are created."
    return {
        "mode": mode, "physical_cuda_gpus": devices,
        "logical_workers": workers,
        "multi_gpu_training_ready": len(devices) > 1,
        "replica_count": len(devices),
        "reason": reason,
        "limitations": [
            "This implementation uses single-process PyTorch DataParallel for CUDA GPUs only.",
            "MPS/XPU and multi-node DDP are inventoried elsewhere but are not silently treated as CUDA replicas.",
            "The effective batch is split across GPUs; each GPU needs enough VRAM for its model replica and activations.",
            "CPU is the coordinator/data pipeline, not a GPU replica."
        ]
    }


def wrap_for_multi_gpu(model, torch_module=None):
    """Return (model, report); wrap only when at least two real CUDA devices exist."""
    if torch_module is None:
        try:
            import torch as torch_module
        except ImportError as exc:
            raise RuntimeError("PyTorch is required for multi-GPU training.") from exc
    report = multi_gpu_topology(torch_module)
    if not report["multi_gpu_training_ready"]:
        return model, report
    ids = [device["index"] for device in report["physical_cuda_gpus"]]
    model = model.to(torch_module.device(f"cuda:{ids[0]}"))
    return torch_module.nn.DataParallel(model, device_ids=ids, output_device=ids[0]), report


def run_multi_gpu_training(model, train_loader, validation_loader, optimizer, loss_fn, **kwargs):
    """Use real CUDA replicas when available, then delegate to bounded trainer."""
    from training_runtime import run_training
    import torch
    wrapped, topology = wrap_for_multi_gpu(model, torch)
    requested_device = kwargs.pop("device", None)
    target_device = "cuda:0" if topology["multi_gpu_training_ready"] else requested_device
    result = run_training(wrapped, train_loader, validation_loader, optimizer, loss_fn,
                          device=target_device, **kwargs)
    result["multi_gpu_topology"] = topology
    result["distributed_training"] = bool(topology["multi_gpu_training_ready"])
    result["parallel_strategy"] = "torch.nn.DataParallel" if topology["multi_gpu_training_ready"] else "single_device_fallback"
    return result
