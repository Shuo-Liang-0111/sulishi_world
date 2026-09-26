"""Bounded file and scene helpers; import has no mutations."""
from pathlib import Path
import json, hashlib, os, math
import bpy, numpy as np
from mathutils import Vector
ROOT=Path('H:/MyWorld/ZurichWorld')
OUT=Path(__file__).resolve().parent
D=json.loads((OUT/'derived/build_input.json').read_text(encoding='utf-8'))
A=np.array(D['A']);U=np.array(D['U']);N=np.array(D['N']);W=D['width_m']
def write(rel,data):
    p=(OUT/rel).resolve();assert p.is_relative_to(OUT.resolve())
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
def P(u,v,z):return np.r_[A+U*u+N*v,z]
def Q(p):return np.r_[(np.array(p)[:2]-A)@U,(np.array(p)[:2]-A)@N,p[2]]
def base_grade(u,v):
    c=D['ground_plane_coefficients'];z=c[0]+c[1]*u+c[2]*v
    local=D.get('left_interface_ground')
    if local:
        def smooth(t):
            t=float(np.clip(t,0,1));return t*t*(3-2*t)
        wu=smooth((local['zero_weight_u_min']-u)/(local['zero_weight_u_min']-local['full_weight_u_max']))
        wv=smooth((local['zero_weight_v_min']-v)/(local['zero_weight_v_min']-local['full_weight_v_max']))
        cc=local['coefficients'];target=cc[0]+cc[1]*u+cc[2]*v
        z+=(target-z)*wu*wv
    return z
_edges=[(np.array(e['a']),np.array(e['b']),np.array([r['t'] for r in e['samples']]),np.array([r['z'] for r in e['samples']])) for e in D.get('ground_edge_profiles',[])]
def grade(u,v):
    z=base_grade(u,v)
    if not _edges:return z
    p=np.array([u,v]);weights=[];deltas=[];width=D['apron_warp_width_m']
    for a,b,ts,zs in _edges:
        ab=b-a;t=np.clip(np.dot(p-a,ab)/np.dot(ab,ab),0,1);close=a+ab*t;dist=np.linalg.norm(p-close)
        if dist>=width:continue
        # Smooth transition with zero slope at the unmodified interior edge.
        w=(1-dist/width)**2*(1+2*dist/width)
        weights.append(w);deltas.append(np.interp(t,ts,zs)-base_grade(*close))
    if weights:z+=float(np.dot(weights,deltas)/sum(weights)*max(weights))
    return z
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
def camera(name,u,v,eye_z,target,lens=36):
    c=bpy.data.collections.get('SF1_QA_CAMERAS') or collection('SF1_QA_CAMERAS')
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);c.objects.link(o)
    o.location=P(u,v,eye_z);o.rotation_euler=(Vector(P(*target))-o.location).to_track_quat('-Z','Y').to_euler()
    d.lens=lens;d.clip_start=.06;d.clip_end=500
    o['eye_height_basis']='1.65m above prepared source-ground apron/landing except explicit context camera'
    return o
def make_cameras():
    return [camera('SF1_QA_ENTRY',4.0,7.65,grade(4,7.65)+1.65,(6.05,0,13.03),32),
       camera('SF1_QA_REVERSE',10.35,1.35,D['landing_z']+1.65,(3.1,4.8,12.22),28),
       camera('SF1_QA_APPROACH',-8.5,11.5,D.get('camera_ground_z',{}).get('SF1_QA_APPROACH',base_grade(-8.5,11.5))+1.65,(6,0,13.1),35),
       camera('SF1_QA_CONTEXT',7.0,21,D.get('camera_ground_z',{}).get('SF1_QA_CONTEXT',base_grade(7,21))+1.65,(6,0,16.35),32),
       camera('SF1_QA_DOOR_DETAIL',6.04,2.07,D['landing_z']+1.65,(6.01,-.1,12.85),24),
       camera('SF1_QA_DOOR_OPEN',6.04,2.07,D['landing_z']+1.65,(6.01,-.7,12.6),24)]
def configure_render():
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32
    s.cycles.use_denoising=True;s.cycles.max_bounces=8;s.cycles.transmission_bounces=6
    s.render.resolution_x=1400;s.render.resolution_y=960;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
    s.render.threads_mode='FIXED';s.render.threads=12
    return s
def render(camera_name,folder='evidence/v01',samples=32):
    s=configure_render();s.camera=bpy.data.objects[camera_name];s.cycles.samples=samples
    p=OUT/folder/(camera_name+'.png');p.parent.mkdir(exist_ok=True,parents=True);s.render.filepath=str(p)
    result=bpy.ops.render.render(write_still=True);assert 'FINISHED' in result
    write(str(Path(folder)/(camera_name+'_settings.json')),dict(camera=camera_name,location=list(s.camera.location),rotation=list(s.camera.rotation_euler),lens=s.camera.data.lens,version=s.get('sf1_version'),native=bpy.data.filepath,native_sha256=sha(bpy.data.filepath),engine=s.render.engine,device=s.cycles.device,samples=s.cycles.samples,resolution=[1400,960],view_transform=s.view_settings.view_transform,look=s.view_settings.look,exposure=s.view_settings.exposure,process_id=os.getpid(),image_sha256=sha(p)))
