# NEXUS-3000 Virtual Cinema Chip — From-Scratch Design Specification

Revision 0.1.0 | Architecture baseline | Not taped out or silicon-validated

## Product definition
NEXUS-3000 is a software-defined cinematic-compute platform. This first revision is a synthesizable SystemVerilog control-plane prototype that can coordinate real compute engines later. VGPU, VTPU and VFXU are logical accelerator domains; this prototype does not contain a GPU, tensor array, HBM or physical chip.

## Block architecture
- Host ingress: opcode, descriptor, valid/ready handshake.
- VNoC: deterministic routing and single-issue dispatch.
- VTPU: screenplay/prompt planning software adapter.
- VGPU: procedural scene rendering through Blender adapter.
- VFXU: compositing adapter.
- VRPU: image transforms; future local adapter.
- VMEDIA: timeline and MP4 encoding through FFmpeg.
- VMEM: project and asset state through SQLite/filesystem.
- Telemetry: accepted, completed and error counters.

## Command protocol
A command is accepted on a rising edge when cmd_valid and cmd_ready are both high. Opcodes 0–6 select VTPU, VGPU, VFXU, VRPU, VMEDIA, VMEM and VNoC. The selected engine receives a one-cycle start pulse, opcode and 32-bit descriptor token. The engine returns done or error. Only one command is in flight in this revision; command FIFOs, multiple issue slots and DMA descriptors are future work.

## Physical implementation plan
1. Simulate with Verilator or Icarus Verilog.
2. Lint and synthesize with Yosys or a vendor FPGA tool.
3. Map the control plane to a supported FPGA and measure clock, utilization and power.
4. Integrate independently verified accelerator IP through documented bus and DMA interfaces.
5. Consider ASIC only after PPA studies, memory/compiler design, verification closure, DFT, floorplanning, timing closure and foundry selection.

## Engineering constraints
- Never execute arbitrary shell commands from hardware descriptors.
- Validate descriptor addresses and lengths before any future DMA.
- Add CDC synchronizers or asynchronous FIFOs for clock-domain crossings.
- Verify reset behavior in every clock domain.
- Make no performance, energy, trillion-lane or 6D claims without measurements.

## Acceptance gates
RTL parses; self-checking route/handshake tests pass; lint has no unexplained latches; synthesis and timing reports are reviewed; FPGA results record board, clock, utilization and measured throughput.

## Honest current capability
This is an architecture and control-plane starter, not a movie renderer. Actual frames require installed local render engines; AI footage requires a connected model provider or local model. The Python backend is the local orchestration plane.
