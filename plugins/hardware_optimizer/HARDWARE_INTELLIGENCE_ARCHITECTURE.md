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
