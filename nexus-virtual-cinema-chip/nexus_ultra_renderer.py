#!/usr/bin/env python3
"""NEXUS Ultra Renderer v0.1 — experimental CPU path/ray-tracing reference.

Standard-library-only educational renderer. Includes multi-sample antialiasing,
diffuse and metallic materials, emissive surfaces, recursive reflections,
soft-shadow sampling, depth of field, atmospheric fog, procedural sky,
ACES-like tone mapping and PPM output. It is not a production renderer and
does not provide real-time GPU acceleration, fluid simulation or certification.
"""
from __future__ import annotations
import argparse
import math
import random
from pathlib import Path

V = tuple[float, float, float]
def add(a: V,b: V)->V: return (a[0]+b[0],a[1]+b[1],a[2]+b[2])
def sub(a: V,b: V)->V: return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def scale(a: V,s: float)->V: return (a[0]*s,a[1]*s,a[2]*s)
def mul(a: V,b: V)->V: return (a[0]*b[0],a[1]*b[1],a[2]*b[2])
def dot(a: V,b: V)->float: return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def length(a: V)->float: return math.sqrt(dot(a,a))
def unit(a: V)->V: return scale(a,1/max(length(a),1e-12))
def reflect(d: V,n: V)->V: return sub(d,scale(n,2*dot(d,n)))
def clamp(x: float)->float: return max(0.0,min(1.0,x))
def mix(a: V,b: V,t: float)->V: return add(scale(a,1-t),scale(b,t))

class Sphere:
    def __init__(self, center: V, radius: float, color: V, metallic=0.0,
                 roughness=0.5, emission: V=(0,0,0)):
        self.center=center; self.radius=radius; self.color=color
        self.metallic=metallic; self.roughness=roughness; self.emission=emission
    def hit(self,o,d):
        oc=sub(o,self.center); b=dot(oc,d); disc=b*b-dot(oc,oc)+self.radius*self.radius
        if disc<0:return None
        root=math.sqrt(disc); t=-b-root
        if t<1e-4:t=-b+root
        if t<1e-4:return None
        p=add(o,scale(d,t))
        return t,p,unit(sub(p,self.center)),self

class Plane:
    def __init__(self,y,color,roughness=0.8):
        self.y=y; self.color=color; self.metallic=0.0
        self.roughness=roughness; self.emission=(0,0,0)
    def hit(self,o,d):
        if abs(d[1])<1e-7:return None
        t=(self.y-o[1])/d[1]
        if t<1e-4:return None
        p=add(o,scale(d,t))
        return t,p,(0,1,0),self

def random_sphere(rng):
    z=rng.uniform(-1,1); a=rng.uniform(0,2*math.pi)
    q=math.sqrt(max(0,1-z*z))
    return (q*math.cos(a),z,q*math.sin(a))

def sky(d):
    horizon=(0.018,0.028,0.055); zenith=(0.002,0.006,0.022)
    c=mix(horizon,zenith,clamp(d[1]*0.5+0.5))
    # Deterministic sparse star-like highlights.
    if d[1]>0.05:
        h=math.sin(d[0]*1271.7+d[1]*927.1+d[2]*313.9)*43758.5453
        if h-math.floor(h)>0.997: c=add(c,(0.55,0.62,0.8))
    return c

def scene(t):
    pulse=0.5+0.5*math.sin(t*2.0)
    objs=[
      Sphere((0,0,0),1.0,(0.025,0.04,0.075),0.78,0.18),
      Sphere((0,0,0),1.035,(0.62,0.25,0.045),0.88,0.12,(0.018,0.006,0.001)),
      Sphere((0,0,0),0.72,(0.012,0.022,0.045),0.55,0.28),
      Sphere((0,1.65,0),0.23,(0.95,0.56,0.16),0.1,0.35,(1.1,0.28,0.025)),
      Sphere((-2.15,0.1,-1.1),0.58,(0.025,0.19,0.55),0.25,0.3),
      Sphere((2.05,0.12,-1.5),0.76,(0.42,0.045,0.08),0.3,0.32),
      Plane(-1.18,(0.055,0.065,0.09),0.72)]
    for i in range(4):
        a=t*0.75+i*math.pi/2
        objs.append(Sphere((2*math.cos(a),0.1*math.sin(a*1.8),2*math.sin(a)),
                           0.075,(0.95,0.52,0.12),0.72,0.16,(0.12,0.025,0.002)))
    return objs

def nearest_hit(o,d,objects):
    best=None
    for obj in objects:
        h=obj.hit(o,d)
        if h and (best is None or h[0]<best[0]): best=h
    return best

