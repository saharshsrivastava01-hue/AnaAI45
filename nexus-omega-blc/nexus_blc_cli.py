"""CLI for NEXUS OMEGA BLC analytical research simulator."""
import argparse, json
from pathlib import Path
from nexus_blc import BLCFabric, Workload, WorkloadKind, demo_workloads

def main():
    p = argparse.ArgumentParser(description="NEXUS OMEGA BLC — analytical simulator")
    p.add_argument("--output", default="nexus_blc_report.json")
    p.add_argument("--demo", action="store_true", help="run the built-in workload suite")
    args = p.parse_args()
    report = BLCFabric().report(demo_workloads())
    out = Path(args.output)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written: {out.resolve()}")
    print("Status: SIMULATION_ONLY; illustrative model values, not hardware measurements.")
    for row in report["results"]:
        print(f'{row["workload"]}: {row["recommended"]}')
if __name__ == "__main__": main()
