"""Bounded, recoverable PyTorch training primitive for VISUAL.

Callers must explicitly provide the model, dataloaders, optimizer and loss.
This module never downloads data or launches a training job on import.
"""
import copy
import math
import os
import tempfile
import time
from pathlib import Path


def validate_training_limits(epochs=3, max_steps_per_epoch=500,
                             validation_steps=100, patience=3,
                             max_seconds=3600, gradient_clip_norm=1.0):
    values = {
        "epochs": (int(epochs), 1, 500),
        "max_steps_per_epoch": (int(max_steps_per_epoch), 1, 100000),
        "validation_steps": (int(validation_steps), 1, 100000),
        "patience": (int(patience), 1, 100),
        "max_seconds": (int(max_seconds), 1, 86400),
    }
    for name, (value, low, high) in values.items():
        if value < low or value > high:
            raise ValueError(f"{name} must be between {low} and {high}")
    clip = float(gradient_clip_norm)
    if not math.isfinite(clip) or clip <= 0 or clip > 1000:
        raise ValueError("gradient_clip_norm must be finite and in (0, 1000]")
    return {name: item[0] for name, item in values.items()} | {
        "gradient_clip_norm": clip
    }


def _move(value, device, torch):
    if torch.is_tensor(value):
        return value.to(device, non_blocking=(str(device).startswith("cuda")))
    if isinstance(value, tuple):
        return tuple(_move(v, device, torch) for v in value)
    if isinstance(value, list):
        return [_move(v, device, torch) for v in value]
    if isinstance(value, dict):
        return {k: _move(v, device, torch) for k, v in value.items()}
    return value


def _device(torch, requested=None):
    if requested:
        device = torch.device(requested)
        if device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but unavailable")
        if device.type == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS requested but unavailable")
        if device.type == "xpu" and (getattr(torch, "xpu", None) is None or not torch.xpu.is_available()):
            raise RuntimeError("XPU requested but unavailable")
        return device
    if torch.cuda.is_available():
        return torch.device("cuda:0")
    mps = getattr(getattr(torch.backends, "mps", None), "is_available", lambda: False)
    if mps():
        return torch.device("mps")
    xpu = getattr(torch, "xpu", None)
    if xpu is not None and xpu.is_available():
        return torch.device("xpu:0")
    return torch.device("cpu")


