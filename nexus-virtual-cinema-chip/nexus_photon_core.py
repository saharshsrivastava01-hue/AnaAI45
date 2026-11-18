#!/usr/bin/env python3
"""NEXUS Photon Core v0.1 — independent educational ray-tracing renderer.

Pure Python, standard library only. Writes PPM frames; optional FFmpeg creates MP4.
This is a small CPU reference renderer, not a Blender-class production renderer.
"""
from __future__ import annotations
import argparse, math, shutil, subprocess
from pathlib import Path

V = tuple[float, float, float]
def add(a: V,b: V)->V: return (a[0]+b[0],a[1]+b[1],a[2]+b[2])
def sub(a: V,b: V)->V: return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def mul(a: V,s: float)->V: return (a[0]*s,a[1]*s,a[2]*s)
def had(a: V,b: V)->V: return (a[0]*b[0],a[1]*b[1],a[2]*b[2])
def dot(a: V,b: V)->float: return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def norm(a: V)->V:
    n=math.sqrt(dot(a,a)); return mul(a,1.0/n) if n else (0,0,0)
def reflect(d: V,n: V)->V: return sub(d,mul(n,2*dot(d,n)))
def clamp(x: float)->float: return max(0.0,min(1.0,x))

class Sphere:
    def __init__(self,c: V,r: float,color: V,metal: float=0.0,emission: V=(0,0,0)):
        self.c,self.r,self.color,self.metal,self.emission=c,r,color,metal,emission
    def hit(self,o: V,d: V):
        oc=sub(o,self.c); b=dot(oc,d); q=dot(oc,oc)-self.r*self.r
        h=b*b-q
        if h<0:return None
        t=-b-math.sqrt(h)
        if t<1e-4:t=-b+math.sqrt(h)
        return t if t>1e-4 else None

class Plane:
    def __init__(self,y: float,color: V): self.y,self.color=y,color
    def hit(self,o: V,d: V):
        if abs(d[1])<1e-6:return None
        t=(self.y-o[1])/d[1]
        return t if t>1e-4 else None

def scene(t: float):
    pulse=0.5+0.5*math.sin(t*2.0)
    objects=[
        Sphere((0,0,0),1.05,(0.035,0.045,0.065),0.82),
        Sphere((0,0,0),1.09,(0.95,0.48,0.08),0.92,(0.025,0.009,0.001)),
        Sphere((0,0,0),0.78,(0.025,0.035,0.06),0.65),
        Sphere((0,1.75,0),0.28,(0.95,0.62,0.16),0.15,(1.0,0.35,0.035)),
        Sphere((-2.3,0.35,-1.0),0.62,(0.06,0.34,0.72),0.25),
        Sphere((2.1,0.15,-1.7),0.82,(0.48,0.08,0.12),0.35),
        Plane(-1.25,(0.075,0.085,0.11))]
    # Three slim golden orbital satellites
    for i in range(3):
        a=t*0.8+i*2*math.pi/3
        objects.append(Sphere((2.0*math.cos(a),0.12*math.sin(a*1.7),2.0*math.sin(a)),0.11,
                              (0.95,0.57,0.12),0.7,(0.18,0.055,0.006)))
    return objects, (4.2,5.0,6.0), (0.0,0.0,0.0), pulse

