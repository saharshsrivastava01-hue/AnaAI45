#!/usr/bin/env python3
"""NEXUS OMEGA: original 4D-style historical stealth short.

An original hooded-rooftop-assassin inspired scene, not an official Assassin's
Creed production and not using Ubisoft characters, logos, music or assets.
"4D" here means time-varying animation, camera motion, layered parallax and
procedural atmosphere; it is not physical 4D projection or haptics.
Frames are rendered locally as PPM. FFmpeg optionally assembles an MP4.
"""
import argparse, json, math, shutil, subprocess, time
from pathlib import Path


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def smooth(a, b, x):
    q = clamp((x-a)/(b-a))
    return q*q*(3-2*q)


def hash2(x, y):
    n = math.sin(x*127.1+y*311.7)*43758.5453
    return n-math.floor(n)


def scene_pixel(u, v, t, aspect):
    # Animated cinematic camera drift and layered old-city skyline.
    drift = 0.035*math.sin(t*0.7)
    u += drift
    horizon = -0.28 + 0.018*math.sin(t*0.4)
    sky = clamp((v-horizon+0.35)/1.2)
    col = [7+12*sky, 12+15*sky, 27+28*sky]

    # Moon and atmospheric halo.
    mx, my = 0.58+0.025*math.sin(t*0.25), 0.48
    mr = math.sqrt((u-mx)**2+(v-my)**2)
    halo = math.exp(-mr*12)*0.20
    moon = 1.0-smooth(0.045,0.052,mr)
    for i,c in enumerate((80,130,185)):
        col[i] += c*halo + c*0.7*moon

    # Distant city towers, arches and warm windows.
    for layer in range(3):
        parallax = (layer+1)*0.012
        x = u + parallax*math.sin(t*0.35+layer)
        base = horizon - layer*0.07
        cell = math.floor((x+1.2)*(10+layer*5))
        local = (x+1.2)*(10+layer*5)-cell
        width = 0.55+0.35*hash2(cell,layer)
        height = 0.12+0.22*hash2(cell,layer+9)
        top = base+height
        building = (local < width) and (v < top) and (v > base-0.35)
        if building:
            shade = 0.55+0.15*hash2(cell,layer+4)
            col[0] = col[0]*0.2+12*shade
            col[1] = col[1]*0.2+17*shade
            col[2] = col[2]*0.2+28*shade
            wx = int(local*17)
            wy = int((top-v)*27)
            window = (wx%4==1 and wy%5==2 and hash2(cell+wx,wy)>0.3)
            if window:
                col[0]+=92; col[1]+=48; col[2]+=13

    # Rooftop foreground.
    roofline = -0.56 + 0.035*math.sin(u*8+t*0.3)
    if v < roofline:
        col = [13,13,20]
        edge = math.exp(-abs(v-roofline)*95)
        col[0]+=70*edge; col[1]+=39*edge; col[2]+=18*edge

    # Original hooded figure silhouette on a rooftop, animated cloak.
    ax = -0.18+0.025*math.sin(t*0.9)
    ay = -0.17
    head = math.sqrt(((u-ax)/0.085)**2+((v-ay)/0.105)**2) < 1
    torso_x = abs(u-ax-0.015*math.sin(t*1.4)*(v+0.2))
    torso = torso_x < (0.105+0.08*clamp((-v-0.05))) and -0.53 < v < -0.19
    cloak = (abs(u-(ax-0.03)) < (0.09+0.14*clamp((-v-0.20))*abs(math.sin(t*1.2)))
             and -0.55 < v < -0.28)
    if head or torso or cloak:
        col = [5,6,11]
        rim = math.exp(-abs(u-(ax+0.09))*35)
        col[0]+=20*rim; col[1]+=25*rim; col[2]+=43*rim

    # Animated hidden blade glint and drifting embers.
    blade_y = -0.31+0.012*math.sin(t*2)
    blade = abs(v-blade_y)<0.006 and ax+0.09<u<ax+0.34
    if blade:
        col = [190,205,220]
    for i in range(22):
        ex = ((hash2(i,3)+0.035*t*(0.3+hash2(i,4)))%1.0)*2-1
        ey = ((hash2(i,5)+0.09*t*(0.5+hash2(i,6)))%1.0)*1.6-0.8
        d = math.sqrt((u-ex)**2+(v-ey)**2)
        ember = math.exp(-d*240)*0.8
        col[0]+=255*ember; col[1]+=95*ember; col[2]+=18*ember

    # Subtle film grain and vignette.
    grain = (hash2(int((u+1)*180),int((v+1)*320)+int(t*12))-0.5)*5
    vignette = clamp(1-0.28*(u*u+v*v))
    return tuple(int(clamp((c+grain)*vignette/255)*255) for c in col)


def render_frame(path, width, height, frame, total):
    t = frame/max(1,total-1)*10.0
    aspect = width/height
    buf = bytearray()
    for y in range(height):
        v = 1-2*(y+0.5)/height
        for x in range(width):
            u = 2*(x+0.5)/width-1
            buf.extend(scene_pixel(u,v,t,aspect))
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode())
        f.write(buf)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--frames",type=int,default=120)
    p.add_argument("--fps",type=int,default=12)
    p.add_argument("--width",type=int,default=180)
    p.add_argument("--height",type=int,default=320)
    p.add_argument("--out",default="NEXUS_ASSASSIN_STYLE_4D_SHORT")
    a=p.parse_args()
    if not 1<=a.frames<=360 or not 1<=a.fps<=60 or not 32<=a.width<=640 or not 32<=a.height<=640:
        p.error("frames 1..360, fps 1..60, dimensions 32..640")
    root=Path(a.out); frames=root/"frames"; frames.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    for i in range(a.frames):
        render_frame(frames/f"frame_{i:05d}.ppm",a.width,a.height,i,a.frames)
        print(f"Rendered frame {i+1}/{a.frames}",flush=True)
    elapsed=time.perf_counter()-started
    ffmpeg=shutil.which("ffmpeg")
    mp4=None
    if ffmpeg:
        mp4=root/"NEXUS_STEALTH_4D_SHORT.mp4"
        subprocess.run([ffmpeg,"-y","-framerate",str(a.fps),"-i",str(frames/"frame_%05d.ppm"),
          "-c:v","libx264","-pix_fmt","yuv420p","-crf","19","-movflags","+faststart",str(mp4)],check=True)
    manifest={"title":"NEXUS: Shadow Above the Old City","style":"original historical stealth fantasy",
      "duration_seconds":a.frames/a.fps,"frames":a.frames,"fps":a.fps,
      "resolution":[a.width,a.height],"render_seconds":elapsed,
      "frames_directory":str(frames),"mp4":str(mp4) if mp4 else None,
      "4d_definition":"time-based animation, camera drift, parallax and animated atmosphere",
      "assets":"original procedural graphics; no Ubisoft characters, logos, music or extracted assets",
      "render_backend":"CPU procedural renderer; no external video AI"}
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
