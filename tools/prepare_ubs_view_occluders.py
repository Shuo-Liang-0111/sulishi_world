"""Read-only ray diagnosis of cached source triangles, never a scene acceptance.

Ignore points inside the already executed r9 clipping volumes. This locates
remaining source surfaces by world position; it does not pretend to include
all new authored occluders or re-open the native scene without Blender.
"""
import json,hashlib
import numpy as np
from workspace_paths import read_path,write_path

paths=[read_path('derived/ubs_theaterstrasse20/'+n) for n in ['build_input.json','r8_geometry_probe.json']]
d,probe=[json.loads(p.read_text()) for p in paths]
r=json.loads(read_path('evidence/G1_027r9/ubs_build_report.json').read_text())
A,U,N=(np.array(d[k]) for k in ['A','U','N'])
SU,SN=(np.array(d[k]) for k in ['side_U','side_N'])
def frame(points,u,n):
    points=np.asarray(points);return np.column_stack(((points[:,:2]-A)@u,(points[:,:2]-A)@n,points[:,2]))
def in_boxes(points,boxes):
    result=np.zeros(len(points),dtype=bool)
    for box in boxes:
        b=np.array(box);result|=((points>=b[::2]-1e-8)&(points<=b[1::2]+1e-8)).all(1)
    return result
triangles=[];ids=[];indices=[]
for row in probe['photo_objects']:
    t=np.array(row['vertices_world'])[np.array(row['triangles'])]
    triangles.extend(t);ids.extend([row['name']]*len(t));indices.extend(range(len(t)))
T=np.array(triangles);ids=np.array(ids);indices=np.array(indices)
e1=T[:,1]-T[:,0];e2=T[:,2]-T[:,0]
normal=np.cross(e1,e2);norm=np.linalg.norm(normal,axis=1)
ground=(norm>1e-8)&(normal[:,2]>.96*norm)&(T[:,:,2].min(1)>8.18)&(T[:,:,2].max(1)<8.91)
results=[]
for camera in r['cameras']:
    eye=np.array(camera['eye']);f=np.array(camera['look'])-eye;f/=np.linalg.norm(f)
    right=np.cross(f,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,f)
    for px in [160,400,640,880,1120]:
        for py in [110,340,530,710]:
            direction=f+right*((px/1280-.5)*36/camera['lens'])+up*((420-py)/1280*36/camera['lens'])
            direction/=np.linalg.norm(direction)
            p=np.cross(direction,e2);det=(p*e1).sum(1);valid=abs(det)>1e-10
            inv=np.zeros(len(det));inv[valid]=1/det[valid]
            q=eye-T[:,0];a=(q*p).sum(1)*inv;qq=np.cross(q,e1);b=(qq*direction).sum(1)*inv
            dist=(qq*e2).sum(1)*inv
            valid&=(a>=0)&(b>=0)&(a+b<=1)&(dist>.06)&(dist<90)
            ii=np.flatnonzero(valid);points=eye+dist[ii,None]*direction
            front=frame(points,U,N);side=frame(points,SU,SN)
            cut=in_boxes(front,d['front_cut_boxes'])|in_boxes(side,d['side_cut_boxes'])|in_boxes(front,d['roof_cut_boxes'])
            cut|=ground[ii]&in_boxes(front,d['ground_cut_boxes'])
            kept=ii[~cut]
            if len(kept):
                j=int(kept[np.argmin(dist[kept])]);point=eye+dist[j]*direction;local=frame([point],U,N)[0]
                results.append(dict(camera=camera['name'],pixel=[px,py],object=ids[j],r8_face=int(indices[j]),
                                    distance_m=float(dist[j]),world_point=point.tolist(),front_uvz=local.tolist()))
out=dict(version='G1_027r9_source_diagnostic',camera_sensor_width_assumed_mm=36,image_size=[1280,840],
         inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
         samples=results,limitations='Cached source ray candidates after known clip volumes. Newly authored surfaces, other source tiles and float32 boundary effects are not included. Native checks and actual images remain authoritative.',
         native_changed=False)
write_path('derived/ubs_theaterstrasse20/view_occluder_candidates.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps([x for x in results if x['camera']=='UF_QA_FRONT' and x['pixel'][0]==640],indent=2))
