#!/usr/bin/env python3
"""NEXUS cinematic finishing pipeline.

CPU/FFmpeg post-production: glow, bloom, chromatic aberration, vignette,
film grain, sharpening, cinematic grade and an original procedural score.
Virtual GPU/TPU names describe scheduler lanes only; this module does not
emulate physical accelerators or claim Dolby certification.
"""
from __future__ import annotations
import argparse, json, math, random, shutil, subprocess, sys, wave
from pathlib import Path
from array import array

def require_ffmpeg():
    for exe in ("ffmpeg", "ffprobe"):
        if not shutil.which(exe):
            raise SystemExit(f"Missing {exe}. Install FFmpeg and add it to PATH.")

def synthesize_score(path: Path, seconds: float, rate: int = 48000):
    """Create an original, royalty-free-by-authorship procedural sci-fi score."""
    total = max(1, int(seconds * rate))
    # D-minor / suspended cinematic motif, slow pad + pulse + sub-bass.
    chord_sets = [(146.83, 174.61, 220.00), (130.81, 164.81, 196.00),
                  (110.00, 146.83, 174.61), (123.47, 146.83, 185.00)]
    rng = random.Random(2090)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(rate)
        chunk = 4096
        for start in range(0, total, chunk):
            frames = min(chunk, total-start)
            out = array("h")
            for j in range(frames):
                t = (start+j)/rate
                chord = chord_sets[int(t//8) % len(chord_sets)]
                fade = min(1.0, t/2.5, max(0.0, (seconds-t)/3.0))
                pad = sum(math.sin(2*math.pi*f*t + 0.18*math.sin(2*math.pi*0.11*t))
                          for f in chord)/3
                bass = math.sin(2*math.pi*(chord[0]/2)*t) * (0.5+0.5*math.sin(2*math.pi*0.08*t))
                pulse_env = max(0.0, math.sin(math.pi*((t*1.5) % 1)))**5
                pulse = math.sin(2*math.pi*(chord[1]*2)*t)*pulse_env*0.16
                shimmer = math.sin(2*math.pi*(chord[2]*4)*t + math.sin(t*0.7))*0.07
                sample = (0.24*pad + 0.20*bass + pulse + shimmer)*fade
                # Gentle stereo width via a slow phase offset.
                left = max(-1.0, min(1.0, sample))
                right = max(-1.0, min(1.0, sample*0.94 + 0.025*math.sin(2*math.pi*0.17*t)))
                out.append(int(left*26000)); out.append(int(right*26000))
            wf.writeframesraw(out.tobytes())

def build_filter(preset: str):
    # Filtergraph uses only common FFmpeg filters; no Dolby codec/certification implied.
    grade = {
      "cinema": "eq=contrast=1.16:saturation=1.18:brightness=-0.015,colorbalance=rs=0.035:gs=0.005:bs=-0.025",
      "sci-fi": "eq=contrast=1.22:saturation=1.28:brightness=-0.025,colorbalance=rs=-0.025:gs=0.015:bs=0.055",
      "neutral": "eq=contrast=1.05:saturation=1.05"
    }[preset]
    return (f"split=2[base][bloom];"
            f"[bloom]gblur=sigma=18:steps=2,eq=brightness=0.10:contrast=1.15[glow];"
            f"[base][glow]blend=all_mode=screen:all_opacity=0.28,"
            f"{grade},unsharp=5:5:0.55:3:3:0.20,"
            f"vignette=PI/5,noise=alls=3:allf=t+u,format=yuv420p[outv]")

def render(source: Path, output: Path, score: Path, preset: str, music_gain: float):
    require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg","-y","-i",str(source),"-i",str(score),
           "-filter_complex",f"[0:v]{build_filter(preset)}",
           "-map","[outv]","-map","1:a:0","-c:v","libx264","-preset","medium",
           "-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","256k",
           "-af",f"loudnorm=I=-16:TP=-1.5:LRA=11,volume={music_gain}",
           "-shortest","-movflags","+faststart",str(output)]
    subprocess.run(cmd, check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, help="Source MP4; omit to render a generated test clip")
    p.add_argument("--output", type=Path, default=Path("nexus-vfx-output/NEXUS_2090_CINEMATIC.mp4"))
    p.add_argument("--seconds", type=float, default=12.0)
    p.add_argument("--preset", choices=["cinema","sci-fi","neutral"], default="sci-fi")
    p.add_argument("--music-gain", type=float, default=0.85)
    p.add_argument("--flow-export", type=Path, help="Optional Google Flow Takeout/export folder")
    args=p.parse_args()
    require_ffmpeg()
    source=args.input
    if source is None:
        source=Path("nexus-vfx-output/source.mp4")
        source.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i",
          "color=c=0x050817:s=1280x720:r=24:d="+str(args.seconds),
          "-vf","drawbox=x='iw/2-2':y=0:w=4:h=ih:color=0x35d9ff@0.7:t=fill,format=yuv420p",
          "-c:v","libx264","-pix_fmt","yuv420p",str(source)],check=True)
    if args.flow_export:
        media=[]
        for f in args.flow_export.rglob("*"):
            if f.suffix.lower() in {".mp4",".mov",".wav",".mp3",".jpg",".png"}:
                media.append(str(f))
        (args.output.parent/"google_flow_assets.json").write_text(
            json.dumps({"source":"Google Flow export","assets":media},indent=2))
        print(f"Indexed {len(media)} Flow-exported media assets.")
    score=args.output.with_name("NEXUS_ORIGINAL_SCI_FI_SCORE.wav")
    # Use source duration when possible; --seconds is fallback.
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
       "-of","default=noprint_wrappers=1:nokey=1",str(source)],capture_output=True,text=True,check=True)
    duration=float(probe.stdout.strip() or args.seconds)
    synthesize_score(score,duration)
    render(source,args.output,score,args.preset,args.music_gain)
    print(json.dumps({"video":str(args.output),"score":str(score),"duration_seconds":duration,
      "preset":args.preset,"audio":"original procedural stereo score","status":"rendered"},indent=2))

if __name__=="__main__": main()
