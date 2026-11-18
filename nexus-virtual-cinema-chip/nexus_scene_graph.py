#!/usr/bin/env python3
"""NEXUS-3000 Scene Graph v0.1.

Standard-library JSON schema validator and sample-scene generator.
This describes assets; it does not render them by itself.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

VECTOR3 = (list, tuple)

def vector3(value, label):
    if not isinstance(value, VECTOR3) or len(value) != 3:
        raise ValueError(f"{label} must contain exactly 3 numbers")
    result = [float(x) for x in value]
    if not all(-1_000_000 <= x <= 1_000_000 for x in result):
        raise ValueError(f"{label} contains an out-of-range value")
    return result

def validate_scene(data):
    if not isinstance(data, dict):
        raise ValueError("scene root must be a JSON object")
    if data.get("schema") != "nexus.scene.v1":
        raise ValueError("schema must be 'nexus.scene.v1'")
    camera = data.get("camera", {})
    if not isinstance(camera, dict):
        raise ValueError("camera must be an object")
    vector3(camera.get("position", [0, 2, 7]), "camera.position")
    vector3(camera.get("target", [0, 0, 0]), "camera.target")
    vector3(data.get("light", [4, 5, 6]), "light")
    for key in ("spheres", "planes", "orbiting_spheres"):
        if not isinstance(data.get(key, []), list):
            raise ValueError(f"{key} must be an array")
    for i, obj in enumerate(data.get("spheres", [])):
        if not isinstance(obj, dict):
            raise ValueError(f"spheres[{i}] must be an object")
        vector3(obj.get("center"), f"spheres[{i}].center")
        vector3(obj.get("color"), f"spheres[{i}].color")
        radius = float(obj.get("radius", 0))
        if not 0 < radius <= 100_000:
            raise ValueError(f"spheres[{i}].radius must be positive")
        metallic = float(obj.get("metallic", 0))
        if not 0 <= metallic <= 1:
            raise ValueError(f"spheres[{i}].metallic must be between 0 and 1")
    for i, obj in enumerate(data.get("planes", [])):
        if not isinstance(obj, dict):
            raise ValueError(f"planes[{i}] must be an object")
        float(obj["y"])
        vector3(obj.get("color"), f"planes[{i}].color")
    for i, obj in enumerate(data.get("orbiting_spheres", [])):
        if not isinstance(obj, dict):
            raise ValueError(f"orbiting_spheres[{i}] must be an object")
        if float(obj.get("size", 0.1)) <= 0 or float(obj.get("orbit_radius", 2)) <= 0:
            raise ValueError(f"orbiting_spheres[{i}] size and orbit_radius must be positive")
        vector3(obj.get("color", [0.95, 0.57, 0.12]), f"orbiting_spheres[{i}].color")
    if not any(data.get(k, []) for k in ("spheres", "planes", "orbiting_spheres")):
        raise ValueError("scene must contain at least one renderable object")
    return {"spheres": len(data.get("spheres", [])),
            "planes": len(data.get("planes", [])),
            "orbiting_spheres": len(data.get("orbiting_spheres", []))}

def sample_scene():
    return {
        "schema": "nexus.scene.v1",
        "name": "NEXUS 2090 - Golden Orbital Signal",
        "camera": {"position": [0, 2, 7], "target": [0, 0, 0], "fov_degrees": 38},
        "light": [4.2, 5.0, 6.0],
        "spheres": [
            {"name": "central_artifact", "center": [0, 0, 0], "radius": 1.05,
             "color": [0.035, 0.045, 0.065], "metallic": 0.82},
            {"name": "blue_planet", "center": [-2.3, 0.35, -1], "radius": 0.62,
             "color": [0.06, 0.34, 0.72], "metallic": 0.25},
            {"name": "red_moon", "center": [2.1, 0.15, -1.7], "radius": 0.82,
             "color": [0.48, 0.08, 0.12], "metallic": 0.35}
        ],
        "planes": [{"name": "stage_floor", "y": -1.25, "color": [0.075, 0.085, 0.11]}],
        "orbiting_spheres": [
            {"name": "gold_satellite_a", "size": 0.11, "orbit_radius": 2.0,
             "angular_speed": 0.8, "phase": 0, "height": 0.1,
             "color": [0.95, 0.57, 0.12], "metallic": 0.7}
        ]
    }

def main():
    parser = argparse.ArgumentParser(description="NEXUS Scene Graph validator")
    parser.add_argument("--validate", help="validate a scene JSON file")
    parser.add_argument("--write-sample", help="write a sample scene JSON file")
    args = parser.parse_args()
    if args.write_sample:
        path = Path(args.write_sample)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sample_scene(), indent=2) + "\n", encoding="utf-8")
        print(f"Sample scene written: {path}")
    if args.validate:
        data = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        counts = validate_scene(data)
        print("Scene valid:", json.dumps(counts, sort_keys=True))
    if not args.validate and not args.write_sample:
        parser.print_help()

if __name__ == "__main__":
    main()
