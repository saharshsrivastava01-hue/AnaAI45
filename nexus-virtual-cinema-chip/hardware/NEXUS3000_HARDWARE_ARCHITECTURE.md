# NEXUS-3000: from RTL to a physical accelerator

## Design intent
Build a modular accelerator that can first be simulated, then synthesized to an
FPGA, and only later considered for ASIC fabrication. No physical GPU/TPU is
created by this repository. The initial hardware is a small fixed-point compute
prototype; all performance, area, frequency and power values must come from
specific synthesis and board measurements.

## v0.2 building blocks
- Compute tile: four signed INT16 lanes, vector MAC and ReLU reduction.
- Tensor dot unit: four-lane INT16 dot product.
- Scratchpad: parameterized synchronous RAM inference candidate.
- Command unit: tagged command acceptance and legal-opcode checking.
- Testbench: first-cycle functional checks for compute arithmetic.

## Proposed SoC structure
Host/PCIe or USB bridge (board-dependent)
  -> AXI4-Lite control + AXI4 memory data fabric
  -> command queue / DMA
  -> local SRAM scratchpad banks
  -> vector/tensor compute tiles
  -> geometry and image-processing engines
  -> video output / frame-buffer DMA

The initial RTL does not yet implement PCIe, AXI, external DDR, a full GPU
rasterizer, shader ISA, floating-point tensor cores, cache coherence, or video
codec hardware. Those are separate engineering blocks.

## Engineering sequence
1. Simulate all RTL with Icarus Verilog or Verilator.
2. Add assertions, reset/handshake corner cases, randomized tests and lint.
3. Integrate AXI interfaces and a DMA engine.
4. Synthesize for a named FPGA board and inspect LUT/FF/BRAM/DSP reports.
5. Close timing, then validate measured board power and thermal limits.
6. Only after FPGA validation consider ASIC RTL hardening, DFT, floorplanning,
   clock-tree synthesis, static timing, IR-drop/EM and foundry PDK signoff.

## Reproducible local simulation
Install Icarus Verilog, then run from this directory:
```sh
iverilog -g2012 -s tb_nexus3000_compute_tile -o /tmp/nexus_tb rtl/nexus3000_compute_tile.sv tb/tb_nexus3000_compute_tile.sv
vvp /tmp/nexus_tb
```
Expected testbench output: `NEXUS compute tile tests PASS`.

## Practical constraints
- A development board is needed for real FPGA execution.
- ASIC fabrication requires a foundry process design kit, EDA signoff tools,
  tapeout preparation and substantial funding.
- The software virtual-chip's large lane counts are scheduler abstractions,
  not actual silicon lanes.
