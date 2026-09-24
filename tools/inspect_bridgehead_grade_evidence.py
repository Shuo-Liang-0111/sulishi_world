"""Compare conflicting bridgehead grades with cached, unfiltered source data.

Horizontal photographic faces may be vehicles/objects. This is diagnostic
evidence, not an automatic ground classifier or permission to move geometry.
"""
from pathlib import Path
import json,struct
import numpy as np
from shapely.geometry import Point,Polygon,box,shape
from shapely import STRtree
from shapely.ops import nearest_points
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_deck'
origin=np.array([2683775,1246700,400]);region=box(2683488,1246808,2683522,1246838)
av={f['id']:shape(f['geometry']) for f in json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']}
road=av['av_bo_boflaeche_a.549'];bank=av['av_bo_boflaeche_a.36232']
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
samples=[];nodes=[]
for item in manifest['items']:
    m=np.array(item['mbs'])
    if Point(m[:2]).distance(region)>m[3]:continue
    raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
    triangles=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3,3)+m[:3]
    centre=triangles.mean(1);cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);norm=np.linalg.norm(cross,axis=1)
    selected=(centre[:,2]>407)&(centre[:,2]<413)&(abs(cross[:,2])>.92*norm)&(norm>.04)
    for i in np.flatnonzero(selected):
        c=centre[i];point=Point(c[:2])
        if region.covers(point):
            kind='road' if road.covers(point) else 'upper_bank' if bank.covers(point) else 'other'
            samples.append(dict(xyz=c.tolist(),node=str(item['node']),face=int(i),kind=kind,area_m2=float(norm[i]/2)))
    nodes.append(str(item['node']))
terrain=np.load(R/'derived/bellevue/bridgehead_bank/survey_terrain.npz')['triangles']
polygons=[Polygon(t[:,:2]) for t in terrain];tree=STRtree(polygons)
def survey(p):
    i=int(tree.nearest(Point(p)));q=np.array(nearest_points(polygons[i],Point(p))[0].coords[0]);t=terrain[i]
    uv=np.linalg.solve((t[1:,:2]-t[0,:2]).T,q-t[0,:2]);return float(t[0,2]+uv@(t[1:,2]-t[0,2]))
seams=json.loads((R/'evidence/G1_027/approach_seam_diagnosis.json').read_text())
rows=[]
for r in seams:
    if r['old_raised']==r['new_raised']:continue
    xy=np.array(r['new_xy'])+origin[:2];near=[s for s in samples if s['kind']=='road' and np.linalg.norm(np.array(s['xyz'])[:2]-xy)<3]
    rows.append(dict(xy_lv95=xy.tolist(),authored_new_z_ln02_m=r['new_z']+400,authored_old_z_ln02_m=r['old_z']+400,
        survey_tin_z_ln02_m=survey(xy),nearby_raw_road_faces=len(near),
        raw_road_z_quantiles=np.quantile([s['xyz'][2] for s in near],[.1,.5,.9]).tolist() if near else None))
result=dict(bounds_lv95=list(region.bounds),source_nodes=nodes,horizontal_photo_candidates=samples,transitions=rows,
            old_station_road_filter_upper_z_ln02_m=409.2,
            caution='Horizontal source faces can contain vehicles; no source is silently promoted to ground truth. No scene edited.')
(D/'grade_evidence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(cached_nodes=len(nodes),raw_horizontal_candidates=len(samples),transitions=len(rows),first=rows[:3])))
