# VISUAL AI Chip Design Lab

## Scope and honest status
This directory is a research RTL prototype for a computer/workstation/server accelerator. It is not a fabricated chip and is not yet connected to the host CPU/GPU/DPU runtime. Source code alone cannot install a new compute unit into existing silicon. A real device requires FPGA deployment or a complete ASIC implementation and fabrication.

## Current prototype
- `rtl/visual_ai_mac_tile.sv`: parameterized signed INT8 multiply-accumulate tile.
- `rtl/visual_ai_chip_cluster.sv`: parameterized parallel cluster; default is four tiles × eight lanes = 32 INT8 MAC lanes.
- `tb/tb_visual_ai_chip_cluster.sv`: self-checking testbench for dot-product result, accumulation, valid signaling and per-tile clear.
- Existing `plugins/chip_lab`: SIMD, XNOR/popcount and leaky-integrate-and-fire research blocks.

The cluster is a parallel MAC bank, not yet a complete systolic matrix-multiplication engine or general-purpose processor.

## Architecture target
1. **Host CPU/control complex** — OS, orchestration, command queues, exception handling and software fallback.
2. **GPU complex** — existing vendor GPU for graphics and parallel kernels, using supported drivers/runtime.
3. **NPU/AI complex** — vendor-supported inference engine when present.
4. **DPU/data complex** — networking, storage and data movement where a real DPU exists.
5. **VISUAL accelerator IP** — dedicated quantized matrix/vector datapath, local SRAM/buffers, DMA, command processor, interrupt/status and host bus interface.
6. **VISUAL runtime** — capability discovery, workload partitioning, measured scheduling, CPU reference path and rollback.

The RTL prototype is an optional future IP block; it must not be advertised as an accelerator available on the current PC until synthesized, deployed and benchmarked on an actual FPGA/ASIC board.

## Research-backed design rules
- Use a documented, portable instruction/data model. RISC-V Vector (V) defines vector registers, element widths and portable vector operations; do not invent incompatible host CPU opcodes for a first accelerator prototype.
- Start with a standard host interface (AXI4/AXI4-Lite for FPGA/SoC integration) and separate control/status from high-bandwidth data movement.
- Build a bit-exact software golden model before optimizing RTL. Test signed extrema (-128, 127), negative products, overflow, reset, stalls, backpressure, clear, repeated commands and malformed transactions.
- Simulation is necessary but not sufficient. Add randomized cocotb tests, assertions, formal checks with SymbiYosys/Yosys-SMTBMC, lint with Verilator, synthesis statistics with Yosys, and timing/physical implementation with a suitable FPGA or ASIC flow.
- Keep CPU reference outputs as the correctness oracle. An accelerator result must match the declared quantization/rounding/saturation specification before it can be selected.
- Profile the whole workload, including DMA and CPU↔accelerator transfers. A faster MAC datapath can still make the application slower if memory movement dominates.
- Do not overclock, undervolt, write privileged hardware registers or bypass vendor drivers.

## Required implementation stages (not marked complete until evidence exists)
### Stage A — RTL correctness
- Signed INT8 multiply, accumulation width and overflow behavior formally specified.
- Saturation/rounding and optional INT4 mode with explicit scale/zero-point contract.
- Valid/ready protocol with reset and clear semantics.
- Independent Python reference model and randomized tests.
- Formal properties for no state change without handshake, reset behavior, no invalid output, and bounded completion.

### Stage B — compute architecture
- Systolic PE grid with documented dataflow (output-stationary or weight-stationary).
- Local operand/accumulator buffers and explicit bank-conflict behavior.
- Command decoder, descriptor validation, bounds checking and error status.
- DMA and host bus integration with address protection and timeout recovery.
- Interrupt/status registers and reset/abort recovery.

### Stage C — FPGA proof
- Named FPGA board and toolchain; clock/reset and pin constraints.
- Synthesis resource report (LUT/FF/DSP/BRAM), timing closure, Fmax, power estimate.
- Board-level tests with host driver and real inference workload.
- CPU/GPU baseline on identical input/model and measured end-to-end latency, throughput, power and thermal results.

### Stage D — ASIC feasibility
- Select a PDK and compatible standard-cell libraries.
- Floorplan, placement, clock-tree synthesis, routing, extraction and static timing analysis.
- DRC/LVS and power-integrity checks; review area, power, IR drop and electromigration.
- Only after signoff and foundry fabrication may the design be called physical silicon.

## Open toolchain research
- Icarus Verilog: quick RTL simulation.
- Verilator: lint and fast compiled simulation.
- cocotb: Python-driven randomized tests and scoreboards.
- Yosys: synthesis and logic statistics; not a complete place-and-route tool.
- SymbiYosys/Yosys-SMTBMC: formal property checking.
- OpenROAD/OpenLane or LibreLane: ASIC physical-design flow, subject to supported PDK and reproducible configuration.
- FPGA vendor tools / nextpnr: board-specific mapping and implementation.

## Verification evidence
The repository CI runs Python tests and Icarus Verilog smoke simulations. CI passing proves only the tests that ran on the specified simulator and software matrix. It does not prove formal correctness, FPGA timing closure, power, performance, or fabrication readiness. Preserve failed runs as regression cases and fix the RTL or testbench based on root-cause evidence rather than weakening assertions.


## Host integration status
The software compute-fabric planner can discover vendor-provided CPU/GPU/NPU runtimes, but this RTL cluster has no bus, DMA engine, command queue, memory-mapped control registers, interrupt controller, synthesis constraints or host driver yet. The next hardware milestones are a systolic dataflow, SRAM/buffer design, AXI4-Lite control plus AXI4 data path, descriptor validation, timeout/reset handling, then FPGA-board proof. No host runtime may select this RTL until board-level tests and a driver-backed execution provider exist.
