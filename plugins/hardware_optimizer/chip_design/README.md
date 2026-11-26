# VISUAL AI Chip Design Lab

## What is included
- `rtl/visual_ai_mac_tile.sv`: parameterized signed INT8 multiply-accumulate tile.
- `rtl/visual_ai_chip_cluster.sv`: four parallel tiles (32 INT8 MAC lanes total by default).
- A host-facing integration concept for CPU/GPU/DPU systems.

## Important boundary
These are starter RTL source files describing digital logic. They do not create a physical chip, install silicon into a CPU/GPU, or accelerate the current computer by being present in this repository. To make hardware, synthesize the RTL for a supported FPGA board, validate timing/resource use, then pursue ASIC implementation and fabrication. No FPGA board or fabrication flow is assumed here.

## Intended architecture
1. Host CPU: operating system, orchestration, control plane and fallback.
2. Host GPU: graphics and general massively-parallel workloads.
3. Host DPU/NPU: vendor-supported inference/data-processing path where present.
4. VISUAL accelerator prototype: deterministic INT8 MAC tile array for matrix/vector kernels.
5. VISUAL runtime: dispatches only supported kernels to a detected and validated device; all other work remains on existing CPU/GPU/NPU backends.

## Current RTL capability
The tile computes a sum of pairwise signed 8-bit products over LANES inputs and accumulates the result in a 32-bit register. The cluster instantiates TILES independent tiles. It is a minimal compute datapath, not a complete neural-network processor: it has no DMA, external memory controller, cache, instruction decoder, compiler, PCIe/USB host interface, security subsystem, power management, or verified clock-domain crossing.

## Build and validation
With Icarus Verilog installed:
```sh
iverilog -g2012 -s visual_ai_chip_cluster -o /tmp/visual_ai_chip.vvp \
  plugins/hardware_optimizer/chip_design/rtl/visual_ai_mac_tile.sv \
  plugins/hardware_optimizer/chip_design/rtl/visual_ai_chip_cluster.sv
vvp /tmp/visual_ai_chip.vvp
```
The command above checks elaboration only; a dedicated testbench and FPGA board validation are still required before hardware claims.

## Roadmap to a real accelerator
- Add a verified testbench and bit-exact software reference.
- Add command registers, DMA, memory protection and host interface.
- Add tiled systolic matrix multiplication and activation/quantization blocks.
- Add clock/reset, interrupt, ECC/parity and fault reporting.
- Synthesize for a named FPGA target and measure LUT/DSP/BRAM use, Fmax, power and thermal behavior.
- Only then evaluate an ASIC flow and foundry process. Never claim production silicon without fabrication and board-level tests.