def trace(o: V,d: V,objects,light: V,depth: int=0)->V:
    best=1e30; obj=None; point=None; normal=None
    for item in objects:
        dist=item.hit(o,d)
        if dist is not None and dist<best:
            best,obj=dist,item
    if obj is None:
        sky=0.5+0.5*d[1]
        return (0.008+0.018*sky,0.015+0.025*sky,0.035+0.055*sky)
    point=add(o,mul(d,best))
    if isinstance(obj,Plane): n=(0,1,0); base=obj.color; metal=0.12; emission=(0,0,0)
    else: n=norm(sub(point,obj.c)); base=obj.color; metal=obj.metal; emission=obj.emission
    l=norm(sub(light,point)); shadow=False
    for other in objects:
        if other is obj: continue
        dist=other.hit(add(point,mul(n,1e-3)),l)
        if dist is not None and dist<math.sqrt(dot(sub(light,point),sub(light,point))): shadow=True; break
    diffuse=max(0,dot(n,l))*(0.16 if shadow else 0.95)
    view=mul(d,-1); h=norm(add(l,view))
    spec=(max(0,dot(n,h))**64)*(0.12+0.78*metal)*(0.12 if shadow else 1)
    ambient=0.10
    local=add(mul(base,ambient+diffuse),mul((1.0,0.72,0.38),spec))
    local=add(local,emission)
    if depth<2 and metal>0.35:
        rd=norm(reflect(d,n))
        reflected=trace(add(point,mul(n,1e-3)),rd,objects,light,depth+1)
        local=add(mul(local,1-metal*0.55),mul(reflected,metal*0.55))
    return tuple(clamp(c) for c in local)

def render_frame(path: Path,w: int,h: int,frame: int,total: int):
    t=frame/max(1,total-1)*2*math.pi
    objects,light,target,pulse=scene(t)
    radius=6.7
    cam=(radius*math.sin(t*0.22),2.0+0.35*math.sin(t),radius*math.cos(t*0.22))
    forward=norm(sub(target,cam)); right=norm((forward[2],0,-forward[0])); up=norm((
        right[1]*forward[2]-right[2]*forward[1],
        right[2]*forward[0]-right[0]*forward[2],
        right[0]*forward[1]-right[1]*forward[0]))
    aspect=w/h; fov=math.tan(math.radians(38))
    data=bytearray()
    for y in range(h):
        for x in range(w):
            sx=(2*(x+0.5)/w-1)*aspect*fov
            sy=(1-2*(y+0.5)/h)*fov
            direction=norm(add(forward,add(mul(right,sx),mul(up,sy))))
            col=trace(cam,direction,objects,light)
            # simple filmic-like tone curve and gamma
            for c in col:
                mapped=(c*(2.51*c+0.03))/(c*(2.43*c+0.59)+0.14)
                data.append(int(255*clamp(mapped)**(1/2.2)))
    path.write_bytes(f"P6\\n{w} {h}\\n255\\n".encode()+data)

def main():
    ap=argparse.ArgumentParser(description="NEXUS Photon Core reference renderer")
    ap.add_argument("--out",default="NEXUS_PHOTON_RENDER")
    ap.add_argument("--width",type=int,default=320); ap.add_argument("--height",type=int,default=180)
    ap.add_argument("--frames",type=int,default=24); ap.add_argument("--fps",type=int,default=12)
    ap.add_argument("--mp4",action="store_true")
    a=ap.parse_args()
    if not (16<=a.width<=1280 and 16<=a.height<=720 and 1<=a.frames<=240 and 1<=a.fps<=60):
        raise SystemExit("Use width 16–1280, height 16–720, frames 1–240, fps 1–60.")
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    for i in range(a.frames):
        render_frame(out/f"frame_{i:05d}.ppm",a.width,a.height,i,a.frames)
        print(f"Rendered {i+1}/{a.frames}",flush=True)
    print(f"Frames saved to: {out.resolve()}")
    if a.mp4:
        ff=shutil.which("ffmpeg")
        if not ff: raise SystemExit("FFmpeg not found. PPM frames are preserved; install FFmpeg to encode MP4.")
        cmd=[ff,"-y","-framerate",str(a.fps),"-i",str(out/"frame_%05d.ppm"),
             "-c:v","libx264","-pix_fmt","yuv420p",str(out/"NEXUS_PHOTON_PREVIEW.mp4")]
        subprocess.run(cmd,check=True)
        print("MP4 created:",out/"NEXUS_PHOTON_PREVIEW.mp4")

if __name__=="__main__": main()
