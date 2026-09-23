"""Reconcile public underpass and bridge identities before authoring a profile.

The output is survey context, not a solved or accepted pedestrian connection.
No heights are invented to force clearance through simplified bridge extrusions.
"""
from pathlib import Path
import hashlib,json,struct
import numpy as np
from shapely.geometry import Point,shape,mapping
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'derived/bellevue/quaibruecke_connection';DEST.mkdir(exist_ok=True)
source=ROOT/'derived/bellevue/riviera_lower/context.json'
existing=json.loads(source.read_text(encoding='utf-8'))
known={q['id']:q for q in existing['features']}
underpass=shape(known['av_ei_flaechenelement_a.39461']['geometry'])
north=shape(known['av_bo_boflaeche_a.40750']['geometry'])
complete_structure=shape(known['view_kuba_flaechen.477']['geometry'])
scope_raw=json.loads((ROOT/'planning/g1_scope.geojson').read_text(encoding='utf-8'))
scope=unary_union([shape(q['geometry']) for q in scope_raw['features']])
selected=[];receipts={}
for filename in ['av_bo_boflaeche_a.geojson','av_ei_flaechenelement_a.geojson','tbl_routennetz.geojson']:
    path=ROOT/'sources/features'/filename
    receipts[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    for f in json.loads(path.read_text(encoding='utf-8'))['features']:
        g=shape(f['geometry'])
        if g.distance(complete_structure)<.30:
            selected.append(f)
shared=north.boundary.intersection(underpass.boundary)
neighbours=[]
for f in selected:
    g=shape(f['geometry']);props=f['properties']
    if f['id'].startswith('av_bo') and g.distance(underpass)<.05:
        neighbours.append({'id':f['id'],'type':props.get('art_txt'),
                           'area_m2':g.area,'distance_to_underpass_m':g.distance(underpass),
                           'shared_boundary_length_m':g.boundary.intersection(underpass.boundary).length})
report={'underpass_area_m2':underpass.area,'north_approach_area_m2':north.area,
        'whole_kuba_pedestrian_structure_m2':complete_structure.area,
        'north_joint_distance_m':north.distance(underpass),'north_joint_boundary_length_m':shared.length,
        'north_plan_overlap_m2':north.intersection(underpass).area,
        'north_boundary_within_1mm_of_underpass_m':north.boundary.intersection(underpass.buffer(.001)).length,
        'plan_contact_is_not_proof_of_vertical_connection':True,
        'underpass_inside_g1_fraction':underpass.intersection(scope).area/underpass.area,
        'whole_kuba_inside_g1_fraction':complete_structure.intersection(scope).area/complete_structure.area,
        'adjacent_land_cover':neighbours,
        'distinct_structures':{k:known[k]['properties'] for k in ['view_kuba_flaechen.477','view_kuba_flaechen.502','view_kuba_flaechen.552']},
        'unresolved':['Underpass walking-floor profile and actual clear height are not supplied by the simplified roof extrusion.',
                      'Hohlraum Bellevue is a separate bridge/void structure, not a public room to invent or open.',
                      'The1985 bridge article is not the separate196-197 underpass article; latter diagrams were not obtained.',
                      'Current2015-renovated underpass lining/lighting and south approach remain to be reconciled before authoring.'],
        'geometry_authored':False,'natural_use_verified':False}

# Raw photo support candidates for profile diagnosis. Low horizontal faces may
# be water or scan artifacts; do not automatically promote them to floor samples.
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
triangles=[];nodes=[]
for item in manifest['items']:
    m=np.array(item['mbs'])
    if Point(m[:2]).distance(underpass)>m[3]:continue
    raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
    xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3,3)+m[:3]
    cent=xyz.mean(1)
    normal=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);size=np.linalg.norm(normal,axis=1)
    mask=(cent[:,2]>404.5)&(cent[:,2]<408)&(abs(normal[:,2])>.85*size)&(size>.08)
    for i in np.flatnonzero(mask):
        if underpass.buffer(-.25).covers(Point(cent[i,:2])):
            triangles.append(xyz[i]);nodes.append(item['node'])
triangles=np.array(triangles).reshape(-1,3,3)
np.savez_compressed(DEST/'unclassified_photo_profile_candidates.npz',triangles=triangles,nodes=np.array(nodes))
report['unclassified_photo_support_count']=len(triangles)
report['no_photo_candidate_assumed_walkable_floor']=True
(DEST/'context.json').write_text(json.dumps({'origin':existing['origin'],'known_features':list(known.values()),
    'nearby_features':selected,'source_sha256':receipts,'base_context_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'report':report},ensure_ascii=False,indent=2),encoding='utf-8')

fig,ax=plt.subplots(figsize=(8,9),dpi=150)
for ident,color in [('view_kuba_flaechen.502','#bec3cb'),('view_kuba_flaechen.552','#d4c2ae'),
                    ('view_kuba_flaechen.477','#99b0a9'),('av_bo_boflaeche_a.40750','#538eac'),
                    ('av_ei_flaechenelement_a.39461','#957ba9')]:
    g=shape(known[ident]['geometry'])
    for part in ([g] if g.geom_type=='Polygon' else g.geoms):
        xy=np.array(part.exterior.coords)[:,:2]-np.array(existing['origin'][:2])
        ax.fill(xy[:,0],xy[:,1],facecolor=color,alpha=.35,edgecolor=color,lw=1)
    pos=np.array(g.representative_point().coords[0])[:2]-np.array(existing['origin'][:2])
    if ident=='view_kuba_flaechen.477':pos=np.array([-265.,98.])
    ax.text(*pos,ident.split('.')[-1],fontsize=8,clip_on=True)
if len(triangles):
    pts=triangles.mean(1);sc=ax.scatter(pts[:,0]-existing['origin'][0],pts[:,1]-existing['origin'][1],c=pts[:,2],s=12)
    fig.colorbar(sc,ax=ax,label='Unclassified photo face height (LN02 m)')
ax.set_xlim(-305,-240);ax.set_ylim(60,202);ax.set_aspect('equal');ax.grid(alpha=.15)
ax.set_xlabel('East from project origin (m)');ax.set_ylabel('North from project origin (m)')
ax.set_title('Quaibruecke public connection: distinct source structures')
fig.tight_layout();fig.savefig(DEST/'source_connection_plan.png');plt.close(fig)
print(json.dumps(report,indent=2))
