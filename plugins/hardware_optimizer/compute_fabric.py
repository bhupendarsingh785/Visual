"""Safe CPU/GPU/NPU workload planner and training preflight for VISUAL.

This layer orchestrates installed runtimes; it does not install drivers, change
firmware, claim custom RTL is active, or launch unbounded training jobs.
"""
import importlib.util
import os
import platform
import shutil


def _torch_inventory():
    if importlib.util.find_spec("torch") is None:
        return {"installed": False, "available": False, "devices": [], "error": "PyTorch not installed"}
    try:
        import torch
        devices = []
        if torch.cuda.is_available():
            for index in range(torch.cuda.device_count()):
                try:
                    props = torch.cuda.get_device_properties(index)
                    devices.append({"kind": "cuda", "index": index, "name": props.name,
                                    "memory_bytes": getattr(props, "total_memory", None)})
                except Exception as exc:
                    devices.append({"kind": "cuda", "index": index, "error": str(exc)[:160]})
        mps = getattr(getattr(torch.backends, "mps", None), "is_available", lambda: False)()
        if mps:
            devices.append({"kind": "mps", "name": "Apple Metal"})
        xpu = getattr(torch, "xpu", None)
        if xpu is not None and getattr(xpu, "is_available", lambda: False)():
            for index in range(xpu.device_count()):
                devices.append({"kind": "xpu", "index": index, "name": xpu.get_device_name(index)})
        return {"installed": True, "version": torch.__version__, "available": bool(devices),
                "devices": devices, "cpu_threads": os.cpu_count() or 1}
    except Exception as exc:
        return {"installed": True, "available": False, "devices": [], "error": str(exc)[:240]}


def compute_fabric_profile():
    """Discover only backends that the local runtime can actually initialize."""
    ort_providers = []
    ort_version = None
    if importlib.util.find_spec("onnxruntime") is not None:
        try:
            import onnxruntime as ort
            ort_providers = list(ort.get_available_providers())
            ort_version = ort.__version__
        except Exception:
            pass
    return {
        "host": {"system": platform.system(), "machine": platform.machine(),
                 "logical_cpus": os.cpu_count() or 1},
        "pytorch": _torch_inventory(),
        "onnxruntime": {"version": ort_version, "providers": ort_providers},
        "training_tools": {name: shutil.which(name) for name in ("torchrun", "accelerate", "deepspeed")
                           if shutil.which(name)},
        "custom_visual_accelerator": {
            "rtl_present": os.path.isdir(os.path.join(os.path.dirname(__file__), "chip_design")),
            "runtime_driver_available": False,
            "active": False,
            "reason": "RTL prototype is not synthesized/deployed on an FPGA or ASIC and has no host driver."
        }
    }


def compute_fabric_plan(workload="inference", training=False, memory_budget_gb=0):
    """Return an explainable, conservative device plan; never silently starts training."""
    profile = compute_fabric_profile()
    torch_info = profile["pytorch"]
    ort = profile["onnxruntime"]["providers"]
    devices = torch_info.get("devices", [])
    gpu_devices = [d for d in devices if d.get("kind") in ("cuda", "mps", "xpu")]
    if "CUDAExecutionProvider" in ort:
        ort_gpu = "CUDAExecutionProvider"
    elif "TensorrtExecutionProvider" in ort:
        ort_gpu = "TensorrtExecutionProvider"
    elif "DmlExecutionProvider" in ort:
        ort_gpu = "DmlExecutionProvider"
    elif "CoreMLExecutionProvider" in ort:
        ort_gpu = "CoreMLExecutionProvider"
    elif "QNNExecutionProvider" in ort:
        ort_gpu = "QNNExecutionProvider"
    elif "XNNPACKExecutionProvider" in ort:
        ort_gpu = "XNNPACKExecutionProvider"
    else:
        ort_gpu = None

    if gpu_devices:
        primary = gpu_devices[0]["kind"]
        selection_reason = "PyTorch reports an initialized accelerator; CPU remains available for orchestration and fallback."
    elif ort_gpu:
        primary = ort_gpu
        selection_reason = "ONNX Runtime exposes an accelerator execution provider; model-level partition support still must be verified."
    else:
        primary = "cpu"
        selection_reason = "No usable GPU/NPU training backend was confirmed; CPU fallback selected."

    mode = "training" if training else str(workload or "inference").lower()
    budget = max(0.0, float(memory_budget_gb or 0))
    steps = [
        "CPU owns OS-facing orchestration, data loading, validation, scheduling and safe fallback.",
        "Send only supported, sufficiently large tensor workloads to an initialized accelerator.",
        "Keep model, optimizer state, activations and batches inside measured host/device memory budgets.",
        "Measure host-to-device transfer and synchronization; do not split tiny operations when transfer cost dominates.",
        "Record backend, model/data hashes, seed, precision, peak RAM/VRAM, throughput and validation metrics.",
        "Use checkpointing, bounded worker counts, early stopping and a recoverable job state."
    ]
    if training:
        steps += [
            "Training requires an explicit model, licensed dataset, objective, validation split and user-approved compute budget.",
            "Use PyTorch device-specific training only after accelerator initialization; use CPU when no accelerator is available.",
            "For multi-GPU training, use torchrun/DDP only after checking compatible devices and communication backend.",
            "Do not train on evaluation/test data; preserve a held-out validation set and reproducible checkpoints."
        ]
    limitations = []
    if not torch_info.get("installed"):
        limitations.append("PyTorch is not installed; training capability is not currently available in this environment.")
    elif not torch_info.get("available"):
        limitations.append("PyTorch exposes no usable accelerator; CPU-only training may be possible but can be slow.")
    if not profile["custom_visual_accelerator"]["active"]:
        limitations.append("VISUAL custom RTL is design-only and cannot be scheduled as a live CPU/GPU device.")
    if budget:
        steps.append("Requested memory budget is advisory until actual free RAM/VRAM is measured for the selected model.")
    return {"workload": mode, "selected_primary": primary, "selection_reason": selection_reason,
            "cpu_role": "control, data pipeline, preprocessing, fallback",
            "accelerator_role": "parallel tensor compute when runtime and operator support are confirmed",
            "memory_budget_gb": budget, "profile": profile, "plan": steps, "limitations": limitations,
            "training_started": False, "custom_rtl_used": False}
