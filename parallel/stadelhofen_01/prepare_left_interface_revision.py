"""v06 replaces the scanned ramp beside the measured west plinth.

The added crop is restricted to the wall-foot/ground height band, within the
existing overall forecourt envelope. It does not move the plinth or steps.
"""
from pathlib import Path
import json, numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

P = Path(__file__).resolve().parent
path = P/'derived/build_input.json'
d = json.loads(path.read_text())
assert d['version'] == 'SF1_v05'
ns = {'__file__': str(P/'prepare_seam_repair.py')}
exec((P/'prepare_seam_repair.py').read_text().split('polys=')[0], ns)

# Low-slope source samples on the real forecourt, clear of the scanned wall ramp.
samples = []
for u in np.linspace(-3.45, -1.35, 12):
    for v in np.linspace(.55, 1.48, 9):
        hs = [h for h in ns['hits']([u,v]) if h['normal_abs_z'] >= .995]
        assert hs, (u,v)
        samples.append(dict(u=float(u),v=float(v),**hs[0]))
design = np.array([[1,r['u'],r['v']] for r in samples])
zz = np.array([r['z'] for r in samples])
coef = np.linalg.lstsq(design,zz,rcond=None)[0]
residual = design@coef-zz
assert abs(residual).max() < .015
d['left_interface_ground'] = dict(coefficients=coef.tolist(),
    full_weight_u_max=-1.19, zero_weight_u_min=-.59,
    full_weight_v_max=1.54, zero_weight_v_min=2.26,
    source_normal_abs_z_min=.995, samples=samples,
    fit_rmse_m=float(np.sqrt(np.mean(residual**2))),
    maximum_fit_residual_m=float(abs(residual).max()))

# Only 5.192 square metres are added, below local z=11.40. The upper wing and
# every original object outside these bounded volumes are preserved.
extra = [-3.5,-1.3,-.82,1.54,9.8,11.40]
d['crop_boxes'].append(extra)
polys = [box(b[0],b[2],b[1],b[3]) for b in d['crop_boxes']]
outline = unary_union(polys)
d['apron_outline'] = list(map(list,outline.exterior.coords[:-1]))
d['left_interface_crop'] = extra
d['left_interface_added_plan_area_m2'] = 5.192

# Remove the two now internal west-side edges. Preserve the other previously
# verified boundaries; their photographed terrain differs from this wall ramp.
profiles = [e for e in d['ground_edge_profiles']
            if e['edge'] != 'plinth_side_left'
            and not (abs(e['a'][1]-1.54)<1e-8 and abs(e['b'][1]-1.54)<1e-8
                     and max(e['a'][0],e['b'][0])<0)]
aa = np.array([-3.5,-.40]);bb = np.array([-3.5,1.54]);rows=[]
for t in np.linspace(0,1,41):
    uv=aa+(bb-aa)*t
    hs=[h for h in ns['hits'](uv) if h['normal_abs_z']>=.995]
    assert hs,uv
    rows.append(dict(t=float(t),uv=uv.tolist(),z=hs[0]['z'],hits=hs))
profiles.append(dict(edge='left_wall_foot_connection',a=aa.tolist(),b=bb.tolist(),
    minimum_normal_abs_z=.995,samples=rows))
d['ground_edge_profiles']=profiles

# Reconstruct only the low wall foot behind the new ground. Its top meets the
# measured source face at z=11.40; the wall base follows the surveyed setback.
tri=ns['t'];a=tri[:,0][:,[0,2]];b=tri[:,1][:,[0,2]]-a;c=tri[:,2][:,[0,2]]-a
det=b[:,0]*c[:,1]-b[:,1]*c[:,0];good=np.abs(det)>1e-10;safe=np.where(good,det,1)
wall=[]
for u in np.linspace(-3.51,-1.29,46):
    dp=np.array([u,11.40])-a
    r=(dp[:,0]*c[:,1]-dp[:,1]*c[:,0])/safe
    s=(b[:,0]*dp[:,1]-b[:,1]*dp[:,0])/safe
    ix=np.where(good&(r>=-1e-7)&(s>=-1e-7)&(r+s<=1+1e-7))[0]
    vs=tri[ix,0,1]+r[ix]*(tri[ix,1,1]-tri[ix,0,1])+s[ix]*(tri[ix,2,1]-tri[ix,0,1])
    front=[float(v) for v in vs if -1.2<v<-.5]
    assert front, u
    wall.append(dict(u=float(u),top_front_v=max(front)+.004))
d['left_wall_foot'] = dict(samples=wall,bottom_front_v=-.735,
    bottom_z=10.34,top_z=11.406,thickness_m=.24,
    basis='Inferred low masonry closure at the surveyed wing setback; top follows actual retained source face to close the local photo boundary.')
d['version']='SF1_v06'
d['v06_revision_basis']='v05 image review and actual image-ray/triangle probes separated the solid plinth from a retained 27-degree scan ramp. Replace only that low wall-foot/ground strip, using genuine low-slope source ground. Same official plinth/stair/canopy outlines and all camera poses.'
d['evidence_tiers']['inferred'].append('v06 low wall-foot closure and side-apron continuation are inferred construction; source-ground fit is relative agreement, not survey accuracy. Added crop is 5.192m2 below 411.40m LN02, within existing outer forecourt bounding extents.')
path.write_text(json.dumps(d,indent=2),encoding='utf-8')
(P/'derived/v06_left_interface_preparation.json').write_text(json.dumps(dict(
    version=d['version'],extra_crop_box_uvz=extra,added_plan_area_m2=5.192,
    total_plan_area_m2=outline.area,ground=d['left_interface_ground'],
    wall_foot=d['left_wall_foot'],unchanged_measured_shapes=['wall_outlines','steps','canopy'],
    old_source_ramp_normal_abs_z=.8953114121302668,
    not_publicly_accepted=True),indent=2),encoding='utf-8')
print(d['version'],'extra crop',extra,'ground fit RMSE',d['left_interface_ground']['fit_rmse_m'])
