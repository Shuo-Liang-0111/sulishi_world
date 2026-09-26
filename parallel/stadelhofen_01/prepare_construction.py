"""Derive a bounded replay specification from measured outlines and inspected photos."""
from pathlib import Path
import json, numpy as np, hashlib
from shapely.geometry import Polygon, MultiPoint, box
from shapely.ops import unary_union
OUT=Path(__file__).resolve().parent;D=OUT/'derived'
s=json.loads((D/'site_spec.json').read_text());A=np.array(s['A']);U=np.array(s['U']);N=np.array(s['N']);origin=np.array(s['origin'])
def Q(x):
    xy=np.array(x)[:,:2]-origin[:2]-A
    return np.column_stack([xy@U,xy@N])
f={a['id']:a for a in json.loads((D/'entrance_survey_features.geojson').read_text())['features']}
stair=Q(f['av_ei_flaechenelement_a.8936']['geometry']['coordinates'][0])
walls=[Q(f['av_ei_flaechenelement_a.'+str(i)]['geometry']['coordinates'][0]) for i in [459,448]]
canopy=Q(f['av_ei_flaechenelement_a.44098']['geometry']['coordinates'][0])
# Four plan edges: outer/inner staircase polygon and its two surveyed tread lines.
i0=np.argmin(np.linalg.norm(stair-[.9156,1.5196],axis=1));i1=np.argmin(np.linalg.norm(stair-[11.0377,1.526],axis=1))
inner=stair[i0:i1+1]
outer=MultiPoint(stair).convex_hull
curves=[]
for ids in [[4289,4290,4291,4292,4293],[4294,4295,4975,4976,4977]]:
    curve=[]
    for num in ids:curve.extend(Q(f['av_ei_linienelement.'+str(num)]['geometry']['coordinates']).tolist())
    curves.append(np.array(curve))
def footprint(curve):
    pts=curve.tolist()+[[float(curve[-1,0]),-.60],[float(curve[0,0]),-.60]]
    return Polygon(pts).buffer(0)
outer=MultiPoint(stair.tolist()+[[-.0802,-.60],[12.0323,-.60]]).convex_hull
step_polys=[outer]+[footprint(c) for c in curves]+[footprint(inner)]
assert all(step_polys[i].buffer(.001).covers(step_polys[i+1]) for i in range(3))
samples=json.loads((D/'ground_source_samples.json').read_text())
rows=[]
for r in samples:
    if 0<r['u']<12 and r['v']>=4.05 and r['v']<=8:
        z=[h['z'] for h in r['hits'] if 9<h['z']<11]
        if z:rows.append([1,r['u'],r['v'],max(z)])
rr=np.array(rows);coef=np.linalg.lstsq(rr[:,:3],rr[:,3],rcond=None)[0];res=rr[:,3]-rr[:,:3]@coef
# The image-grounded landing is not a height observation: retain explicit uncertainty.
landing=11.28;rise=.155
steps=[]
for i,p in enumerate(step_polys):
    p=p.simplify(.002,preserve_topology=True)
    steps.append(dict(index=i,top_z=landing-rise*(3-i),bottom_z=10.34,outline=list(p.exterior.coords)[:-1],
        plan_source=['AV8936 outer edge','AV4289–4293','AV4294–4295 /4975–4977','AV8936 inner edge'][i]))
# Local replacement shell contains the apron and the two source-located side plinths.
scope=dict(u=[-1.30,13.25],v=[-.82,8.0],z=[9.8,15.80])
spec={**s,'scope_local':scope,'steps':steps,'wall_outlines':[list(Polygon(w).simplify(.002).exterior.coords)[:-1] for w in walls],
    'canopy_outline':canopy.tolist(),'landing_z':landing,'riser_m':rise,
    'ground_plane_coefficients':coef.tolist(),'ground_fit_samples':len(rows),'ground_fit_rmse_m':float(np.sqrt(np.mean(res**2))),
    'ground_fit_max_residual_m':float(np.abs(res).max()),
    'evidence_tiers':{
      'measured_xy':['AV38215 station building boundary, EGID2372568','AV44098 canopy outline','AV8936 and ten line elements for rounded four-step plan','AV448/459 flanking plinth outlines'],
      'source_mesh_z':['Visible forecourt samples v=4.05–8m used for graded apron and boundary matching','LOD2 canopy upper envelope 415.307m LN02 and first cornice approximately 415.79m'],
      'photograph_observed':['Three round-arched double doors with divided glass and solid lower panels','Glazed metal cantilever roof and decorative iron wall brackets; no invented freestanding columns','Four risers, two handrails, pale grey masonry, stone tread nosings','2010 photo in cantonal 2020 inventory is dated context, not contemporary operational proof'],
      'inferred':['Landing 411.28m LN02 and 155mm rises: image proportions tied to canopy/forecourt, not field survey; approximate uncertainty ±0.15m','Opening widths, jamb depths, masonry courses, bracket profiles, glass/metal thicknesses and fastener manufacture','Concealed cavity behind closed doors; no claimed public interior/interactive entrance','PBR finish family and wear distribution; not site-scanned optical measurements']},
    'source_paths':{},'base_native':'H:/MyWorld/ZurichWorld/native/G1_027r8_sternen_entrance_joinery.blend',
    'base_sha256':'beeec6979340d5edcdfd51b8fae27c3e19f857e96cb7e11b506c4c46f2f5290a'}
for p in [D/'entrance_survey_features.geojson',OUT/'sources/zh_heritage_stadelhofen_2020.pdf',OUT/'sources/heritage_entrance_photo_1.jpg']:
    spec['source_paths'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
# Bound source candidates by triangles; final replay additionally checks native fingerprints.
arr=np.load(D/'source_triangles.npz');q=arr['local'];ids=arr['node']
lo=q.min(axis=1);hi=q.max(axis=1);bounds=np.array([scope[k] for k in ['u','v','z']]);hit=np.all((hi>=bounds[:,0])&(lo<=bounds[:,1]),axis=1)
spec['candidate_old_objects']=['CTX_I3S_'+str(n) for n in np.unique(ids[hit])]
allman=json.loads(Path('F:/MyWorld/ZurichWorld/sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
spec['context_nodes']=[r['node'] for r in allman['items'] if np.linalg.norm(np.array(r['mbs'][:2])-(A+U*6+origin[:2]))<r['mbs'][3]+58]
spec['import_collection']='SF1_AUTHOR_ENTRANCE';spec['context_collection']='SF1_REFERENCE_CONTEXT_DO_NOT_MERGE'
(D/'build_input.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
print(json.dumps(dict(candidate_old_objects=spec['candidate_old_objects'],context_nodes=len(spec['context_nodes']),ground_fit=coef.tolist(),rmse=spec['ground_fit_rmse_m'],step_areas=[p.area for p in step_polys],scope=scope),indent=2))
