#!/usr/bin/env python3
"""NEXUS OMEGA Virtual Chip Studio.

Self-contained educational virtual machine: instruction stream, virtual lanes,
register file, bounded memory, deterministic frame kernel and optional FFmpeg
assembly. All lanes are simulated by a host interpreter; lane count is not
physical silicon or extra compute throughput.
"""
from __future__ import annotations
import argparse, json, math, os, platform, random, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class Lane:
    lane_id: int
    state: str = "IDLE"
    retired: int = 0

@dataclass
class Instruction:
    pc: int
    opcode: str
    args: tuple

class VirtualChip:
    def __init__(self, lanes=256, memory_mb=32, workers=4):
        if not 1 <= lanes <= 1_000_000:
            raise ValueError("lanes must be 1..1,000,000 (simulated)")
        if not 1 <= memory_mb <= 512:
            raise ValueError("memory_mb must be 1..512")
        self.lanes = [Lane(i) for i in range(lanes)]
        self.memory = bytearray(memory_mb * 1024 * 1024)
        self.reg = [0] * 32
        self.pc = 0
        self.cycles = 0
        self.retired = 0
        self.state = "POWERED_OFF"
        self.workers = max(1, min(workers, 32, os.cpu_count() or 1))
        self.trace = []

    def boot(self):
        if self.state not in ("POWERED_OFF", "HALTED"):
            raise RuntimeError("VM already booted")
        self.state = "BOOTING"
        self.reg[0] = len(self.lanes)
        self.reg[1] = len(self.memory)
        self.state = "READY"
        self.trace.append({"event":"BOOT","virtual_lanes":len(self.lanes),
                           "virtual_memory_bytes":len(self.memory)})
        return self.snapshot()

    def execute(self, program):
        if self.state != "READY":
            raise RuntimeError("Boot the virtual chip before execution")
        self.state = "RUNNING"
        start = time.perf_counter()
        for ins in program:
            self.pc = ins.pc
            if ins.opcode == "LOADI":
                self.reg[ins.args[0]] = int(ins.args[1])
            elif ins.opcode == "ADD":
                a,b,c = ins.args; self.reg[a] = self.reg[b] + self.reg[c]
            elif ins.opcode == "MUL":
                a,b,c = ins.args; self.reg[a] = self.reg[b] * self.reg[c]
            elif ins.opcode == "XOR":
                a,b,c = ins.args; self.reg[a] = self.reg[b] ^ self.reg[c]
            elif ins.opcode == "STORE8":
                addr, reg = ins.args
                self.memory[int(addr) % len(self.memory)] = int(self.reg[reg]) & 255
            elif ins.opcode == "BARRIER":
                self.cycles += 1
            elif ins.opcode == "HALT":
                self.retired += 1
                break
            else:
                self.state = "FAULT"
                raise ValueError("Unknown opcode: " + ins.opcode)
            self.retired += 1
            self.cycles += 1
        elapsed = time.perf_counter() - start
        self.state = "READY"
        self.trace.append({"event":"PROGRAM_COMPLETE","retired":self.retired,
                           "cycles":self.cycles,"elapsed_seconds":round(elapsed,6)})
        return {"elapsed_seconds":round(elapsed,6),"retired":self.retired,
                "cycles":self.cycles,"registers":self.reg[:8]}

    def run_frame_kernel(self, frame_index, width, height, seed=2090):
        """Render a procedural sci-fi frame using virtual-lane batches."""
        self.state = "RUNNING"
        start = time.perf_counter()
        rng = random.Random(seed + frame_index)
        pixels = bytearray(width * height * 3)
        # A virtual lane owns a deterministic stripe; Python performs the math.
        stripe_count = min(len(self.lanes), height)
        def render_stripe(y0):
            y1 = min(height, y0 + math.ceil(height / stripe_count))
            local = bytearray()
            for y in range(y0, y1):
                for x in range(width):
                    nx = (x - width * .5) / max(1, height)
                    ny = (y - height * .5) / max(1, height)
                    horizon = .58 + .025 * math.sin(frame_index * .12)
                    mountain = abs(math.sin(nx * 11 + math.sin(nx * 3) * 2)) * .12
                    ground = ny > horizon - mountain
                    # Dark atmospheric sky, gold horizon and central alien sphere.
                    d = math.sqrt((nx * 1.5) ** 2 + (ny + .02) ** 2)
                    sphere = d < (.19 + .008 * math.sin(frame_index * .2))
                    glow = max(0.0, 1.0 - abs(ny - horizon) * 9)
                    if sphere:
                        edge = abs(d - .17)
                        pulse = max(0.0, 1.0 - edge * 35)
                        rgb = (int(12 + 90*pulse), int(18 + 48*pulse), int(32 + 10*pulse))
                    elif ground:
                        fissure = abs(math.sin(nx*55 + math.sin(ny*18)*3 + frame_index*.08)) > .985
                        rgb = (int(12 + (100 if fissure else 0)*glow),
                               int(12 + (62 if fissure else 0)*glow), 18)
                    else:
                        star = rng.random() > .9993
                        rgb = (int(4 + 45*glow + (150 if star else 0)),
                               int(7 + 27*glow + (110 if star else 0)),
                               int(18 + 12*glow + (45 if star else 0)))
                    local.extend(rgb)
            return y0, local
        stripe_h = math.ceil(height / stripe_count)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            chunks = list(pool.map(render_stripe, range(0, height, stripe_h)))
        for y0, chunk in chunks:
            offset = y0 * width * 3
            pixels[offset:offset+len(chunk)] = chunk
        self.retired += stripe_count
        self.cycles += stripe_count
        self.state = "READY"
        return pixels, time.perf_counter() - start

    def snapshot(self):
        return {"state":self.state,"virtual_lane_count":len(self.lanes),
                "virtual_registers":len(self.reg),"virtual_memory_bytes":len(self.memory),
                "host_cpu_logical_threads":os.cpu_count() or 1,
                "host_worker_threads":self.workers,"instructions_retired":self.retired,
                "simulated_cycles":self.cycles,"host_platform":platform.platform(),
                "hardware_note":"Virtual lanes are software abstractions. The host CPU executes this interpreter; this is not a physical GPU/TPU or a trillion-fold speedup."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path("NEXUS_VIRTUAL_CHIP_OUTPUT"))
    p.add_argument("--lanes",type=int,default=256)
    p.add_argument("--memory-mb",type=int,default=32)
    p.add_argument("--workers",type=int,default=4)
    p.add_argument("--width",type=int,default=180)
    p.add_argument("--height",type=int,default=320)
    p.add_argument("--frames",type=int,default=24)
    p.add_argument("--fps",type=int,default=12)
    args=p.parse_args()
    if not (16<=args.width<=640 and 16<=args.height<=640 and 1<=args.frames<=120 and 1<=args.fps<=60):
        p.error("Use width/height 16..640, frames 1..120 and fps 1..60")
    args.out.mkdir(parents=True,exist_ok=True)
    chip=VirtualChip(args.lanes,args.memory_mb,args.workers)
    boot=chip.boot()
    # Execute a small real VM instruction program before dispatching frame kernels.
    program=[Instruction(0,"LOADI",(2,2090)),Instruction(1,"LOADI",(3,42)),
             Instruction(2,"MUL",(4,2,3)),Instruction(3,"XOR",(5,4,3)),
             Instruction(4,"STORE8",(0,5)),Instruction(5,"BARRIER",()),
             Instruction(6,"HALT",())]
    vm_result=chip.execute(program)
    frame_times=[]
    for i in range(args.frames):
        pixels,elapsed=chip.run_frame_kernel(i,args.width,args.height)
        frame_times.append(elapsed)
        (args.out/f"frame_{i:05d}.ppm").write_bytes(
            f"P6\n{args.width} {args.height}\n255\n".encode("ascii")+pixels)
        print(f"VCHIP frame {i+1}/{args.frames} retired | {elapsed:.3f}s",flush=True)
    video=None
    if shutil.which("ffmpeg"):
        pattern=str(args.out/"frame_%05d.ppm")
        target=args.out/"NEXUS_OMEGA_VIRTUAL_CHIP.mp4"
        cmd=["ffmpeg","-y","-loglevel","error","-framerate",str(args.fps),
             "-i",pattern,"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(target)]
        proc=subprocess.run(cmd,check=False)
        if proc.returncode==0: video=str(target)
    report={"project":"NEXUS OMEGA Virtual Chip Studio","status":"completed",
            "boot":boot,"vm_program":vm_result,"final_chip_state":chip.snapshot(),
            "frames":args.frames,"resolution":[args.width,args.height],
            "mean_frame_kernel_seconds":round(sum(frame_times)/len(frame_times),6),
            "video":video,"frames_directory":str(args.out.resolve()),
            "truth":"Rendering calculations were executed by this Python virtual machine on the host CPU. Virtual lane count does not multiply physical compute."}
    (args.out/"nexus_virtual_chip_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
