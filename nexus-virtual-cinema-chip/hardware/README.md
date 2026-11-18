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


## v0.3 ray-tracing foundation

Added `rtl/nexus3000_ray_aabb.sv`: a fixed-point Q16.16 ray / axis-aligned
bounding-box (AABB) slab-intersection unit. It clips the ray's near/far interval
against the supplied bounds and returns a hit flag. This is a useful primitive
for a future bounding-volume hierarchy (BVH) traversal engine.

Simulation test: `tb/tb_nexus3000_ray_aabb.sv` checks one intersecting box and
one miss. The GitHub Actions workflow compiles and runs this test when triggered.

This block is not a complete ray tracer: it does not traverse a BVH, shade
triangles, sample materials, trace reflections, or render pixels. It uses
fixed-point arithmetic and requires numerical-range validation and synthesis
before hardware use.


## v0.4 BVH traversal controller

Added `rtl/nexus3000_bvh_traversal.sv`, an iterative depth-first traversal
controller with a bounded on-chip stack. It requests node metadata from an
external BVH store, skips missed nodes, visits the left child first, defers the
right child on the stack, and emits intersected leaf indices. Stack overflow
is reported explicitly.

The memory and AABB intersection logic remain external interfaces; this module
is the traversal controller, not a complete BVH/ray-tracing pipeline.
Testbench: `tb/tb_nexus3000_bvh_traversal.sv`. GitHub Actions is configured
to compile and run this test on workflow execution.


## v0.5 BVH correctness fix and film pipeline

The BVH controller state enum now uses three bits for its five states, and its
stack-capacity check compares the current occupancy directly with the configured
depth. This corrects an RTL encoding issue found during source review. Simulation
is still required to establish behavior.

The repository root now includes `nexus_film_pipeline.py`, which connects the
CPU reference renderer to FFmpeg MP4 encoding and the cinematic finishing
module (colour grade, glow/bloom-style processing, and an original procedural
stereo score). Example from the repository's `nexus-virtual-cinema-chip`
directory:

```sh
python nexus_film_pipeline.py --out NEXUS_FILM_OUTPUT --width 160 --height 90 --frames 24 --fps 12 --spp 1 --depth 1
```

The resulting `NEXUS_FILM.mp4` is a low-resolution prototype output, not a
Hollywood production master. Rendering cost rises quickly with resolution,
samples per pixel, reflection depth and frame count. The CI workflow includes
a tiny end-to-end smoke test; check the Actions run for its actual result.


## v0.5 triangle intersection unit

Added `rtl/nexus3000_triangle_intersect.sv`, a compact Möller–Trumbore
ray/triangle intersection reference using signed Q8.8 coordinates and outputs
for distance and barycentric coordinates. The companion testbench checks a
front-facing hit and a parallel-ray miss. GitHub Actions is configured to
compile and run this test.

This first implementation uses combinational arithmetic, including division;
its timing, numerical range, edge cases, and FPGA resource use must be measured
before increasing ray-lane count or treating it as a production accelerator.
It does not yet integrate the AABB, BVH, triangle store, material system, or
frame renderer into one hardware pipeline.
