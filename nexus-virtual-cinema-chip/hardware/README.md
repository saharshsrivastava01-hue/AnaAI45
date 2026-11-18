# NEXUS-3000 hardware prototype

## Scope
This directory starts the path from the software-defined NEXUS virtual chip to
real programmable logic. v0.1 contains a synthesizable four-lane signed INT16
vector compute tile with vector multiply-accumulate and ReLU-sum operations,
plus a SystemVerilog testbench.

It is **not** a complete GPU/TPU, does not contain a physical memory controller,
video pipeline, PCIe interface, or fabricated silicon. No performance or power
claims are made. A physical implementation requires FPGA hardware, vendor
synthesis/place-and-route tools, timing closure, board-level power validation,
and eventually ASIC design/foundry work.

## Verify with Icarus Verilog
From this directory:
```sh
iverilog -g2012 -s tb_nexus3000_compute_tile -o /tmp/nexus_tb rtl/nexus3000_compute_tile.sv tb/tb_nexus3000_compute_tile.sv
vvp /tmp/nexus_tb
```

Expected: `NEXUS compute tile tests PASS`.

## Roadmap
1. v0.1 compute tile and simulation.
2. Add parameterized scratchpad SRAM interface, DMA and command queue.
3. Add tiled matrix multiply and fixed-point/FP formats.
4. Add display/video DMA and compositing accelerator blocks.
5. Add AXI4 interconnect, clock/reset domains, interrupts and FPGA constraints.
6. Integrate on a supported FPGA development board; measure resource use, clock,
   throughput and board power. Only measured results become specifications.

The GPU/TPU labels in the wider software scheduler are virtual scheduling domains,
not physical accelerators. This RTL is the first small, real hardware-design artifact.


## v0.2 integrated chip top

The v0.2 prototype adds `rtl/nexus3000_chip_top.sv`, which connects the
command sequencer to the four-lane INT16 compute tile. It accepts tagged
commands, routes vector MAC and ReLU operations, and returns a tagged result
with an error indication. The integration testbench is
`tb/tb_nexus3000_chip_top.sv`.

Run the integrated simulation with Icarus Verilog:

```sh
iverilog -g2012 -s tb_nexus3000_chip_top -o /tmp/nexus_top_tb \
  rtl/nexus3000_compute_tile.sv rtl/nexus3000_command_unit.sv \
  rtl/nexus3000_chip_top.sv tb/tb_nexus3000_chip_top.sv
vvp /tmp/nexus_top_tb
```

The GitHub Actions workflow now includes this integration simulation. A
committed workflow definition is not evidence of a passing run; check the
Actions page for the actual result. The design still requires FPGA synthesis,
timing closure, board validation and hardware measurements before it can be
called a working physical chip.
