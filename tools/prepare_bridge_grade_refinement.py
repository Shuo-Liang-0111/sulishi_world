"""Evaluate the existing source-backed grade on refined, UV-preserving meshes."""
from pathlib import Path
import hashlib,json
import numpy as np
from bridge_grade_math import RefinedGrade

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_grade'
meta=json.loads((D/'027r2_refined_objects.json').read_text())
base=json.loads((D/'027r1_patch.json').read_text())
assert hashlib.sha256((D/'027r2_refined_reference.npz').read_bytes()).hexdigest()==meta['reference_sha256']
ref=np.load(D/'027r2_refined_reference.npz');g=RefinedGrade(np.load(D/'027_surfaces.npz'),base['coefficients'])
out={};diagnosis=[];slopes=[];repairs=[]
roadroles={'road_asphalt','road_concrete','road_joint','rail_steel','groove_floor','groove_wall','crossing_paint',
           'asphalt_road','asphalt_track','rail','drain'}
surfaces={'road_asphalt','road_concrete','road_joint','asphalt_road','asphalt_track','asphalt_walk'}
for row in meta['objects']:
    key=row['key'];v=ref[key].astype(float);xy=v[:,:2];role=row['role']
    if role in roadroles:dz=g.delta(xy,'road')
    elif role=='asphalt_walk':dz=g.delta(xy,'walk')
    else:
        assert role in ['curb','paint']
        road,_=g.surfaces['road'].sample(xy);walk,_=g.surfaces['walk'].sample(xy)
        if role=='paint':alpha=(abs(v[:,2]-walk)<abs(v[:,2]-road)).astype(float)
        else:alpha=np.clip((v[:,2]-road)/np.maximum(walk-road,.02),0,1)
        dz=g.delta(xy,'road')*(1-alpha)+g.delta(xy,'walk')*alpha
    new=v.astype(np.float32);new[:,2]=(v[:,2]+dz).astype(np.float32)
    ids=ref[key+'_faces'];before=v[ids];bn=np.cross(before[:,1]-before[:,0],before[:,2]-before[:,0])
    if role in surfaces:
        upper=(bn[:,2]>.85*np.linalg.norm(bn,axis=1))&(bn[:,2]>1e-5)
        initial=new.copy();repaired=set()
        for iteration in range(96):
            t=new[ids].astype(float);n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
            slope=np.linalg.norm(n[:,:2],axis=1)/np.maximum(n[:,2],1e-20)
            bad=np.flatnonzero(upper&(slope>.25))
            if not len(bad):break
            stable=np.flatnonzero(upper&(slope<.2)&(n[:,2]>.001));centres=t[:,:,:2].mean(1)
            for face in bad:
                edge=max(np.linalg.norm(t[face,i,:2]-t[face,j,:2]) for i,j in [(0,1),(1,2),(2,0)])
                if n[face,2]/edge>=.005:
                    diagnosis.append(dict(name=row['name'],face=int(face),slope=float(slope[face]),points=t[face].tolist()))
                    continue
                near=stable[np.argsort(np.linalg.norm(centres[stable]-centres[face],axis=1))[:3]]
                if len(near) and np.min(np.linalg.norm(centres[near]-centres[face],axis=1))<1:
                    grad=np.median(-n[near,:2]/n[near,2,None],axis=0)
                else:
                    centre=centres[face];kind='walk' if role=='asphalt_walk' else 'road'
                    grad=np.array([(g.target(centre+step,kind)[0]-g.target(centre-step,kind)[0])/.2
                        for step in [np.array([.1,0]),np.array([0,.1])]])
                ia,ib=max([(0,1),(1,2),(2,0)],key=lambda p:np.linalg.norm(t[face,p[1],:2]-t[face,p[0],:2]))
                direction=(t[face,ib,:2]-t[face,ia,:2])/edge
                grad+=direction*((t[face,ib,2]-t[face,ia,2])/edge-grad@direction)
                if np.linalg.norm(grad)>.25:
                    diagnosis.append(dict(name=row['name'],face=int(face),long_slope=float(np.linalg.norm(grad))))
                    continue
                plane=np.mean(t[face,:,2]-t[face,:,:2]@grad)+t[face,:,:2]@grad
                for vertex,z in zip(ids[face],plane):
                    eq=np.all(new[:,:2]==new[vertex,:2],axis=1)
                    new[eq,2]+=np.float32(z-new[vertex,2])
                repaired.add(int(face))
            if diagnosis:break
        if repaired:
            change=float(np.max(abs(new[:,2]-initial[:,2])))
            if change>=.005:
                failure=dict(name=row['name'],max_adjustment_m=change,faces=sorted(repaired),
                    vertices=[dict(index=int(i),before=initial[i].tolist(),after=new[i].tolist())
                              for i in np.flatnonzero(abs(new[:,2]-initial[:,2])>.001)],
                    triangles=[dict(face=i,reference=v[ids[i]].tolist(),before=initial[ids[i]].tolist(),after=new[ids[i]].tolist())
                               for i in sorted(repaired)])
                (D/'027r2_numeric_diagnosis.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
            # This is bounded geometric regularization of sub-5mm-wide
            # triangles spanning a curved field, not merely float rounding.
            # Keep XY/source boundaries fixed and record every adjustment;
            # 5mm remains below the source fit's27mm median residual.
            assert change<.005,(row['name'],change)
            repairs.append(dict(name=row['name'],faces=len(repaired),max_adjustment_m=change))
        t=new[ids].astype(float);n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
        values=np.linalg.norm(n[upper,:2],axis=1)/n[upper,2];slopes.extend(values.tolist())
        if len(values) and values.max()>.25:diagnosis.append(dict(name=row['name'],remaining_max_slope=float(values.max())))
    assert np.array_equal(new[:,:2],ref[key][:,:2])
    out[key]=new
np.savez_compressed(D/'027r2_refined_patch.npz',**out)
summary=dict(version='G1_027r2',base_version='G1_027r1',objects=len(out),
    vertices=sum(len(v) for v in out.values()),numeric_repairs=repairs,unresolved=diagnosis,
    upper_slope_quantiles=np.quantile(slopes,[.5,.95,.99,1]).tolist(),
    inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'027r2_refined_reference.npz',
        D/'027r2_refined_objects.json',D/'027r1_patch.json',D/'027_surfaces.npz']},
    payload_sha256=hashlib.sha256((D/'027r2_refined_patch.npz').read_bytes()).hexdigest(),
    visual_acceptance=False,natural_use_verified=False)
(D/'027r2_refinement.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['inputs','numeric_repairs','unresolved']},indent=2))
print('UNRESOLVED',len(diagnosis),json.dumps(diagnosis[:8]))
assert not diagnosis,'Refinement candidate requires further correction; no native changes applied.'
