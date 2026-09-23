"""Non-destructive exact plan-mask cut of source photo triangles for the rebuilt island."""
import json,struct,argparse
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,Point,box
from shapely import constrained_delaunay_triangles

ROOT=Path(__file__).resolve().parents[1]
block=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
cut=shape(block['island']).union(shape(block['core_outline']))
parser=argparse.ArgumentParser();parser.add_argument('--road-surfaces',action='store_true');args=parser.parse_args()
if args.road_surfaces:
    road=json.loads((ROOT/'derived/bellevue/transport/road_input.json').read_text())
    cut=cut.union(shape(road['road_mask']))
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
out=[];removed=0;retessellated=0
for item in manifest['items']:
    m=item['mbs']
    if Point(m[:2]).distance(cut)>m[3]:continue
    raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
    xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3).astype(float)
    uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2).copy()
    world=(xyz+np.array(m[:3])).reshape(-1,3,3);ut=uv.reshape(-1,3,2)
    vv=[];uu=[];changed=False
    for tri,tex in zip(world,ut):
        poly=Polygon(tri[:,:2])
        if not poly.is_valid or poly.area<1e-9:
            if cut.contains(Point(tri[:,:2].mean(axis=0))):removed+=1;changed=True
            else:vv.extend((tri-np.array(m[:3])).tolist());uu.extend(tex.tolist())
            continue
        if not poly.intersects(cut):
            vv.extend((tri-np.array(m[:3])).tolist());uu.extend(tex.tolist());continue
        diff=poly.difference(cut);changed=True
        if diff.is_empty:removed+=1;continue
        if abs(diff.area-poly.area)<1e-10:
            vv.extend((tri-np.array(m[:3])).tolist());uu.extend(tex.tolist());continue
        retessellated+=1
        pieces=list(diff.geoms) if hasattr(diff,'geoms') else [diff]
        matrix=np.column_stack([tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2]])
        for piece in pieces:
            if piece.geom_type!='Polygon' or piece.area<1e-9:continue
            for sub in constrained_delaunay_triangles(piece).geoms:
                xy=np.array(list(sub.exterior.coords)[:3]);weights=np.linalg.solve(matrix,(xy-tri[0,:2]).T).T
                coords=tri[0]+weights[:,0,None]*(tri[1]-tri[0])+weights[:,1,None]*(tri[2]-tri[0])
                tuv=tex[0]+weights[:,0,None]*(tex[1]-tex[0])+weights[:,1,None]*(tex[2]-tex[0])
                if np.dot(np.cross(coords[1]-coords[0],coords[2]-coords[0]),np.cross(tri[1]-tri[0],tri[2]-tri[0]))<0:
                    coords=coords[::-1];tuv=tuv[::-1]
                vv.extend((coords-np.array(m[:3])).tolist());uu.extend(tuv.tolist())
    if changed:out.append({'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']})
payload={'mask_basis':'Official Bellevue island plus circular core footprint; original source collection remains intact.',
         'changed_nodes':len(out),'removed_triangles':removed,'retessellated_triangles':retessellated,
         'overrides':out}
if args.road_surfaces:payload['mask_basis']+=' Also replaces exact official road polygons within the documented 150x145m station study area; originals remain untouched.'
path=ROOT/('derived/bellevue/transport/photo_cut.json' if args.road_surfaces else 'derived/bellevue/photo_cut.json');path.write_text(json.dumps(payload,separators=(',',':')))
print(json.dumps({k:v for k,v in payload.items() if k!='overrides'}))
