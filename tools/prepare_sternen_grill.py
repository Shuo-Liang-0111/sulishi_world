"""Dimension a bounded Theaterstrasse 22 frontage reconstruction from AV/roof data.

The roof and footprint are measured constraints. Window, joinery, floor and
material details are photographic inference from the owner's two exterior views.
"""
from pathlib import Path
import ast, hashlib, json
import numpy as np
from shapely.geometry import Polygon
from shapely import constrained_delaunay_triangles
from workspace_paths import read_path, write_path

origin=np.array([2683775.,1246700.,400.])
avpath=read_path('sources/features/av_bo_boflaeche_a.geojson')
av=next(f for f in json.loads(avpath.read_text())['features'] if f['id']=='av_bo_boflaeche_a.50487')
ring=np.array(av['geometry']['coordinates'][0])-origin[:2]
A=ring[0];B=ring[5];U=(B-A)/np.linalg.norm(B-A);N=np.array([U[1],-U[0]])
width=float(np.linalg.norm(B-A))
roofsource=read_path('sources/features/bauten_dachmodell_3d.geojson')
roof=[f for f in json.loads(roofsource.read_text())['features'] if f['properties'].get('egid')==302060199]
assert len(roof)==5
roofpath=write_path('derived/sternen_grill/official_roof_features.json')
roofpath.write_text(json.dumps(roof))
# Front eave endpoints are directly present in the official source roof.
eave=25.164
assert abs(width-13.236)<.002
spec=dict(version='G1_027r5',base_version='G1_027r4',egid=302060199,address='Theaterstrasse 22',
    AV=av['id'],origin=origin.tolist(),A=A.tolist(),U=U.tolist(),N=N.tolist(),width=width,
    depth=16.03,floor_z=8.57,balcony_floor_z=11.78,upper_start_z=15.12,eave_z=eave,
    levels=[dict(bottom=15.12,top=18.47,sill=15.75,head=18.01),
            dict(bottom=18.47,top=21.81,sill=19.09,head=21.36),
            dict(bottom=21.81,top=eave,sill=22.43,head=24.71)],
    front_centers=[1.80,5.01,8.22,11.43],side_centers=[2.04,5.91,9.78,13.65],window_width=2.06,
    footprint=ring.tolist(),roof_features=roof,
    # Local u/v/z boxes: strip immediately behind each reconstructed street face.
    photo_cut_boxes=[[-.045,width+.10,-1.80,1.65,8.46,25.24],
                     [width-1.80,width+1.0,-16.03,1.65,8.46,25.24]],
    roof_cut_box=[-.08,width+.10,-16.03,.25,25.24,31.0],
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [avpath,roofpath,
        read_path('sources/references/sternen_grill/psp_1.jpg'),read_path('sources/references/sternen_grill/psp_2.jpg')]},
    basis='AV footprint and official roof constrain position/envelope. PSP exterior photographs constrain four front bays, three office levels, recessed restaurant band, balcony, stone and metal family. Exact floor divisions, opening sizes, fabrication, glazing and shallow unopened interiors are inferred. Rear facade/interior circulation are not reconstructed in this batch.',
    floor_basis='Three existing source-ground rays 8.486,8.511,8.570 m and nearby authored pavement 8.592 m; threshold 8.570 m is inferred, not official engineering level.')

# Bounded residual bridge fragments, separate from the building footprint.
probe_path=read_path('derived/bridge_residuals/source_probe.json');probe=json.loads(probe_path.read_text())
tree=ast.parse(read_path('tools/blender_probe_bridge_context.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='connected_face_components')
namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'diagnostic_components','exec'),namespace)
selected={'CTX_I3S_34256':[2,3,4,5,6,7],'CTX_I3S_34216':[2]};cuts=[]
for row in probe['context']:
    if row['name'] not in selected:continue
    cc=namespace['connected_face_components'](row['vertices'],row['faces'])
    parts=[c for c in cc if c['component'] in selected[row['name']]]
    assert len(parts)==len(selected[row['name']])
    for c in parts:
        assert -279<c['min'][0]<-266 and c['max'][0]<-266
        assert 111<c['min'][1] and c['max'][1]<120
        assert 10<c['min'][2] and c['max'][2]<14.5
    cuts.append(dict(object=row['name'],mesh_digest=row['mesh_digest'],
        faces=sorted(i for c in parts for i in c['face_ids']),components=parts,
        basis='Detached distorted source sheets above rebuilt public bridgehead. Original photo retained; ground/railing/poles already have physical authored counterparts. No distant facade is removed by this cleanup.'))
assert sum(len(c['faces']) for c in cuts)==65
spec['bridge_residual_cuts']=cuts
spec['residual_probe_sha256']=hashlib.sha256(probe_path.read_bytes()).hexdigest()
roof_triangles=[];roof_audit=[]
for feature in roof:
    if feature['properties']['type']=='GroundSurface':continue
    for pi,rings in enumerate(feature['geometry']['coordinates']):
        rings=[np.array(r,float)-origin for r in rings]
        if max(r[:,2].max() for r in rings)<25.16:continue
        outer=rings[0];normal=sum((np.cross(a,b) for a,b in zip(outer[:-1],outer[1:])),np.zeros(3))
        if np.linalg.norm(normal)<1e-8:continue
        normal/=np.linalg.norm(normal);drop=int(np.argmax(abs(normal)));axes=[i for i in range(3) if i!=drop]
        poly=Polygon(outer[:,axes],holes=[r[:,axes] for r in rings[1:]])
        repaired=not poly.is_valid
        if repaired:poly=poly.buffer(0)
        allpoints=np.concatenate(rings);extra=0;count=0
        residual=float(np.max(abs((allpoints-outer[0])@normal)))
        for tri in constrained_delaunay_triangles(poly).geoms:
            if tri.area<1e-10:continue
            vv=[]
            for xy in list(tri.exterior.coords)[:3]:
                xy=np.array(xy);j=np.argmin(np.linalg.norm(allpoints[:,axes]-xy,axis=1))
                if np.linalg.norm(allpoints[j,axes]-xy)<1e-6:p=allpoints[j].copy()
                else:
                    p=outer[0].copy();p[axes]=xy;p[drop]=outer[0,drop]-(xy-outer[0,axes])@normal[axes]/normal[drop];extra+=1
                vv.append(p.tolist())
            roof_triangles.append(dict(source=feature['id'],type=feature['properties']['type'],polygon=pi,vertices=vv));count+=1
        roof_audit.append(dict(source=feature['id'],polygon=pi,rings=len(rings),triangles=count,geometry_repaired=repaired,
            interpolated_vertices=extra,max_source_plane_residual_m=residual))
spec['roof_triangles']=roof_triangles;spec['roof_triangulation_audit']=roof_audit
write_path('derived/sternen_grill/build_input.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
print(json.dumps(dict(width=width,front_bays=4,side_bays=4,office_levels=3,bridge_residual_faces=65,exact_roof_features=len(roof))))
