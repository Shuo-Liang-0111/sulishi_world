"""Inspect cached survey geometry and photographic levels at the Riviera edge.

This creates diagnostics only. A flat AV polygon is not a measured walkway level,
and a covered-water polygon must not be converted into an exposed water surface.
"""
from pathlib import Path
import hashlib
import json
import struct

import numpy as np
from shapely.geometry import Point, Polygon, box, shape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'derived/bellevue/riviera_quay'
OUT.mkdir(parents=True, exist_ok=True)
ORIGIN = np.array([2683775., 1246700., 400.])
window = box(2683445,1246836,2683515,1247012)
selected = []
source_hashes = {}
for file, ids in [('av_bo_boflaeche_a.geojson',[145,40750,24105,20161,5939]),
                  ('av_ei_flaechenelement_a.geojson',[18091,20735,28347,47309,35223,35317,35398,
                     37826,37827,37828,37832,38011,38597,36814,36825])]:
    path = ROOT/'sources/features'/file
    source_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for feature in json.loads(path.read_text(encoding='utf-8'))['features']:
        if feature['properties'].get('objectid') in ids:
            selected.append(feature)
line_path=ROOT/'sources/features/av_ei_linienelement.geojson'
source_hashes[str(line_path.relative_to(ROOT))]=hashlib.sha256(line_path.read_bytes()).hexdigest()
lines=[f for f in json.loads(line_path.read_text())['features']
       if f['properties'].get('art_txt')=='wichtige_Treppe' and shape(f['geometry']).intersects(window)]

terrain = {}
for path in (ROOT/'sources/terrain').glob('*.geojson'):
    for feature in json.loads(path.read_text(encoding='utf-8'))['features']:
        if shape(feature['geometry']).intersects(window): terrain[feature['id']] = feature
tt = np.array([f['geometry']['coordinates'][0][:3] for f in terrain.values()])

manifest_path = ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json'
manifest = json.loads(manifest_path.read_text())
all_tri = []; all_nodes = []; all_ids = []
for item in manifest['items']:
    sphere = np.asarray(item['mbs'])
    if Point(sphere[:2]).distance(window) > sphere[3]: continue
    raw = Path(item['geometry']).read_bytes()
    count = struct.unpack_from('<I',raw)[0]
    tri = (np.frombuffer(raw,dtype='<f4',count=count*3,offset=8).reshape(-1,3)+sphere[:3]).reshape(-1,3,3)
    c = tri.mean(axis=1)
    keep = np.flatnonzero((c[:,0]>=window.bounds[0])&(c[:,0]<=window.bounds[2])&
                          (c[:,1]>=window.bounds[1])&(c[:,1]<=window.bounds[3])&
                          (c[:,2]>402)&(c[:,2]<412))
    all_tri.extend(tri[keep]); all_nodes.extend([item['node']]*len(keep)); all_ids.extend(keep.tolist())
tri = np.asarray(all_tri); c = tri.mean(axis=1)
normal = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
area = np.linalg.norm(normal,axis=1)/2
horizontal = (abs(normal[:,2])>1.8*area)&(area>.004)
np.savez_compressed(OUT/'source_geometry.npz',photo_triangles=tri,photo_nodes=np.array(all_nodes),
                    photo_triangle_ids=np.array(all_ids),terrain_triangles=tt)
(OUT/'sources.json').write_text(json.dumps({'origin':ORIGIN.tolist(),'features':selected,'step_lines':lines,
    'source_hashes':source_hashes,'terrain_ids':list(terrain),'photo_manifest':str(manifest_path.relative_to(ROOT)),
    'photo_samples':len(tri),'horizontal_samples':int(horizontal.sum()),
    'basis':'Cached authoritative XY boundaries and TIN; photographic levels are diagnostic observations, not new survey.'},
    ensure_ascii=False,indent=2),encoding='utf-8')

fig,(ax,bx)=plt.subplots(1,2,figsize=(12,12),dpi=150)
im=plt.imread(ROOT/'sources/references/swissimage-context.jpg')
for axis in (ax,bx): axis.imshow(im,extent=[2683420,2684200,1246300,1247110])
colors=['#fff000','#24ffcf','#fff','#ffaa33','#9eff70','#ff38e4','#ff5533','#55aaff','#d6ff30']
for i,feature in enumerate(selected):
    color=colors[i%len(colors)]
    g=shape(feature['geometry'])
    for axis in (ax,bx):
        axis.plot(*g.exterior.xy,c=color,lw=1)
        p=g.representative_point(); axis.text(p.x,p.y,feature['id'].split('.')[-1],fontsize=7,
            color=color,bbox={'facecolor':'black','alpha':.6,'pad':1},clip_on=True)
for f in lines:
    g=shape(f['geometry'])
    for axis in (ax,bx):axis.plot(*g.xy,c='#60eaff',lw=.45)
ax.set_xlim(2683445,2683515);ax.set_ylim(1246836,1247012)
bx.set_xlim(2683481,2683510);bx.set_ylim(1246840,1246902)
for axis in (ax,bx):axis.set_aspect('equal');axis.ticklabel_format(useOffset=False,style='plain');axis.tick_params(labelsize=6)
ax.set_title('Cached AV sources | whole river edge')
bx.set_title('South wall, access stair and covered-water footprint')
fig.tight_layout();fig.savefig(OUT/'source_plan.png');plt.close(fig)

anchor=np.array([2683500.277,1246895.644]);along=np.array([-.3363364,.9417419]);across=np.array([-.9417419,-.3363364])
delta=c[:,:2]-anchor; stations=delta@along; offsets=delta@across
fig,axes=plt.subplots(3,1,figsize=(10,10),dpi=150)
for axis,interval in zip(axes,[(4,28),(35,65),(72,105)]):
    keep=horizontal&(stations>=interval[0])&(stations<interval[1])&(offsets>-3)&(offsets<14)
    axis.scatter(offsets[keep],c[keep,2],s=np.minimum(area[keep]*9,24),c=stations[keep],cmap='viridis')
    axis.set_xlim(-3,14);axis.set_ylim(404,410);axis.grid(alpha=.3)
    axis.set_title(f'Original photographic horizontal faces | along {interval} m')
    axis.set_xlabel('Distance riverward from upper sidewalk AV edge (m)');axis.set_ylabel('LN02 m')
fig.tight_layout();fig.savefig(OUT/'photo_cross_sections.png');plt.close(fig)
print(json.dumps({'features':len(selected),'photo_triangles':len(tri),'terrain_triangles':len(tt),
                  'horizontal_faces':int(horizontal.sum()),'output':str(OUT)}))
