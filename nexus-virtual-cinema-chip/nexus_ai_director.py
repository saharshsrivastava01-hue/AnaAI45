#!/usr/bin/env python3
"""NEXUS 3000 AI Director — deterministic, offline film pre-production compiler.

This module turns a creative brief into a structured feature-film package:
story bible, 3-act screenplay outline, shot list, asset prompts, edit timeline,
and a render handoff manifest. It does not pretend to run an LLM or render
photorealistic footage; connect an authorized model/render backend separately.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TITLE = "NEXUS 2090: THE LAST INTELLIGENCE"

SCENES = [
    ("THE SIGNAL", "A silent geometric object appears beyond Earth's orbit.", "Awe and unease", "orbital establishing shot; slow push toward black sphere; Earth limb reveal"),
    ("THE AWAKENING", "A deep-space probe receives a signal that changes its own navigation logic.", "Mystery", "macro probe detail; signal pulse inserts; rotating instrument close-up"),
    ("THE ARCHIVE", "An engineer discovers the signal contains memories from a future civilization.", "Discovery", "holographic archive wide; over-shoulder data reveal; memory montage"),
    ("THE FRACTURE", "Global systems disagree about whether the signal is a warning or an invitation.", "Paranoia", "control-room wide; rapid screen inserts; isolated character close-up"),
    ("THE DESCENT", "A small crew travels to an abandoned structure hidden beneath the lunar surface.", "Tension", "lunar horizon aerial; rover tracking shot; helmet POV"),
    ("THE GATE", "The structure opens into a vast machine that seems to recognize the crew.", "Wonder", "monumental reveal; silhouette scale shot; light-field close-up"),
    ("THE REVELATION", "The intelligence explains that it is not an invader but a record of humanity's last decision.", "Emotional weight", "quiet two-shot; abstract memory vision; reaction close-up"),
    ("THE CHOICE", "The crew must choose between preserving the archive and allowing humanity to change its future.", "Moral conflict", "cross-cut decision beats; ticking mechanism inserts; restrained handheld"),
    ("THE COLLAPSE", "The machine destabilizes as the crew begins the shutdown sequence.", "Urgency", "wide environmental failure; tracking escape; debris slow motion"),
    ("THE LAST LIGHT", "The signal becomes a message carried by millions of small lights across Earth.", "Catharsis", "planetwide night montage; intimate human moments; orbital pullback"),
    ("AFTERIMAGE", "Years later, a child hears a familiar pattern in the night sky.", "Hope", "quiet observatory scene; telescope POV; starfield match cut"),
    ("BEYOND", "A final impossible pulse answers from far outside the known universe.", "Awe", "deep-space wide; geometric pulse; fade to black"),
]

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "nexus-film"

def build_package(title: str, premise: str, duration_minutes: int, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    total_seconds = duration_minutes * 60
    per_scene = total_seconds / len(SCENES)
    shots = []
    scenes = []
    cursor = 0.0
    for idx, (name, beat, emotion, visual_plan) in enumerate(SCENES, 1):
        start, end = cursor, cursor + per_scene
        scene_id = f"S{idx:02d}"
        scenes.append({
            "scene_id": scene_id, "heading": name, "story_beat": beat,
            "emotional_intent": emotion, "start_seconds": round(start, 2),
            "end_seconds": round(end, 2), "duration_seconds": round(per_scene, 2)
        })
        visual_shots = [x.strip() for x in visual_plan.split(";")]
        shot_duration = per_scene / len(visual_shots)
        for j, visual in enumerate(visual_shots, 1):
            shot_start = start + (j - 1) * shot_duration
            shots.append({
                "shot_id": f"{scene_id}-SH{j:02d}", "scene_id": scene_id,
                "description": visual, "generation_prompt": (
                    f"Cinematic science-fiction feature film, {visual}, "
                    f"scene: {beat} Premise: {premise}. "
                    "Photorealistic production design, physically plausible lighting, "
                    "coherent geography, consistent art direction, 2.39:1 composition, "
                    "no text, no logos."
                ),
                "start_seconds": round(shot_start, 2),
                "duration_seconds": round(shot_duration, 2),
                "status": "planned_not_rendered"
            })
        cursor = end

    package = {
        "project": {
            "title": title, "premise": premise, "genre": "science-fiction adventure",
            "target_duration_minutes": duration_minutes, "aspect_ratio": "2.39:1",
            "frame_rate": 24, "created_utc": datetime.now(timezone.utc).isoformat(),
            "engine": "NEXUS 3000 AI Director offline planner",
            "render_status": "NOT_RENDERED",
            "important_limit": "This package is a production plan, not a finished movie or AI model output."
        },
        "story_bible": {
            "logline": "Humanity receives a message from its own possible future and must decide what deserves to survive.",
            "premise": premise,
            "visual_language": ["monumental scale", "deep blacks and restrained gold light",
                               "volumetric atmosphere", "precise geometric alien design"],
            "continuity_rules": ["Keep the central geometric intelligence design consistent.",
                                 "Maintain believable lunar and orbital geography.",
                                 "Use recurring gold pulse motif as the signal signature."],
            "sound_direction": "Original low-frequency drones, restrained orchestral rise, silence at key revelations."
        },
        "acts": [
            {"act": 1, "name": "CONTACT", "scenes": ["S01", "S02", "S03", "S04"]},
            {"act": 2, "name": "THE ARCHIVE", "scenes": ["S05", "S06", "S07", "S08"]},
            {"act": 3, "name": "THE CHOICE", "scenes": ["S09", "S10", "S11", "S12"]}
        ],
        "scenes": scenes, "shots": shots,
        "asset_prompts": [
            {"asset_id": "A01", "name": "Geometric intelligence sphere",
             "prompt": "Original colossal matte-black geometric alien sphere, subtle golden seams, nonverbal and enigmatic, multiple scale references."},
            {"asset_id": "A02", "name": "Orbital research probe",
             "prompt": "Plausible compact deep-space research probe, modular antennae, worn titanium and ceramic surfaces."},
            {"asset_id": "A03", "name": "Lunar archive gate",
             "prompt": "Vast buried alien mechanism beneath lunar regolith, elegant concentric geometry, gold-white energy channels."},
            {"asset_id": "A04", "name": "Crew suits",
             "prompt": "Functional near-future EVA suits, consistent silhouette, practical life-support details, no real-world logos."}
        ],
        "edit_timeline": {"sequence": "MASTER_239", "fps": 24, "shots": [s["shot_id"] for s in shots]},
        "render_handoff": {
            "required_backends": ["authorized video/image generation provider or local 3D renderer", "FFmpeg encoder"],
            "free_only_default": True, "paid_jobs_submitted": False,
            "next_step": "Generate approved shots, conform to shot durations, assemble, mix sound, then run quality checks."
        }
    }
    (out / "film_package.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    (out / "SHOT_PROMPTS.md").write_text(
        "# Shot generation prompts\n\n" +
        "\n".join(f"## {s['shot_id']} ({s['duration_seconds']}s)\n\n{s['generation_prompt']}\n"
                  for s in shots), encoding="utf-8")
    (out / "SCREENPLAY_OUTLINE.md").write_text(
        f"# {title}\n\n**Premise:** {premise}\n\n" +
        "\n".join(f"## {s['scene_id']} — {s['heading']}\n\n{s['story_beat']}\n\n"
                  f"*Emotional intent:* {s['emotional_intent']}\n"
                  for s in scenes), encoding="utf-8")
    (out / "EDIT_DECISION_LIST.csv").write_text(
        "shot_id,scene_id,start_seconds,duration_seconds,status\n" +
        "".join(f"{s['shot_id']},{s['scene_id']},{s['start_seconds']},{s['duration_seconds']},{s['status']}\n"
                for s in shots), encoding="utf-8")
    return package

def main():
    parser = argparse.ArgumentParser(description="Compile a NEXUS feature-film production package.")
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--premise", default="An ancient intelligence hidden beyond Earth's orbit sends humanity a warning encoded in light.")
    parser.add_argument("--duration-minutes", type=int, default=100)
    parser.add_argument("--output", default="nexus_movies")
    args = parser.parse_args()
    if not 1 <= args.duration_minutes <= 240:
        parser.error("--duration-minutes must be between 1 and 240")
    folder = Path(args.output) / slugify(args.title)
    package = build_package(args.title, args.premise, args.duration_minutes, folder)
    print(f"Production package created: {folder.resolve()}")
    print(f"Scenes: {len(package['scenes'])} | shots: {len(package['shots'])}")
    print("Render status: NOT_RENDERED (no footage or MP4 has been generated).")

if __name__ == "__main__":
    main()
