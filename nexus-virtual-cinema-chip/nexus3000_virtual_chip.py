#!/usr/bin/env python3
"""NEXUS-3000 Virtual SoC Fabric v0.3.

Integrated software control-plane model for the NEXUS hardware roadmap.
All capacities/lanes are logical scheduler budgets, not physical resources.
"""
from __future__ import annotations
import argparse, json
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass(frozen=True)
class Engine:
    name: str
    domain: str
    lanes: int
    memory_gb: float
    capabilities: tuple[str, ...]

ENGINES = (
    Engine("VTPU","AI and tensor planning",4096,64,("inference","planning","matrix_dot","upscaling")),
    Engine("VGPU","graphics and raster",8192,128,("raster","materials","particles","geometry_shading")),
    Engine("VRPU","ray and path tracing",4096,96,("raytrace","shadows","reflections","global_illumination")),
    Engine("VFXU","effects and compositing",2048,64,("compositing","denoise","color","glow","keying")),
    Engine("VGEU","geometry",2048,48,("mesh","procedural","transforms","subdivision")),
    Engine("VAU","audio and spatial sound",512,16,("mixing","synthesis","spatial_audio","mastering")),
    Engine("VMEDIA","encode and delivery",512,32,("encode","mux","subtitles","qc")),
    Engine("VIO","asset and data movement",256,64,("ingest","cache","manifest","streaming")),
    Engine("VDMA","virtual DMA scheduling",256,32,("copy","transfer","framebuffer")),
    Engine("VNoC","virtual network-on-chip",128,16,("routing","arbitration","telemetry")),
    Engine("VSEC","safety and isolation",64,8,("validation","limits","audit")),
)
TASKS = (
 ("creative_plan","VTPU","planning",[]),
 ("asset_ingest","VIO","ingest",["creative_plan"]),
 ("geometry_build","VGEU","procedural",["asset_ingest"]),
 ("material_shading","VGPU","materials",["geometry_build"]),
 ("lighting_simulation","VRPU","raytrace",["material_shading"]),
 ("frame_render","VGPU","raster",["lighting_simulation"]),
 ("ray_effects","VRPU","reflections",["frame_render"]),
 ("vfx_composite","VFXU","compositing",["ray_effects"]),
 ("audio_score","VAU","synthesis",["creative_plan"]),
 ("audio_mix","VAU","mixing",["audio_score"]),
 ("frame_transfer","VDMA","framebuffer",["vfx_composite"]),
 ("media_encode","VMEDIA","encode",["frame_transfer","audio_mix"]),
 ("quality_control","VSEC","validation",["media_encode"]),
 ("delivery","VMEDIA","qc",["quality_control"]),
)

def topology():
    return {
      "chip":"NEXUS-3000","version":"0.3",
      "execution_model":"integrated virtual SoC control plane",
      "physical_hardware":False,
      "fabric":{"name":"VNoC","topology":"hierarchical mesh","virtual_links":128,
                "features":["capability-aware routing","priority arbitration","telemetry model"]},
      "memory":{"name":"VMEM","virtual_capacity_gb":512,
                "tiers":["L0 register-file model","L1 scratchpad model","L2 scene cache model","framebuffer model","asset archive"]},
      "control":{"command_queue":"VQ","dma":"VDMA","safety":"VSEC",
                 "max_parallel_jobs":8,"retry_limit":2},
      "hardware_rtl_blocks":[
        "hardware/rtl/nexus3000_compute_tile.sv",
        "hardware/rtl/nexus3000_tensor_dot.sv",
        "hardware/rtl/nexus3000_scratchpad.sv",
        "hardware/rtl/nexus3000_command_unit.sv"],
      "engines":[asdict(e) for e in ENGINES],
      "pipeline":[{"stage":s,"engine":e,"capability":c,"depends_on":d} for s,e,c,d in TASKS],
      "honesty":{"physical_accelerators":0,"measured_throughput":False,
        "note":"Lane counts and memory capacities are virtual scheduling abstractions."}
    }

def build_plan():
    by_name={e.name:e for e in ENGINES}
    result=[]
    for i,(stage,engine,cap,depends) in enumerate(TASKS,1):
        if cap not in by_name[engine].capabilities:
            raise ValueError(f"Unsupported capability {engine}:{cap}")
        result.append({"sequence":i,"stage":stage,"engine":engine,
          "capability":cap,"depends_on":depends,
          "virtual_lane_budget":min(by_name[engine].lanes,256),
          "status":"planned_not_executed"})
    return {"chip":"NEXUS-3000","version":"0.3","mode":"virtual_simulation",
            "physical_accelerators":0,"stages":result}

def validate_plan(plan):
    seen=set()
    for item in plan["stages"]:
        if any(dep not in seen for dep in item["depends_on"]):
            raise ValueError("Pipeline dependency must refer to an earlier stage")
        seen.add(item["stage"])
    return True

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group()
    g.add_argument("--topology",action="store_true")
    g.add_argument("--plan",action="store_true")
    p.add_argument("--write")
    a=p.parse_args()
    result=topology() if a.topology else build_plan()
    if a.plan: validate_plan(result)
    rendered=json.dumps(result,indent=2)
    if a.write:
        path=Path(a.write); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(rendered+"\\n",encoding="utf-8")
        print(f"Wrote {path}")
    else: print(rendered)

if __name__=="__main__": main()