def direct_lighting(p,n,objects,light,rng,samples):
    total=(0.0,0.0,0.0)
    for _ in range(samples):
        lp=add(light,scale(random_sphere(rng),0.32))
        delta=sub(lp,p); dist=length(delta); l=scale(delta,1/max(dist,1e-9))
        ndl=max(0,dot(n,l))
        if ndl<=0: continue
        blocker=nearest_hit(add(p,scale(n,1e-3)),l,objects)
        visible=1.0 if blocker is None or blocker[0]>=dist-0.02 else 0.12
        total=add(total,scale((1.0,0.78,0.52),ndl*visible/(samples)))
    return total

def trace(o,d,objects,light,rng,depth=0,max_depth=3,fog=0.018,shadow_samples=2):
    hit=nearest_hit(o,d,objects)
    if hit is None: return sky(d)
    dist,p,n,obj=hit
    direct=direct_lighting(p,n,objects,light,rng,shadow_samples)
    diffuse=mul(obj.color,add((0.075,0.085,0.12),direct))
    result=add(diffuse,obj.emission)
    if depth<max_depth and obj.metallic>0.05:
        reflected=unit(reflect(d,n))
        # Roughness perturbation is a compact approximation, not a full BRDF.
        jitter=scale(random_sphere(rng),obj.roughness*0.22)
        reflected=unit(add(reflected,jitter))
        bounced=trace(add(p,scale(n,1e-3)),reflected,objects,light,rng,
                      depth+1,max_depth,fog,shadow_samples)
        result=add(scale(result,1-obj.metallic*0.72),scale(mul(bounced,obj.color),obj.metallic*0.72))
    trans=math.exp(-fog*dist)
    return add(scale(result,trans),scale((0.018,0.026,0.045),1-trans))

def aces(x):
    return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14))

def render(out,w,h,frames,fps,spp,seed,depth,fog,dof):
    out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(seed)
    for frame in range(frames):
        t=frame/max(1,frames-1)*2*math.pi
        objects=scene(t)
        target=(0,0,0); radius=6.8
        cam=(radius*math.sin(t*0.18),1.8+0.22*math.sin(t),radius*math.cos(t*0.18))
        forward=unit(sub(target,cam))
        right=unit((forward[2],0,-forward[0]))
        up=unit((right[1]*forward[2]-right[2]*forward[1],
                 right[2]*forward[0]-right[0]*forward[2],
                 right[0]*forward[1]-right[1]*forward[0]))
        aspect=w/h; fov=math.tan(math.radians(36)); pixels=bytearray()
        for y in range(h):
            for x in range(w):
                col=(0.0,0.0,0.0)
                for _ in range(spp):
                    sx=(2*(x+rng.random())/w-1)*aspect*fov
                    sy=(1-2*(y+rng.random())/h)*fov
                    direction=unit(add(forward,add(scale(right,sx),scale(up,sy))))
                    origin=cam
                    if dof>0:
                        lens=scale(random_sphere(rng),dof)
                        origin=add(cam,lens)
                        direction=unit(sub(add(cam,scale(direction,7.0)),origin))
                    sample=trace(origin,direction,objects,(4.2,5.2,5.5),rng,
                                 0,depth,fog,2)
                    col=add(col,scale(sample,1/spp))
                for c in col:
                    pixels.append(int(255*(aces(c)**(1/2.2))))
        (out/f"frame_{frame:05d}.ppm").write_bytes(
            f"P6\n{w} {h}\n255\n".encode()+pixels)
        print(f"Rendered frame {frame+1}/{frames}",flush=True)
    (out/"render_manifest.json").write_text(
      __import__("json").dumps({"renderer":"NEXUS Ultra Renderer v0.1",
       "resolution":[w,h],"frames":frames,"fps":fps,"samples_per_pixel":spp,
       "max_reflection_depth":depth,"fog_density":fog,"depth_of_field":dof,
       "status":"frames_generated_if_execution_completed"},indent=2)+"\n",
      encoding="utf-8")
    print(f"Frames and manifest saved in {out.resolve()}")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",default="NEXUS_ULTRA_RENDER")
    p.add_argument("--width",type=int,default=160); p.add_argument("--height",type=int,default=90)
    p.add_argument("--frames",type=int,default=12); p.add_argument("--fps",type=int,default=12)
    p.add_argument("--spp",type=int,default=2,help="samples per pixel")
    p.add_argument("--depth",type=int,default=2,help="reflection depth, 0-5")
    p.add_argument("--fog",type=float,default=0.018)
    p.add_argument("--dof",type=float,default=0.0,help="depth-of-field lens radius")
    p.add_argument("--seed",type=int,default=2090)
    a=p.parse_args()
    if not (16<=a.width<=640 and 16<=a.height<=360 and 1<=a.frames<=120
            and 1<=a.fps<=60 and 1<=a.spp<=16 and 0<=a.depth<=5
            and 0<=a.fog<=1 and 0<=a.dof<=0.2):
        p.error("parameters outside safe prototype limits")
    render(Path(a.out),a.width,a.height,a.frames,a.fps,a.spp,a.seed,a.depth,a.fog,a.dof)

if __name__=="__main__": main()
