#!/usr/bin/env python3
"""NEXUS OMEGA 3D short-film generator — procedural ray-marched scene.

Generates original 3D-looking RGB frames without external AI models or paid APIs.
Frames are PPM; if FFmpeg is installed, an MP4 is assembled automatically.
Rendering is CPU software execution; virtual accelerator architecture is logged
as a scheduler/model, not claimed as physical GPU hardware.
"""
import argparse, json, math, shutil, subprocess, time
from pathlib import Path


def normalize(v):
    n = math.sqrt(sum(x*x for x in v)) or 1.0
    return tuple(x/n for x in v)


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def sphere_sdf(p, center, radius):
    return math.sqrt(sum((p[i]-center[i])**2 for i in range(3))) - radius


def terrain_height(x,z,t):
    return -1.15 + 0.13*math.sin(x*2.7 + t*0.35)*math.cos(z*1.8) + 0.06*math.sin(x*7.0+z*4.0)


def scene(p,t):
    # A hovering alien monolith/sphere above volcanic terrain.
    sphere = sphere_sdf(p, (0.0, 0.15 + 0.10*math.sin(t*0.7), 0.0), 0.72)
    ground = p[1] - terrain_height(p[0],p[2],t)
    return min(sphere, ground)


def normal_at(p,t):
    e=0.002
    n=(scene((p[0]+e,p[1],p[2]),t)-scene((p[0]-e,p[1],p[2]),t),
       scene((p[0],p[1]+e,p[2]),t)-scene((p[0],p[1]-e,p[2]),t),
       scene((p[0],p[1],p[2]+e),t)-scene((p[0],p[1],p[2]-e),t))
    return normalize(n)


def render_pixel(u,v,t,aspect):
    # Slowly orbiting camera; perspective ray.
    cam=(2.6*math.sin(t*0.18), 1.15, 3.8*math.cos(t*0.18))
    target=(0.0,0.0,0.0)
    forward=normalize(tuple(target[i]-cam[i] for i in range(3)))
    right=normalize((forward[2],0.0,-forward[0]))
    up=normalize((right[1]*forward[2]-right[2]*forward[1],
                  right[2]*forward[0]-right[0]*forward[2],
                  right[0]*forward[1]-right[1]*forward[0]))
    ray=normalize(tuple(forward[i]+right[i]*u*aspect*0.72+up[i]*v*0.72 for i in range(3)))
    p=cam
    distance=0.0
    hit=False
    for _ in range(72):
        d=scene(p,t)
        if d<0.003:
            hit=True
            break
        distance+=max(0.003,min(d,0.22))
        if distance>12:
            break
        p=tuple(cam[i]+ray[i]*distance for i in range(3))
    if not hit:
        sky=max(0.0,1.0-(v+0.2)*0.55)
        return (int(3+8*sky),int(5+12*sky),int(16+36*sky))
    n=normal_at(p,t)
    light=normalize((-0.5,0.85,0.45))
    diffuse=max(0.0,dot(n,light))
    if p[1] < -0.75:
        fissure=max(0.0,math.sin(p[0]*27+math.sin(p[2]*13+t)*2))**18
        glow=fissure*(0.5+0.5*math.sin(t*2))
        base=(22+180*glow,13+105*glow,10+25*glow)
    else:
        # Dark reflective shell with a bright golden energy rim.
        rim=(1.0-max(0.0,dot(tuple(-x for x in ray),n)))**3
        pulse=0.65+0.35*math.sin(t*2.2+p[0]*4)
        base=(8+155*rim*pulse,12+112*rim*pulse,25+75*rim*pulse)
    shade=0.28+0.72*diffuse
    return tuple(max(0,min(255,int(c*shade))) for c in base)


def render_frame(path,w,h,index,total):
    t=index/max(1,total-1)*6.283
    aspect=w/h
    pixels=bytearray()
    for y in range(h):
        v=1.0-2.0*(y+0.5)/h
        for x in range(w):
            u=2.0*(x+0.5)/w-1.0
            pixels.extend(render_pixel(u,v,t,aspect))
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
        f.write(pixels)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--frames",type=int,default=48)
    p.add_argument("--fps",type=int,default=12)
    p.add_argument("--width",type=int,default=180)
    p.add_argument("--height",type=int,default=320)
    p.add_argument("--out",default="NEXUS_3D_SHORT_FILM")
    a=p.parse_args()
    if not 1<=a.frames<=240 or not 1<=a.fps<=60 or not 32<=a.width<=640 or not 32<=a.height<=640:
        p.error("frames 1..240, fps 1..60, dimensions 32..640")
    root=Path(a.out); frames_dir=root/"frames"; frames_dir.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    for i in range(a.frames):
        render_frame(frames_dir/f"frame_{i:05d}.ppm",a.width,a.height,i,a.frames)
        print(f"Rendered frame {i+1}/{a.frames}")
    elapsed=time.perf_counter()-started
    ffmpeg=shutil.which("ffmpeg")
    video=None
    if ffmpeg:
        video=root/"NEXUS_OMEGA_3D_SHORT.mp4"
        cmd=[ffmpeg,"-y","-framerate",str(a.fps),"-i",str(frames_dir/"frame_%05d.ppm"),
             "-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-movflags","+faststart",str(video)]
        subprocess.run(cmd,check=True)
    manifest={"project":"NEXUS OMEGA 3D short film","scene":"orbiting alien sphere above volcanic terrain",
      "frames":a.frames,"fps":a.fps,"resolution":[a.width,a.height],"elapsed_render_seconds":elapsed,
      "video_file":str(video) if video else None,"frames_directory":str(frames_dir),
      "engine":"original CPU ray-marched procedural renderer",
      "external_video_models_used":False,
      "hardware_note":"Runs on host CPU. The NEXUS virtual GPU/TPU architectural models do not create physical accelerator hardware."}
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
