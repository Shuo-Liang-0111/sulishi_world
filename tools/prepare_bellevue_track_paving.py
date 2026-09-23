"""Photo-constrained material segmentation; cadastral XY and authored grades preserved.

These finish boundaries are interpreted, not an official engineering material layer.
Occlusion beneath trams/canopies and slab joint spacing remain explicitly inferred.
"""
import json
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,LineString,box,mapping
from shapely.ops import unary_union
from shapely.affinity import translate
from shapely import constrained_delaunay_triangles
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/transport';origin=np.array([2683775.,1246700.])
payload=json.loads((OUT/'road_input.json').read_text());road=shape(payload['road_mask'])
cad=json.loads((ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
byid={f['id']:shape(f['geometry']) for f in cad}
axes=json.loads((OUT/'source_features.json').read_text())['rail_lines']
# Clip the two actual curved track axes. A single straight quadrilateral had
# crossed the intervening passenger island and incorrectly painted the road east of it.
east_corridor=unary_union([shape(axes[i]['geometry']).buffer(1.4,cap_style=2) for i in [11,13,15,16]])
east_corridor=east_corridor.intersection(box(2683580,1246809,2683628,1246858)).intersection(road)
# The central tram-only triangle/loop has mineral paving visible in SWISSIMAGE.
# The west/east corridors are traced from visible tonal/panel boundaries; masked
# portions are continued along the surveyed track direction rather than invented lanes.
zones=[{'id':'southern_tram_reservation','geometry':byid['av_bo_boflaeche_a.106988'].intersection(road),'basis':'AV polygon plus orthophoto and south-facing operator photo; exact under-tree finish inferred'},
       {'id':'west_platform_trackbed','geometry':Polygon([(2683515,1246827.5),(2683576,1246869),(2683582,1246864),(2683521,1246822.5)]).intersection(road),'basis':'Manual orthophoto corridor interpretation; curved ends and junction continuation approximate'},
       {'id':'east_platform_trackbed','geometry':east_corridor,'basis':'Actual curved AV rail axes 40430/40432/40434/40435; 1.4 m half-width and occluded finish inferred; clipped to AV road footprint'}]
concrete=unary_union([z['geometry'] for z in zones]);local=translate(concrete,-origin[0],-origin[1])
segments=[([2683532,1246835],[2683578,1246866],'west'),([2683540,1246828],[2683614,1246810],'south'),([2683587,1246859],[2683620,1246808],'east')]
joint_lines=[]
for start,end,name in segments:
    a=np.array(start,dtype=float);b=np.array(end,dtype=float);d=b-a;length=np.linalg.norm(d);d/=length;n=np.array([-d[1],d[0]])
    for s in np.arange(1.5,length,3.6):
        p=a+d*s;line=LineString([p-n*4,p+n*4]).intersection(concrete)
        if not line.is_empty:joint_lines.append(line)
joints=unary_union([l.buffer(.004,cap_style=2) for l in joint_lines]).intersection(concrete)
jl=translate(joints,-origin[0],-origin[1]);parts=[];area_counts={'asphalt':0.,'concrete':0.,'joint':0.}
def polys(g):return [v for v in (g.geoms if hasattr(g,'geoms') else [g]) if v.geom_type=='Polygon' and v.area>1e-10]
def split_triangle(t,g,dz):
    out=[];base=np.array(t);a=(base[1:,:2]-base[0,:2]).T;det=np.linalg.det(a)
    if abs(det)<1e-13:return out
    for p in polys(g):
        for tri in constrained_delaunay_triangles(p).geoms:
            coords=list(tri.exterior.coords)[:3];v=[]
            for x,y in coords:
                w=np.linalg.solve(a,np.array([x,y])-base[0,:2]);v.append([x,y,float(base[0,2]+w@(base[1:,2]-base[0,2])+dz)])
            if np.cross(np.array(v[1])-v[0],np.array(v[2])-v[0])[2]<0:v.reverse()
            out.append(v)
    return out
for part in payload['pieces']:
    if part['kind']!='road_asphalt':continue
    buffers={k:[] for k in area_counts}
    for triangle in part['triangles']:
        p=Polygon(np.array(triangle)[:,:2]);in_concrete=p.intersection(local)
        groups={'asphalt':p.difference(local),'concrete':in_concrete.difference(jl),'joint':in_concrete.intersection(jl)}
        for key,g in groups.items():
            area_counts[key]+=g.area;buffers[key].extend(split_triangle(triangle,g,-.003 if key=='joint' else 0))
    for kind,triangles in buffers.items():
        if triangles:parts.append({'id':part['id']+'_'+kind,'source_id':part['id'],'kind':kind,'triangles':triangles})
records={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':z['id'],'basis':z['basis'],'evidence':['sources/references/swissimage-bellevue-detail.jpg','sources/references/architecture/belcafe-exterior.jpg'],'status':'interpreted_not_surveyed_material_boundary'},'geometry':mapping(z['geometry'])} for z in zones]}
(OUT/'paving_zones.geojson').write_text(json.dumps(records,indent=2))
report={'area_m2':area_counts,'source_road_input_sha256':__import__('hashlib').sha256((OUT/'road_input.json').read_bytes()).hexdigest(),'plan_geometry_changed':False,'road_grade_changed':False,'joint_width_m_inferred':.008,'joint_module_m_inferred':3.6,'joint_depth_m_inferred':.003,'status':'working interpretation; masked material edges and precise joint locations not surveyed','source_files':['sources/references/swissimage-bellevue-detail.jpg','sources/references/architecture/belcafe-exterior.jpg']}
(OUT/'paving_input.json').write_text(json.dumps({'report':report,'parts':parts},separators=(',',':')))
fig,ax=plt.subplots(figsize=(12,12),layout='constrained');ax.imshow(Image.open(ROOT/'sources/references/swissimage-bellevue-detail.jpg'),extent=[2683500,2683650,1246765,1246910]);
for z in zones:
    for p in polys(z['geometry']):
        xy=np.array(p.exterior.coords);ax.fill(xy[:,0],xy[:,1],alpha=.15,color='#00ffff');ax.plot(xy[:,0],xy[:,1],c='#00ffff',lw=.7)
for l in joint_lines:
    for part in (l.geoms if hasattr(l,'geoms') else [l]):
        if part.geom_type=='LineString':xy=np.array(part.coords);ax.plot(xy[:,0],xy[:,1],c='#ffbb00',lw=.5)
ax.set_xlim(2683500,2683650);ax.set_ylim(1246765,1246910);ax.set_aspect('equal');ax.ticklabel_format(style='plain',useOffset=False);ax.set_title('Paving interpretation / cyan boundary; orange joints inferred, not survey')
fig.savefig(OUT/'paving_interpretation.png',dpi=145);print(json.dumps(report))