def run_training(model, train_loader, validation_loader, optimizer, loss_fn,
                 *, device=None, epochs=3, max_steps_per_epoch=500,
                 validation_steps=100, patience=3, max_seconds=3600,
                 gradient_clip_norm=1.0, checkpoint_dir=None,
                 precision="fp32"):
    """Train a caller-supplied model with bounded FP32/AMP and safe checkpoints."""
    limits = validate_training_limits(
        epochs, max_steps_per_epoch, validation_steps, patience,
        max_seconds, gradient_clip_norm
    )
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is required; install a compatible build explicitly.") from exc

    if precision not in {"fp32", "fp16", "bf16"}:
        raise ValueError("precision must be fp32, fp16, or bf16")
    target = _device(torch, device)
    if precision == "fp16" and target.type not in {"cuda", "xpu"}:
        raise ValueError("fp16 AMP is supported here only on CUDA/XPU; use bf16 or fp32")
    if precision == "bf16" and target.type not in {"cpu", "cuda", "xpu"}:
        raise ValueError("bf16 AMP is not enabled for this device type")
    model.to(target)
    amp_enabled = precision != "fp32"
    amp_dtype = torch.float16 if precision == "fp16" else torch.bfloat16
    scaler = torch.amp.GradScaler(target.type, enabled=(precision == "fp16"))
    started = time.monotonic()
    best_loss = float("inf")
    best_state = None
    best_optimizer = None
    bad_epochs = 0
    history = []
    stopped_reason = "epoch_limit"
    checkpoint_path = None

    root = Path(checkpoint_dir or (Path.home() / ".visual" / "checkpoints")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError("checkpoint_dir must be a directory")
    checkpoint_path = root / f"visual-training-{time.time_ns()}.pt"

    def run_validation():
        model.eval()
        total = 0.0
        sample_count = 0
        batch_count = 0
        with torch.no_grad():
            for batch in validation_loader:
                if batch_count >= limits["validation_steps"]:
                    break
                if time.monotonic() - started >= limits["max_seconds"]:
                    return None
                if not isinstance(batch, (tuple, list)) or len(batch) < 2:
                    raise ValueError("Each batch must contain (inputs, targets)")
                inputs = _move(batch[0], target, torch)
                targets = _move(batch[1], target, torch)
                with torch.autocast(device_type=target.type, dtype=amp_dtype,
                                    enabled=amp_enabled):
                    loss = loss_fn(model(inputs), targets)
                if not torch.isfinite(loss).all():
                    raise FloatingPointError("Non-finite validation loss")
                batch_size = int(targets.shape[0]) if getattr(targets, "ndim", 0) > 0 else 1
                total += float(loss.detach().item()) * batch_size
                sample_count += batch_size
                batch_count += 1
                if time.monotonic() - started >= limits["max_seconds"]:
                    return None
        if not sample_count:
            if time.monotonic() - started >= limits["max_seconds"]:
                return None
            raise ValueError("validation_loader produced no batches")
        return total / sample_count

    try:
        for epoch in range(limits["epochs"]):
            model.train()
            train_total = 0.0
            train_samples = 0
            train_steps = 0
            for batch in train_loader:
                if time.monotonic() - started >= limits["max_seconds"]:
                    stopped_reason = "time_limit"
                    break
                if train_steps >= limits["max_steps_per_epoch"]:
                    break
                if not isinstance(batch, (tuple, list)) or len(batch) < 2:
                    raise ValueError("Each batch must contain (inputs, targets)")
                inputs = _move(batch[0], target, torch)
                targets = _move(batch[1], target, torch)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type=target.type, dtype=amp_dtype,
                                    enabled=amp_enabled):
                    loss = loss_fn(model(inputs), targets)
                if not torch.isfinite(loss).all():
                    raise FloatingPointError("Non-finite training loss")
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), limits["gradient_clip_norm"])
                scaler.step(optimizer)
                scaler.update()
                batch_size = int(targets.shape[0]) if getattr(targets, "ndim", 0) > 0 else 1
                train_total += float(loss.detach().item()) * batch_size
                train_samples += batch_size
                train_steps += 1
            if not train_steps:
                if stopped_reason != "time_limit":
                    raise ValueError("train_loader produced no batches")
                break

            validation_loss = run_validation()
            if validation_loss is None:
                stopped_reason = "time_limit"
                break
            record = {
                "epoch": epoch + 1,
                "train_loss": train_total / train_samples,
                "validation_loss": validation_loss,
                "steps": train_steps,
                "training_samples": train_samples,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
            history.append(record)
            if validation_loss < best_loss:
                best_loss = validation_loss
                best_state = copy.deepcopy(model.state_dict())
                best_optimizer = copy.deepcopy(optimizer.state_dict())
                bad_epochs = 0
                fd, temporary = tempfile.mkstemp(prefix=".visual-train-", suffix=".tmp", dir=str(root))
                os.close(fd)
                try:
                    torch.save({
                        "model_state": best_state,
                        "optimizer_state": best_optimizer,
                        "epoch": epoch + 1,
                        "validation_loss": best_loss,
                        "device": str(target),
                    }, temporary)
                    os.replace(temporary, checkpoint_path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            else:
                bad_epochs += 1
                if bad_epochs >= limits["patience"]:
                    stopped_reason = "early_stopping"
                    break
            if stopped_reason == "time_limit":
                break
    except Exception:
        if best_state is not None:
            model.load_state_dict(best_state)
            if best_optimizer is not None:
                optimizer.load_state_dict(best_optimizer)
        raise

    if best_state is not None:
        model.load_state_dict(best_state)
    return {
        "status": "completed" if history else "no_training_steps",
        "device": str(target),
        "epochs_completed": len(history),
        "best_validation_loss": best_loss if best_state is not None else None,
        "stopped_reason": stopped_reason,
        "history": history,
        "best_checkpoint": str(checkpoint_path) if best_state is not None else None,
        "rolled_back_to_best_weights": best_state is not None,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "limits": limits,
        "distributed_training": False,
        "training_updates": sum(item["steps"] for item in history),
        "validation_is_sample_weighted": True,
        "validation_steps_unit": "batches",
        "precision": precision,
        "amp_enabled": amp_enabled,
    }
