"""Check prepared source coverage and open bridge ends before Blender authoring.

These are plan/height checks, not saved-scene, collision or visual acceptance.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from shapely.geometry import shape,Polygon,LineString,Point
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_deck'
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
parts=P['parts'];report=P['report']
assert P['version']=='G1_027'
assert not report['g1_scope_expanded'] and not report['old_geometry_moved']
for path,digest in P['source_sha256'].items():
    assert hashlib.sha256((R/path).read_bytes()).hexdigest()==digest,path

def union_roles(roles):
    return unary_union([shape(p['plan']) for p in parts if p['role'] in roles])

raised=unary_union([shape(z['geometry']) for z in P['zones'] if z['raised']])
road=unary_union([shape(z['geometry']) for z in P['zones'] if not z['raised']])
actual_raised=union_roles({'asphalt_walk'})
actual_road=union_roles({'asphalt_road','asphalt_track','rail','drain'})
errors={'walk_cycle_m2':raised.symmetric_difference(actual_raised).area,
        'road_track_m2':road.symmetric_difference(actual_road).area,
        'rail_head_m2':shape(P['heads']).symmetric_difference(union_roles({'rail'})).area,
        'groove_m2':shape(P['channels']).difference(shape(P['heads'])).symmetric_difference(union_roles({'drain'})).area}
assert max(errors.values())<.001,errors
for part in parts:
    vertices=np.array(part['vertices']);assert np.isfinite(vertices).all(),part['name']
    assert all(len(f)>=3 and min(f)>=0 and max(f)<len(vertices) for f in part['faces']),part['name']

base=json.loads((D/'existing_approaches.json').read_text())
old=unary_union([Polygon(np.array(t)[:,:2]+O[:2]) for row in base['surfaces'] for t in row['triangles']])
assert old.intersection(shape(P['surface'])).area<.001
frame=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
along=np.array(frame['bridge_along'])
av={f['id']:shape(f['geometry']) for f in json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']}
guard_checks=[]
for guard in P['guards']:
    points=np.array(guard['path']);delta=np.diff(points,axis=0)
    alignment=np.abs(delta@along)/np.linalg.norm(delta,axis=1)
    footprint=av[guard['source']].intersection(shape(P['bridge']))
    assert alignment.min()>.98 and all(footprint.buffer(.001).covers(Point(p)) for p in points)
    line=LineString(points)
    assert 100<line.length<130
    guard_checks.append(dict(source=guard['source'],length_m=line.length,
                             min_alignment=float(alignment.min()),transverse_end_returns=False))

source_masts={f['id']:f for f in json.loads((R/'sources/features/quaibruecke_deck/fahrleitungen_mast.geojson').read_text())['features']}
for mast in P['masts']:
    original=source_masts[mast['id']]
    assert np.array_equal(mast['xy'],shape(original['geometry']).centroid.coords[0])
    assert mast['base_ln02_m']==original['properties']['hoehemastuk']
    assert mast['top_ln02_m']==original['properties']['hoehemastok']
assert len(P['masts'])==12

fig,ax=plt.subplots(figsize=(14,4.8))
colors={'walk':'#dbc592','cycle':'#a7c6b3','road':'#999fa6','track':'#c1b9af'}
for z in P['zones']:
    g=shape(z['geometry']);polygons=[g] if g.geom_type=='Polygon' else list(g.geoms)
    for poly in polygons:
        coords=np.array(poly.exterior.coords)-O[:2]
        ax.fill(*coords.T,color=colors[z['kind']],edgecolor='white',linewidth=.2)
for guard in P['guards']:
    p=np.array(guard['path'])-O[:2];ax.plot(*p.T,color='#263d4d',lw=2)
for mast in P['masts']:
    p=np.array(mast['xy'])-O[:2];ax.plot(*p,'ko',ms=3)
    ax.text(*p,mast['id'].split('.')[-1],fontsize=7)
ax.set_aspect('equal');ax.set_xlabel('East from project origin (m)');ax.set_ylabel('North (m)')
ax.set_title('G1_027 preparation: cadastral zones, open bridge ends; guard fabrication inferred')
fig.tight_layout();fig.savefig(D/'plan.png',dpi=120);plt.close(fig)
result=dict(input_sha256=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest(),
            coverage_difference_m2=errors,guards=guard_checks,source_masts_preserved=12,
            blender_authored=False,visual_acceptance=False,natural_use_verified=False,
            unresolved=['Contact wires require continuous support, attachment and height checks before authoring.',
                        'Mast base/ground differences require explicit inferred foundation details.',
                        'Existing photographic deck replacement is not yet prepared or applied.'])
(D/'preparation_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
