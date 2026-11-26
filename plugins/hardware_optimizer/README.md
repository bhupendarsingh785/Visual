# VISUAL Hardware Optimizer

Adds hardware discovery, workload-aware optimization planning and optional ONNX Runtime session initialization.

- Detects CPU architecture/count, available RAM, Android SoC properties, common accelerator device nodes, ONNX Runtime execution providers and local inference executables.
- Produces conservative plans for LLM, vision, audio/speech and robotics workloads.
- If ONNX Runtime is already installed, initializes a local ONNX model with graph optimizations and only providers actually exposed by that runtime.
- Restricts model paths to ~/.visual/models, Android Download and Documents.
- Does not create physical hardware, install packages, download models, alter drivers, overclock, undervolt, fine-tune weights or claim speedups without benchmarks.
- Device-node presence does not prove driver compatibility; session initialization is not proof of inference performance.

Workflow: profile device -> record baseline -> select compatible backend/precision -> measure end-to-end latency, throughput, peak RAM, utilization, energy and temperature -> compare output quality -> enable only after regression tests. Keep CPU fallback.
