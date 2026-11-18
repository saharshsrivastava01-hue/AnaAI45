#!/usr/bin/env python3
"""NEXUS Immersive Media Pipeline v0.1.

Creates and validates an honest production manifest for CGI/VFX, large-format
image delivery, spatial-audio metadata, and stereoscopic/immersive targets.
It does not encode Dolby/IMAX-certified deliverables or create true 4D effects.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SCHEMA = "nexus.immersive.pipeline.v1"
VIDEO_PROFILES = {
    "preview_4k": {"width": 3840, "height": 2160, "fps": 24, "stereo": False},
    "large_format_4k": {"width": 4096, "height": 2160, "fps": 24, "stereo": False},
    "stereo_3d_4k": {"width": 3840, "height": 2160, "fps": 24, "stereo": True}
}
AUDIO_PROFILES = {
    "stereo": {"channels": 2, "layout": "2.0"},
    "surround_5_1": {"channels": 6, "layout": "5.1"},
    "surround_7_1": {"channels": 8, "layout": "7.1"},
    "immersive_object_audio": {"channels": None, "layout": "object_based_metadata_required"}
}
STAGES = [
    "asset_ingest", "geometry_and_cgi", "materials_and_lighting",
    "raytrace_render", "vfx_composite", "stereoscopic_review",
    "spatial_audio_mix", "color_and_mastering", "quality_control", "delivery"
]

def build_manifest(name, video, audio):
    if video not in VIDEO_PROFILES:
        raise ValueError(f"Unknown video profile: {video}")
    if audio not in AUDIO_PROFILES:
        raise ValueError(f"Unknown audio profile: {audio}")
    return {
        "schema": SCHEMA,
        "project": name,
        "status": "specification_only_not_rendered",
        "video": {**VIDEO_PROFILES[video], "profile": video,
                  "certification": "not_implied"},
        "audio": {**AUDIO_PROFILES[audio], "profile": audio,
                  "dolby_atmos_authoring": "requires licensed tools and compatible monitoring"},
        "immersive_targets": {
            "large_format": "delivery target only; venue-specific technical specification required",
            "stereoscopic_3d": "requires left/right camera render and stereo QC",
            "4d": "physical motion, wind, scent, water and seat effects require venue hardware; not encoded as ordinary video",
            "hdr": "requires defined transfer function, color primaries, mastering display and metadata"
        },
        "pipeline": [{"sequence": i+1, "stage": stage, "state": "planned"}
                     for i, stage in enumerate(STAGES)],
        "render_policy": {
            "resolution_is_not_quality_guarantee": True,
            "no_fake_certification": True,
            "test_low_resolution_before_final": True,
            "preserve_linear_master_and_provenance": True
        }
    }

def validate(manifest):
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Invalid immersive pipeline schema")
    video = manifest.get("video", {})
    if video.get("width", 0) < 16 or video.get("height", 0) < 16:
        raise ValueError("Invalid video dimensions")
    if video.get("fps", 0) <= 0:
        raise ValueError("Frame rate must be positive")
    pipeline = manifest.get("pipeline")
    if not isinstance(pipeline, list) or not pipeline:
        raise ValueError("Pipeline stages are missing")
    seq = [x.get("sequence") for x in pipeline]
    if seq != list(range(1, len(seq)+1)):
        raise ValueError("Pipeline sequence numbers must be contiguous")
    return {"project": manifest.get("project"), "stages": len(pipeline),
            "video": f'{video["width"]}x{video["height"]}@{video["fps"]}',
            "audio_profile": manifest.get("audio", {}).get("profile")}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="NEXUS 2090")
    p.add_argument("--video", choices=VIDEO_PROFILES, default="preview_4k")
    p.add_argument("--audio", choices=AUDIO_PROFILES, default="surround_7_1")
    p.add_argument("--out", default="NEXUS_IMMERSIVE_PIPELINE.json")
    p.add_argument("--validate", help="validate an existing pipeline manifest")
    a=p.parse_args()
    if a.validate:
        data=json.loads(Path(a.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate(data),indent=2))
    else:
        data=build_manifest(a.name,a.video,a.audio)
        out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
        print(f"Pipeline manifest written: {out}")
        print(json.dumps(validate(data),indent=2))

if __name__=="__main__":
    main()
