"""NEXUS OMEGA: beyond-limit research engines integrated with the existing chip build.

Research architecture and workload router only. Experimental engines are
virtual descriptors, not physical devices or executable accelerators.
"""
from dataclasses import asdict, dataclass
from typing import Iterable
from nexus_horizon_runtime import DeviceInfo, discover_devices

@dataclass(frozen=True)
class ResearchEngine:
    code: str
    principle: str
    best_for: tuple[str, ...]
    maturity: str
    executable_today: bool
    physical_device_required: str
    limitation: str

ENGINES = (
 ResearchEngine("NOVA-OPT", "photonic matrix operations and optical interconnect",
  ("dense_matmul", "optical_link"), "experimental research", False, "photonic accelerator",
  "precision, optical-electrical conversion, calibration and memory feed"),
 ResearchEngine("MEM-CORE-X", "compute-near/in-memory",
  ("embedding_lookup", "sparse_attention", "memory_bound"), "research/prototype dependent", False, "compute-in-memory device",
  "device variation, endurance, precision and data conversion"),
 ResearchEngine("NEXUS-NEURO", "event-driven neuromorphic processing",
  ("event_stream", "sparse_inference"), "research/prototype dependent", False, "neuromorphic processor",
  "mapping, training compatibility and workload dependence"),
 ResearchEngine("REV-CORE", "reversible logic",
  ("low_energy_logic",), "early research", False, "reversible logic hardware",
  "clocking, fan-out, error control and practical circuit overhead"),
 ResearchEngine("STOCH-CORE", "probabilistic/approximate computation",
  ("sampling", "approximate_optimization"), "research", False, "specialized probabilistic hardware",
  "error tolerance and reproducibility"),
 ResearchEngine("QUANTUM-BRIDGE", "external quantum processor interface",
  ("quantum_circuit",), "provider-specific", False, "accessible quantum provider",
  "noise, queue time, encoding, error correction and narrow applicability"),
 ResearchEngine("3D-HYPERFABRIC", "chiplet/3D stacked heterogeneous interconnect",
  ("multi_engine", "memory_locality"), "industry research and deployment", False, "3D packaged hardware",
  "thermal density, yield, packaging and test"),
 ResearchEngine("THERMO-SHIELD", "thermal/power-aware runtime policy",
  ("all",), "software policy prototype", True, "host telemetry and power controls",
  "software can schedule around limits but cannot remove physical heat")
)

def research_catalog() -> dict:
 return {"architecture":"NEXUS OMEGA existing chip build",
         "status":"research_descriptors_not_hardware",
         "physical_future_engines_present":False,
         "engines":[asdict(x) for x in ENGINES]}

def route_research_workload(workload: str, devices: Iterable[DeviceInfo] | None = None) -> dict:
 """Recommend a research direction and separately list actually detected devices."""
 matches=[e for e in ENGINES if workload in e.best_for or "all" in e.best_for]
 detected=list(devices if devices is not None else discover_devices())
 return {"workload":workload,
         "research_candidates":[e.code for e in matches],
         "executable_research_candidates":[e.code for e in matches if e.executable_today],
         "detected_hardware":[{"id":d.device_id,"kind":d.kind,"name":d.name,
                               "available":d.available,"backend":d.execution_backend}
                              for d in detected if d.available],
         "status":"recommendation_only",
         "million_x_speedup_verified":False}

if __name__=="__main__":
 import json
 print(json.dumps(research_catalog(),indent=2))
