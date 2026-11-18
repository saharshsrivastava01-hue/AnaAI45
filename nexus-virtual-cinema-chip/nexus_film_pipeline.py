#!/usr/bin/env python3
"""NEXUS film pipeline: procedural scene -> CPU-rendered frames -> MP4 -> VFX/audio finish.

This is a free, local-first prototype. It uses Python and FFmpeg; it is not a
Hollywood production renderer and does not claim GPU acceleration or Dolby certification.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RENDERER = ROOT / "nexus_ultra_renderer.py"
FINISHER = ROOT / "nexus_cinematic_vfx_audio.py"

def run(command: list[str]) -> None:
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, check=True)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("NEXUS_FILM_OUTPUT"))
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--height", type=int, default=90)
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--spp", type=int, default=1)
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--preset", choices=("cinema", "sci-fi", "neutral"), default="sci-fi")
    args = parser.parse_args()
    if not (16 <= args.width <= 640 and 16 <= args.height <= 360 and
            1 <= args.frames <= 120 and 1 <= args.fps <= 60 and
            1 <= args.spp <= 16 and 0 <= args.depth <= 5):
        parser.error("render settings exceed the prototype's safe limits")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("FFmpeg and ffprobe must be installed and available on PATH")
    if not RENDERER.is_file() or not FINISHER.is_file():
        parser.error("renderer or finishing module is missing from this project")
    out = args.out.resolve()
    frames_dir = out / "frames"
    out.mkdir(parents=True, exist_ok=True)
    intermediate = out / "NEXUS_ungraded.mp4"
    final = out / "NEXUS_FILM.mp4"
    run([sys.executable, str(RENDERER), "--out", str(frames_dir),
         "--width", str(args.width), "--height", str(args.height),
         "--frames", str(args.frames), "--fps", str(args.fps),
         "--spp", str(args.spp), "--depth", str(args.depth)])
    run(["ffmpeg", "-y", "-framerate", str(args.fps), "-i",
         str(frames_dir / "frame_%05d.ppm"), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", str(intermediate)])
    run([sys.executable, str(FINISHER), "--input", str(intermediate),
         "--output", str(final), "--seconds",
         str(args.frames / args.fps), "--preset", args.preset])
    print(f"FILM_READY={final}")
    print("This is a prototype MP4. Increase resolution, samples and frame count only when compute time permits.")

if __name__ == "__main__":
    main()
