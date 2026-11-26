# VISUAL AI Chip Design Lab

This directory contains synthesizable SystemVerilog building blocks for research, simulation and FPGA prototyping. These are RTL designs, not fabricated silicon and not a claim of a production-ready CPU/GPU.

## Included architectures

- `ai_mac_pe.sv`: signed multiply-accumulate processing element; cascade multiple PEs into a systolic array.
- `ai_simd_vector.sv`: parameterized multi-lane integer SIMD arithmetic.
- `ai_xnor_popcount.sv`: XNOR/popcount primitive used by binary neural networks.
- `ai_spiking_neuron.sv`: leaky integrate-and-fire neuron.
- `visual_ai_compute_tile.sv`: integration tile combining SIMD, BNN and spiking blocks.

## Quick simulation

With Icarus Verilog installed:

```sh
iverilog -g2012 -s visual_ai_compute_tile -o /tmp/visual_chip.vvp rtl/ai_simd_vector.sv rtl/ai_xnor_popcount.sv rtl/ai_spiking_neuron.sv rtl/visual_ai_compute_tile.sv
vvp /tmp/visual_chip.vvp
```

The command above elaborates the integration top; add a testbench to run functional assertions. For FPGA use, select a target board, clock constraints, pin constraints, synthesis tool and timing constraints. Validate reset behavior, signed arithmetic, overflow, timing closure, area, power and thermal behavior before deployment.

## Roadmap

1. Add a verified systolic array wrapper and parameterized dataflow.
2. Add DMA and memory-mapped control/status registers.
3. Add quantized INT8/INT4 datapaths with saturation and rounding.
4. Add bus interfaces and platform-specific FPGA constraints.
5. Benchmark against CPU/GPU runtimes using identical workloads and report measured latency, throughput, area and power.

No code here overclocks a device, writes privileged hardware registers, or creates a physical chip. Silicon fabrication requires a foundry and a verified physical-design flow.
