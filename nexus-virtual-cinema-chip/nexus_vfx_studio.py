#!/usr/bin/env python3
"""NEXUS VFX Studio v0.1 — node-graph compositor reference engine.

Builds and validates a deterministic VFX graph manifest. This is an early
software prototype, not a replacement for Blender/Nuke and not a physical
chip installation. Pixel-processing nodes require future renderer adapters.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

NODE_TYPES = {
    "FootageInput": {"inputs": 0, "outputs": ["image"]},
    "ColorGrade": {"inputs": 1, "outputs": ["image"]},
    "Glow": {"inputs": 1, "outputs": ["image"]},
    "ChromaKey": {"inputs": 1, "outputs": ["image", "matte"]},
    "Transform2D": {"inputs": 1, "outputs": ["image"]},
    "CompositeOver": {"inputs": 2, "outputs": ["image"]},
    "FilmGrain": {"inputs": 1, "outputs": ["image"]},
    "Output": {"inputs": 1, "outputs": []},
}

def validate(graph):
    if graph.get("schema") != "nexus.vfx.graph.v1":
        raise ValueError("Unsupported VFX graph schema")
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("nodes and edges must be arrays")
    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id") or not node.get("type"):
            raise ValueError("Every node needs an id and type")
        if node["id"] in by_id:
            raise ValueError(f"Duplicate node id: {node['id']}")
        if node["type"] not in NODE_TYPES:
            raise ValueError(f"Unknown node type: {node['type']}")
        by_id[node["id"]] = node
    incoming = {key: 0 for key in by_id}
    adjacency = {key: [] for key in by_id}
    for edge in edges:
        src, dst = edge.get("from"), edge.get("to")
        if src not in by_id or dst not in by_id:
            raise ValueError(f"Edge references unknown node: {edge}")
        incoming[dst] += 1
        adjacency[src].append(dst)
    for key, node in by_id.items():
        count = incoming[key]
        required = NODE_TYPES[node["type"]]["inputs"]
        if count != required:
            raise ValueError(f"{key} ({node['type']}) expects {required} incoming edges, got {count}")
    # Topological ordering also detects cycles.
    ready = [key for key, count in incoming.items() if count == 0]
    order = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for nxt in adjacency[current]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                ready.append(nxt)
    if len(order) != len(by_id):
        raise ValueError("VFX graph contains a cycle")
    if not any(n["type"] == "Output" for n in nodes):
        raise ValueError("Graph needs at least one Output node")
    return order

def sample_graph():
    return {
        "schema": "nexus.vfx.graph.v1",
        "name": "NEXUS 2090 — cinematic signal composite",
        "description": "Starter node graph; adapters are required for pixel execution.",
        "nodes": [
            {"id": "plate", "type": "FootageInput", "params": {"path": "renders/plate.mp4"}},
            {"id": "grade", "type": "ColorGrade", "params": {"look": "deep-space-gold"}},
            {"id": "glow", "type": "Glow", "params": {"threshold": 0.78, "intensity": 1.4}},
            {"id": "grain", "type": "FilmGrain", "params": {"amount": 0.025}},
            {"id": "out", "type": "Output", "params": {"path": "delivery/vfx_preview.mov"}}
        ],
        "edges": [
            {"from": "plate", "to": "grade"},
            {"from": "grade", "to": "glow"},
            {"from": "glow", "to": "grain"},
            {"from": "grain", "to": "out"}
        ]
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write-sample", help="write starter VFX graph JSON")
    p.add_argument("--validate", help="validate a VFX graph JSON file")
    args = p.parse_args()
    if args.write_sample:
        path = Path(args.write_sample)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sample_graph(), indent=2) + "\n", encoding="utf-8")
        print(f"Sample graph written: {path}")
    if args.validate:
        graph = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        order = validate(graph)
        print("VFX graph valid. Execution order:", " -> ".join(order))
    if not args.write_sample and not args.validate:
        p.print_help()

if __name__ == "__main__":
    main()
