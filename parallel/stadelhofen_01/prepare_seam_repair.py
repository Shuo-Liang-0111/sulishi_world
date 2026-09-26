"""Precisely measured local edge transition from retained source ground triangles."""
from pathlib import Path
import json, numpy as np
from shapely.geometry import box
from shapely.ops import unary_union
OUT=Path(__file__).resolve().parent;P=OUT/'derived';d=json.loads((P/'build_input.json').read_text())
arr=np.load(P/'source_triangles.npz');t=arr['local'];ids=arr['node'];a=t[:,0,:2];b=t[:,1,:2]-a;c=t[:,2,:2]-a;det=b[:,0]*c[:,1]-b[:,1]*c[:,0]
normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);nz=np.abs(normal[:,2])/np.maximum(np.linalg.norm(normal,axis=1),1e-12)
good=(np.abs(det)>1e-8)&(nz>.82);safe=np.where(good,det,1)
def hits(xy):
    dp=np.array(xy)-a;r=(dp[:,0]*c[:,1]-dp[:,1]*c[:,0])/safe;ss=(b[:,0]*dp[:,1]-b[:,1]*dp[:,0])/safe
    ix=np.where(good&(r>=-1e-7)&(ss>=-1e-7)&(r+ss<=1+1e-7))[0]
    zz=t[ix,0,2]+r[ix]*(t[ix,1,2]-t[ix,0,2])+ss[ix]*(t[ix,2,2]-t[ix,0,2])
    return sorted([dict(z=float(z),node=str(ids[i]),normal_abs_z=float(nz[i])) for z,i in zip(zz,ix) if 9.8<z<11.2],key=lambda x:x['z'])
polys=[box(-1.3,-.82,13.25,8),box(-3.5,1.54,-1.3,8),box(13.25,1.54,15.35,8)]
outline=np.array(unary_union(polys).exterior.coords[:-1]);profiles=[];missing=[]
for k,(p0,p1) in enumerate(zip(outline,np.roll(outline,-1,axis=0))):
    # Only exposed walkable forecourt edges. Rear portions terminate into masonry.
    p0=p0.copy();p1=p1.copy()
    if max(p0[1],p1[1])<1.54-1e-8:continue
    if min(p0[1],p1[1])<1.54:
        if p0[1]<1.54:p0=p0+(p1-p0)*(1.54-p0[1])/(p1[1]-p0[1])
        else:p1=p1+(p0-p1)*(1.54-p1[1])/(p0[1]-p1[1])
    length=np.linalg.norm(p1-p0)
    if length<.005:continue
    values=[]
    for fraction in np.linspace(0,1,max(2,int(np.ceil(length/.055))+1)):
        uv=p0+(p1-p0)*fraction;hs=hits(uv)
        if not hs:missing.append(dict(uv=uv.tolist(),edge=k))
        values.append(dict(t=float(fraction),uv=uv.tolist(),z=hs[0]['z'] if hs else None,hits=hs))
    profiles.append(dict(edge=k,a=p0.tolist(),b=p1.tolist(),samples=values))
assert not missing,missing
d['version']='SF1_v02';d['apron_outline']=outline.tolist();d['apron_warp_width_m']=.72;d['ground_edge_profiles']=profiles
d['crop_boxes']=[[-1.3,13.25,-.82,8,9.8,15.8],[-3.5,-1.3,1.54,8,9.8,15.8],[13.25,15.35,1.54,8,9.8,15.8]]
d['seam_repair_basis']='Two bounded paving extensions bypass unresolved source scan obstruction patches: west 2.2m x6.46m, east 2.1m x6.46m; facades and measured station outlines unchanged. New ground within 0.72m of exposed edge blends to original nearby nearly horizontal triangles. Absolute photo height remains uncertain.'
def intersected_area(triangle,bounds):
    poly=[p.copy() for p in triangle]
    for axis,value,sgn in [(0,bounds[0],1),(0,bounds[1],-1),(1,bounds[2],1),(1,bounds[3],-1),(2,bounds[4],1),(2,bounds[5],-1)]:
        if len(poly)<3:return 0.
        keep=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=(a[axis]-value)*sgn;db=(b[axis]-value)*sgn
            if da>=0:keep.append(a)
            if (da>=0)!=(db>=0):keep.append(a+(b-a)*da/(da-db))
        poly=keep
    return sum(float(np.linalg.norm(np.cross(poly[i]-poly[0],poly[i+1]-poly[0]))*.5) for i in range(1,len(poly)-1))
d['candidate_old_objects']=[];broad_only=[]
for node in np.unique(ids):
    q=t[ids==node];lo=q.min(axis=1);hi=q.max(axis=1)
    for bb in d['crop_boxes']:
        bounds=np.array(bb).reshape(3,2)
        possible=np.all((hi>=bounds[:,0])&(lo<=bounds[:,1]),axis=1)
        if not np.any(possible):continue
        if any(intersected_area(tri,bb)>1e-8 for tri in q[possible]):
            d['candidate_old_objects'].append('CTX_I3S_'+str(node));break
    else:
        if any(np.any(np.all((hi>=np.array(bb).reshape(3,2)[:,0])&(lo<=np.array(bb).reshape(3,2)[:,1]),axis=1)) for bb in d['crop_boxes']):broad_only.append('CTX_I3S_'+str(node))
d['broad_phase_only_no_cut_objects']=broad_only
d['camera_ground_z']={'SF1_QA_APPROACH':10.051853403676258,'SF1_QA_CONTEXT':10.014204615703948}
(P/'build_input.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
(P/'seam_repair_receipt.json').write_text(json.dumps(dict(patch_area_m2=unary_union(polys).area,additional_area_m2=unary_union(polys).area-polys[0].area,profile_samples=sum(len(e['samples']) for e in profiles),missing=missing,candidate_old_objects=d['candidate_old_objects'],boundary_plan=d['apron_outline'],crop_boxes=d['crop_boxes'],basis=d['seam_repair_basis']),indent=2))
print('Seam repair prepared:',len(profiles),'edges,',sum(len(e['samples']) for e in profiles),'source hits,',d['candidate_old_objects'])
