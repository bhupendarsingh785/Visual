# VISUAL Hardware Intelligence & Optimization Architecture

## Mission
Build a portable software layer that makes the best measured use of the CPU, GPU and NPU already present in a device. It does not manufacture silicon, replace firmware, or promise a speedup without measurements.

## Hardware layers (keep these distinct)
1. Silicon / microarchitecture — cores, execution units, caches, memory controllers, SIMD, GPU compute units, NPU MAC arrays. These require chip design and fabrication; software in this repository cannot create them.
2. Firmware and drivers — kernel drivers, GPU userspace drivers, vendor NPU runtime. Usually supplied and signed by the device/OEM; never overwrite or bypass them.
3. Compiler and kernels — ARM NEON/SVE, x86 AVX, GPU shaders/kernels, optimized matrix multiplication, fused operators, memory layouts.
4. Inference runtime — ONNX Runtime execution providers, llama.cpp/ggml, LiteRT delegates, vendor SDKs such as Qualcomm QNN where supported.
5. VISUAL scheduler — workload classification, device capability detection, memory/thermal budgets, backend selection, fallback, profiling and regression gates.

## Runtime selection policy
- Discover actual installed providers and libraries at runtime. A SoC marketing specification or device node alone is not proof of usable acceleration.
- Select only a provider that the installed runtime reports and that successfully initializes for the target model.
- Prefer accelerator execution for supported expensive subgraphs; keep CPU for unsupported operators. Avoid repeated CPU↔GPU copies and tiny offloads whose transfer overhead exceeds compute savings.
- On Android, NNAPI is deprecated starting Android 15. Do not make it the default future path. Prefer maintained runtime/delegate/vendor paths actually shipped for the device; preserve CPU fallback.
- For CPU-only LLMs, benchmark GGUF/llama.cpp quantization and ARM NEON support on the exact phone. Q4/Q5 are quality/performance trade-offs, not universal winners.

## Workload intelligence
- LLM: weight quantization, KV-cache quantization/budgeting, bounded context, batch=1 interactive decoding, prompt prefill/decode separated, one model resident where possible.
- Vision: resize/crop once, fuse preprocessing where supported, reuse buffers, batch only when latency budget permits.
- Audio: streaming chunks, bounded look-ahead, avoid repeated resampling and format conversion, keep voice activity detection cheap.
- Robotics/control: deterministic deadlines and bounded latency take priority over raw throughput; never put a safety-critical control loop behind an unbounded LLM call.

## Memory and thermal control
- Reserve RAM for Android and the app; model weights + KV cache + activations + runtime buffers must fit with headroom.
- Use memory-mapped weights where supported, reuse tensor buffers, avoid duplicate model copies and release idle sessions.
- Read thermal/frequency signals only where exposed by the OS. Reduce concurrency/context/batch under thermal pressure; never overclock, undervolt, or write privileged sysfs nodes.
- More threads are not always faster: benchmark thread counts and account for big.LITTLE core topology, scheduler contention and battery drain.

## Measurement contract
Record device/OS/runtime/provider/model hash/quantization/input shape/thread count, warm-up count, run count, median and p95 latency, throughput, peak RSS, CPU/GPU/NPU utilization when exposed, temperature and battery/energy where available. Compare baseline and candidate on the same device and inputs.
- A speedup is accepted only if correctness/quality stays within the declared tolerance and the measured target metric improves.
- Reject unstable, thermally throttled or incomparable runs.
- Store benchmark records as JSON with provenance; do not mix synthetic-input results with real user workload results.

## Research-backed building blocks
- ONNX Runtime Execution Providers partition supported subgraphs across hardware backends and retain CPU fallback.
- ONNX Runtime graph optimizations include constant folding, redundant-node elimination, operator fusion and layout optimizations.
- llama.cpp supports CPU SIMD paths including ARM NEON and multiple quantization families; test on the actual target device.
- Apache TVM is a compiler route for target-specific graph/kernel optimization, but adds build and maintenance complexity. Adopt only after a reproducible benchmark demonstrates value.
- Android NNAPI is deprecated from Android 15; runtime/delegate strategy must be version-aware.

