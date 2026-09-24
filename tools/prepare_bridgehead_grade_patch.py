"""Fit omitted higher road support, then prepare a bounded editable vertex repair.

Retain every original XY, face, UV and source mast endpoint. This is an inferred
smoothed reconstruction grade, not an engineering survey or runtime acceptance.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from bridge_grade_math import Grade,weight

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_grade'
source=json.loads((D/'raw_source_candidates.json').read_text())
p=np.array([q['xyz'] for q in source]);q=(p[:,:2]-[2683505,1246835])/20
a=np.c_[np.ones(len(q)),q,q[:,0]**2,q[:,0]*q[:,1],q[:,1]**2]
base=np.minimum(np.sqrt([s['area_m2'] for s in source]),3);w=base.copy()
for _ in range(20):
    coef=np.linalg.lstsq(a*w[:,None],p[:,2]*w,rcond=None)[0]
    error=a@coef-p[:,2];w=base*np.minimum(1,.04/np.maximum(abs(error),1e-8))
support=abs(error)<=.14
for _ in range(12):
    w=base*support*np.minimum(1,.04/np.maximum(abs(error),1e-8))
    coef=np.linalg.lstsq(a*w[:,None],p[:,2]*w,rcond=None)[0];error=a@coef-p[:,2]
assert support.sum()>200 and np.quantile(abs(error[support]),.95)<.14
grade=Grade(np.load(D/'027_surfaces.npz'),coef)
rows=json.loads((D/'027_target_objects.json').read_text());old=np.load(D/'027_target_vertices.npz')
bridge=json.loads((R/'derived/bellevue/bridge_deck/build_input.json').read_text())
masts={m['id'].split('.')[-1]:m for m in bridge['masts']};mast_changes={}
for ident,m in masts.items():
    xy=np.array(m['xy'])-[2683775,1246700]
    nearby={k:grade.surfaces[k].sample(xy) for k in grade.surfaces}
    kind=min(nearby,key=lambda k:float(nearby[k][1][0]))
    dz=float(grade.delta(xy,kind)[0]) if kind!='bank' else 0.
    oldground=m['ground_interpreted_ln02_m']-400;newground=oldground+dz
    oldtop=max(oldground+.045,m['base_ln02_m']-400+.025)
    newtop=max(newground+.045,m['base_ln02_m']-400+.025)
    mast_changes[ident]=dict(ground_before=oldground,ground_after=newground,top_before=oldtop,top_after=newtop,kind=kind)
changed=[];patch={};numerical_repairs=[]
roadroles={'road_asphalt','road_concrete','road_joint','rail_steel','groove_floor','groove_wall','crossing_paint',
           'asphalt_road','asphalt_track','rail','drain'}
for row in rows:
    v=old[row['key']];xy=v[:,:2];name=row['name'];role=row['role'];dz=np.zeros(len(v))
    if name.startswith(('BD_MAST_FOUNDATION_','BD_MAST_FLANGE_','BD_MAST_ANCHOR_')):
        ident=name.split('_')[3];m=mast_changes[ident]
        if name.startswith('BD_MAST_FOUNDATION_'):
            low=m['ground_before']-.14;alpha=np.clip((v[:,2]-low)/(m['top_before']-low),0,1)
            dz=(1-alpha)*(m['ground_after']-m['ground_before'])+alpha*(m['top_after']-m['top_before'])
        else:dz[:]=m['top_after']-m['top_before']
    elif role in roadroles:dz=grade.delta(xy,'road')
    elif role in ['asphalt_walk','guard']:dz=grade.delta(xy,'walk')
    elif role in ['curb','paint']:
        road,_=grade.surfaces['road'].sample(xy);walk,_=grade.surfaces['walk'].sample(xy)
        if role=='paint':alpha=(abs(v[:,2]-walk)<abs(v[:,2]-road)).astype(float)
        else:alpha=np.clip((v[:,2]-road)/np.maximum(walk-road,.02),0,1)
        dz=grade.delta(xy,'road')*(1-alpha)+grade.delta(xy,'walk')*alpha
    else:raise AssertionError((name,role))
    # The saved mesh uses float32. The prospective payload has exactly those
    # coordinates so safety checks see the same values as the Blender apply.
    new=v.astype(np.float32);new[:,2]=(v[:,2]+dz).astype(np.float32)
    if role in ['road_asphalt','road_concrete','road_joint','asphalt_walk','asphalt_road','asphalt_track']:
        ids=old[row['key']+'_triangles'];before=v[ids]
        bn=np.cross(before[:,1]-before[:,0],before[:,2]-before[:,0])
        upper=(bn[:,2]>.85*np.linalg.norm(bn,axis=1))&(bn[:,2]>1e-5)
        initial=new.copy();repaired=set()
        for iteration in range(12):
            t=new[ids].astype(float);n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
            slope=np.linalg.norm(n[:,:2],axis=1)/np.maximum(n[:,2],1e-20)
            bad=np.flatnonzero(upper&(slope>.25))
            if not len(bad):break
            stable=np.flatnonzero(upper&(slope<.2)&(n[:,2]>.001))
            centres=t[:,:,:2].mean(1)
            for face in bad:
                edge=max(np.linalg.norm(t[face,i,:2]-t[face,j,:2]) for i,j in [(0,1),(1,2),(2,0)])
                assert n[face,2]/edge<.005,('Non-numerical steep face',name,int(face))
                near=stable[np.argsort(np.linalg.norm(centres[stable]-centres[face],axis=1))[:3]]
                if len(near) and np.min(np.linalg.norm(centres[near]-centres[face],axis=1))<1:
                    gradient=np.median(-n[near,:2]/n[near,2,None],axis=0)
                else:
                    # Some complete fragments are sub-millimetre-wide strips;
                    # estimate the local design tangent over20cm, not from the
                    # ill-conditioned tiny triangle itself.
                    centre=centres[face];kind='walk' if role=='asphalt_walk' else 'road'
                    gradient=np.array([(grade.target(centre+step,kind)[0]-grade.target(centre-step,kind)[0])/.2
                                       for step in [np.array([.1,0]),np.array([0,.1])]])
                    assert np.linalg.norm(gradient)<.2,(name,int(face),gradient.tolist())
                ia,ib=max([(0,1),(1,2),(2,0)],key=lambda pair:np.linalg.norm(t[face,pair[1],:2]-t[face,pair[0],:2]))
                direction=(t[face,ib,:2]-t[face,ia,:2])/edge
                along=(t[face,ib,2]-t[face,ia,2])/edge
                # Preserve the resolved slope along its long edge; only the
                # unstable transverse slope of this narrow triangle is repaired.
                gradient+=direction*(along-gradient@direction)
                assert np.linalg.norm(gradient)<.25,(name,int(face))
                plane_z=np.mean(t[face,:,2]-t[face,:,:2]@gradient)+t[face,:,:2]@gradient
                for vertex,z in zip(ids[face],plane_z):
                    equivalent=np.all(new[:,:2]==new[vertex,:2],axis=1)
                    new[equivalent,2]+=np.float32(z-new[vertex,2])
                repaired.add(int(face))
            assert np.max(abs(new[:,2]-initial[:,2]))<.002,('Overlarge numerical adjustment',name)
        else:raise AssertionError(('Sliver repair did not converge',name))
        if repaired:numerical_repairs.append(dict(name=name,triangles=sorted(repaired),max_adjustment_m=float(np.max(abs(new[:,2]-initial[:,2])))))
    moved=np.abs(new[:,2]-v[:,2])>1e-7
    if not moved.any():continue
    assert np.array_equal(new[:,:2],v[:,:2].astype(np.float32)),name
    assert max(abs(dz))<.8,(name,float(max(abs(dz))))
    patch[row['key']]=new
    changed.append(dict(**row,changed_vertices=int(moved.sum()),max_shift_m=float(max(abs(dz)))))
np.savez_compressed(D/'027r1_vertex_patch.npz',**patch)
record=dict(base_version='G1_027',target_version='G1_027r1',objects=changed,mast_foundations=mast_changes,numerical_repairs=numerical_repairs,
    source_center_lv95=[2683505,1246835],source_scale_m=20,coefficients=coef.tolist(),
    support_faces=int(support.sum()),candidate_faces=len(source),
    rejected_source_faces=[dict(node=s['node'],face=s['face'],residual_m=float(error[i])) for i,s in enumerate(source) if not support[i]],
    support_residual_quantiles_m=np.quantile(abs(error[support]),[.5,.9,.95,1]).tolist(),
    bounds_lv95=[2683478,1246810,2683521,1246855],
    inferred='Robust local road grade with smooth boundary fade; 30mm dropped tie to retained bank,120mm raised bridge walk; fabricate mast bases without moving source masts.',
    visual_acceptance=False,natural_use_verified=False,
    inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'raw_source_candidates.json',D/'027_surfaces.npz',D/'027_target_vertices.npz',D/'027_target_objects.json']})
record['patch_sha256']=hashlib.sha256((D/'027r1_vertex_patch.npz').read_bytes()).hexdigest()
(D/'027r1_patch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(dict(objects=len(changed),vertices=sum(q['changed_vertices'] for q in changed),max_shift_m=max(q['max_shift_m'] for q in changed),support=record['support_faces'],residuals=record['support_residual_quantiles_m'],patch_bytes=(D/'027r1_vertex_patch.npz').stat().st_size)))
