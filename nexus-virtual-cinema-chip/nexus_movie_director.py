#!/usr/bin/env python3
"""NEXUS Movie Director: offline short-film planner for the virtual cinema chip.

Creates a structured vertical-short production plan, timed hook/caption beats,
shot prompts, and an SRT subtitle file. It does not call an LLM or generate
photorealistic footage; the existing renderer remains a procedural CPU renderer.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

GENRES = {
    "sci-fi": {
        "world": "a silent orbital megastructure above a storm-lit planet",
        "visual": "vast scale, metallic silhouettes, amber energy and deep-space haze",
        "sound": "low cinematic drone, rising pulse, restrained impact accents",
    },
    "adventure": {
        "world": "an unexplored mountain pass beneath a strange golden sky",
        "visual": "dramatic ridgelines, fast reveals, dust and warm backlight",
        "sound": "driving percussion, wind, rising orchestral texture",
    },
    "fantasy": {
        "world": "an ancient floating citadel surrounded by luminous clouds",
        "visual": "mysterious architecture, glowing particles and rich atmospheric depth",
        "sound": "mystical textures, deep drums and a memorable melodic motif",
    },
    "sports": {
        "world": "a futuristic arena carved into a vast desert landscape",
        "visual": "dynamic wide reveals, close action details and energetic motion",
        "sound": "rhythmic impacts, crowd energy and a fast musical build",
    },
}

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "nexus-short"

def build_plan(title: str, genre: str, duration: int, platform: str) -> dict:
    if genre not in GENRES:
        raise ValueError(f"Unsupported genre: {genre}")
    if not 15 <= duration <= 90:
        raise ValueError("duration must be between 15 and 90 seconds")
    if platform not in {"youtube-shorts", "instagram-reels", "tiktok"}:
        raise ValueError("unsupported platform")
    world = GENRES[genre]
    # Pacing is deliberately front-loaded; timing scales with selected duration.
    beats = [
        (0.00, 0.08, "HOOK", "What if this world was never meant to be found?", "Extreme visual reveal; open on motion, not a logo."),
        (0.08, 0.24, "MYSTERY", "Something is waking beneath the horizon.", "Reveal one impossible detail; hold back the explanation."),
        (0.24, 0.48, "ESCALATION", "Every step brings the signal closer.", "Three escalating visual beats with hard cuts on sound."),
        (0.48, 0.72, "PAYOFF", "Then the entire sky begins to change.", "Largest scale reveal; strongest light and motion contrast."),
        (0.72, 0.90, "TWIST", "The signal was coming from behind them.", "Reverse the visual expectation; make the final reveal readable."),
        (0.90, 1.00, "LOOP", "Watch the opening again.", "End on a composition that visually connects to the first frame."),
    ]
    scenes = []
    for i, (start, end, name, caption, direction) in enumerate(beats, 1):
        scenes.append({
            "shot": i,
            "beat": name,
            "start_seconds": round(start * duration, 2),
            "end_seconds": round(end * duration, 2),
            "caption": caption,
            "director_note": direction,
            "visual_prompt": f"{world}; {world['visual'] if False else GENRES[genre]['visual']}; {direction} Cinematic, coherent geography, strong silhouette, no text or logos.",
            "sound_direction": GENRES[genre]["sound"],
        })
    return {
        "project_title": title,
        "project_slug": slugify(title),
        "platform": platform,
        "aspect_ratio": "9:16",
        "target_duration_seconds": duration,
        "genre": genre,
        "creative_world": world["world"],
        "creative_goal": "Earn attention with an immediate visual question, escalate clearly, deliver a payoff, and create a natural loop. Virality is not guaranteed.",
        "retention_design": {
            "first_frame_rule": "Start with the most intriguing moving image; no intro card.",
            "caption_rule": "One short readable thought at a time; keep important action unobstructed.",
            "edit_rule": "Change shot scale or visual information every few seconds; cut on sound accents.",
            "loop_rule": "Match the final image or motion direction to the opening.",
        },
        "shots": scenes,
        "publishing_checklist": [
            "Verify music and sound-effect licences before publishing.",
            "Check every caption on a phone-sized screen.",
            "Export 1080x1920 only after a low-resolution preview is approved.",
            "Review the first two seconds without sound and with sound.",
            "Use an accurate title and description; do not use misleading engagement bait.",
            "Check platform music, disclosure and synthetic-media rules.",
        ],
    }

def write_srt(plan: dict, path: Path) -> None:
    def stamp(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    lines = []
    for index, shot in enumerate(plan["shots"], 1):
        lines += [str(index), f"{stamp(shot['start_seconds'])} --> {stamp(shot['end_seconds'])}", shot["caption"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="NEXUS: The Signal")
    parser.add_argument("--genre", choices=sorted(GENRES), default="sci-fi")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--platform", choices=("youtube-shorts", "instagram-reels", "tiktok"), default="youtube-shorts")
    parser.add_argument("--out", type=Path, default=Path("NEXUS_MOVIE_PROJECT"))
    args = parser.parse_args()
    plan = build_plan(args.title, args.genre, args.duration, args.platform)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "production_plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "shot_prompts.txt").write_text("\n\n".join(
        f"SHOT {s['shot']} — {s['beat']} ({s['start_seconds']}–{s['end_seconds']}s)\n{s['visual_prompt']}"
        for s in plan["shots"]), encoding="utf-8")
    write_srt(plan, args.out / "captions.srt")
    print(f"PROJECT_READY={args.out.resolve()}")
    print("Created production_plan.json, shot_prompts.txt, captions.srt")
    print("This is an offline planning stage; it does not generate AI footage or guarantee virality.")

if __name__ == "__main__":
    main()
