"""Associate existing review-ray hits with cached official building identities.

This is a read-only investigation, not a facade design or permission to assume
that all wings of a footprint share the same window rhythm.
"""
import hashlib,json
from shapely.geometry import shape,Point
from workspace_paths import read_path,write_path

ray_file=read_path('evidence/G1_027r2/context_pixel_probe.json')
av_file=read_path('sources/features/av_bo_boflaeche_a.geojson')
probe=json.loads(ray_file.read_text());features=json.loads(av_file.read_text())['features']
buildings=[(f,shape(f['geometry'])) for f in features if f['geometry'] and 'Gebaeude' in str(f['properties'].get('art_txt'))]
pixels=[[97,234],[148,362],[706,311],[867,325]]
rows=[]
for sample in probe['samples']:
    if sample['camera']!='BD_QA_EAST' or sample['pixel'] not in pixels:continue
    hit=sample['hits'][0];local=hit['local_point'];point=Point(local[0]+2683775,local[1]+1246700)
    near=[]
    for feature,geom in buildings:
        distance=geom.distance(point)
        if distance<6:
            near.append(dict(source_id=feature['id'],egid=feature['properties'].get('gwr_egid'),
                use=feature['properties'].get('art_txt'),distance_m=float(distance),contains=geom.covers(point)))
    rows.append(dict(pixel=sample['pixel'],photo_object=hit['object'],local_point=local,
                     nearby_official_footprints=sorted(near,key=lambda x:x['distance_m'])))
assert len(rows)==4
report=dict(basis='Unchanged BD_QA_EAST camera and existing photo-ray observations; nearest AV identities, not facade dimensions.',
    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ray_file,av_file]},points=rows,
    source_identity_only=True,facade_design_complete=False,scene_modified=False)
write_path('derived/facade_identity/bridge_view_candidates.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(points=len(rows),nearest_egids=[r['nearby_official_footprints'][0]['egid'] for r in rows],scene_modified=False)))