## Development gates
A. Device inventory tests.
B. Backend initialization tests per device family.
C. Numerical correctness tests against CPU reference.
D. Sustained 10-30 minute thermal and memory stress tests.
E. Real workload benchmark and quality checks.
F. Canary rollout, fallback and rollback.
No feature is marked production-ready until all relevant gates pass.


## Compute-fabric integration
The `compute_fabric` module inventories PyTorch CUDA/MPS/XPU devices and ONNX Runtime providers at runtime. The scheduler treats CPU as the control/data-loading and correctness-fallback domain; it only selects accelerators reported by installed runtimes. TensorRT is preferred over CUDA when both ONNX providers are exposed, while actual graph partitioning and numerical correctness must still be checked per model. A DPU is not assumed: networking/storage offload is enabled only when a concrete vendor runtime and device are detected. `hardware_compute_fabric_plan` is a preflight planner, not a training executor.

## Training execution contract
Training jobs must be explicit and bounded. The reusable training runtime accepts caller-provided model, dataloaders, optimizer and loss function; it enforces epoch/step/time limits, finite-loss checks, validation-based best-checkpoint selection, early stopping and rollback to the best in-memory weights. It does not download datasets, choose licenses, start jobs automatically or promise multi-GPU training. DDP requires a separately validated launcher/backend and is not inferred from the presence of `torchrun` alone.


## Dataset provenance and evaluation
`dataset_manifest.py` inventories local training data without downloading or uploading it. Every file receives a SHA-256 digest and byte count; a declared source and license are mandatory, and unknown licenses or pending/denied consent quarantine the dataset from training eligibility. The manifest records paths and metadata, not dataset contents. `benchmark.py` provides bounded warm-up and synchronized latency measurements with median/p95 and throughput. Results must be collected on the target machine with identical inputs and runtime versions before claiming performance gains.


## Multi-GPU replica fabric
The `multi_gpu.py` layer inventories actual CUDA devices and assigns one model replica worker per detected GPU, with the CPU acting as coordinator and data pipeline. For two or more real CUDA GPUs, `run_multi_gpu_training` uses PyTorch `DataParallel` to replicate the model and split batches. It falls back to the existing single-device trainer on zero/one CUDA GPU. This does not manufacture GPUs by copying CPU/GPU code. CUDA-only in this implementation; multi-node DDP and MPS/XPU replica training remain future work. Validate VRAM fit, numerical equivalence, throughput and sustained thermals on the target computer before production use.


## Distributed training, profiling and recovery (implementation status)
- `distributed_training.py` provides explicit `torchrun` environment validation, one-process-per-device initialization, NCCL selection only when CUDA is available, Gloo CPU fallback for integration tests, DDP wrapping, `DistributedSampler` construction, sample-weighted all-reduce, and rank-0 atomic checkpoints.
- Every distributed training entrypoint must call `sampler.set_epoch(epoch)` and use equal-length rank workloads. DDP does not shard input data itself. Keep all ranks on the same collective/control-flow path; a rank-local exception can otherwise strand peers in collectives.
- Launch CUDA jobs with `torchrun --standalone --nproc_per_node=<GPU_COUNT> your_training_entrypoint.py`. Set `--max-restarts` only when the entrypoint loads a checkpoint and can safely resume. The existing bounded `run_training` function remains single-process; the new helpers are primitives, not yet a replacement end-to-end distributed trainer.
- `save_checkpoint` stores model, optimizer, optional scheduler/scaler, epoch and metadata atomically on rank 0. `load_checkpoint` restores those states. RNG states, sampler position, dataloader worker state and automatic elastic restart orchestration are not yet persisted; exact mid-epoch replay is therefore not guaranteed.
- `profiler.py` offers opt-in scheduled CPU/CUDA profiling and Chrome trace export. Run it separately from performance benchmarks because profiler instrumentation changes timing.
- CI now adds a two-process CPU Gloo DDP synchronization test, checkpoint round-trip/profiler trace tests, and a Yosys synthesis/structural-check job for the multi-tile MAC cluster.
- Yosys synthesis plus Icarus simulation are RTL verification, not FPGA board validation. FPGA validation still requires a selected board/device, vendor toolchain, pin/clock constraints, timing closure, bitstream programming, on-board functional tests, and measured power/performance. No physical FPGA has been tested by CI.
