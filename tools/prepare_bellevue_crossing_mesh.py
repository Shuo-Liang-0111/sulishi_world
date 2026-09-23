"""Fit reviewed visible paint candidates to existing native road triangles."""
import json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon
from shapely.affinity import translate
from shapely import STRtree,constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/transport'
source=OUT/'crossings_candidates.geojson';doc=json.loads(source.read_text());payload=json.loads((OUT/'road_input.json').read_text())
tris=np.array([t for p in payload['pieces'] if p['kind']=='road_asphalt' for t in p['triangles']]);polys=[Polygon(t[:,:2]) for t in tris];tree=STRtree(polys)
items=[]
for f in doc['features']:
    local=translate(shape(f['geometry']),-2683775,-1246700);out=[]
    for idx in tree.query(local,predicate='intersects'):
        cut=local.intersection(polys[idx]);parts=cut.geoms if hasattr(cut,'geoms') else [cut];base=tris[idx];ab=(base[1:,:2]-base[0,:2]).T
        if abs(np.linalg.det(ab))<1e-10:continue
        for p in parts:
            if p.geom_type!='Polygon' or p.area<1e-8:continue
            for tri in constrained_delaunay_triangles(p).geoms:
                verts=[]
                for xy in list(tri.exterior.coords)[:3]:
                    w=np.linalg.solve(ab,np.array(xy)-base[0,:2]);z=base[0,2]+w@(base[1:,2]-base[0,2]);verts.append([*xy,float(z+.0015)])
                if np.cross(np.array(verts[1])-verts[0],np.array(verts[2])-verts[0])[2]<0:verts.reverse()
                out.append(verts)
    if out:items.append({'id':f['properties']['id'],'properties':f['properties'],'triangles':out})
report={'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'road_input_sha256':hashlib.sha256((OUT/'road_input.json').read_bytes()).hexdigest(),'bar_count':len(items),'paint_offset_m_inferred':.0015,'visual_review':'All 70 candidate outlines inspected over SWISSIMAGE; they follow visible yellow crossing paint. Occluded/fragmented bars are not reconstructed as complete crossings.','source_scope':'11 official walking crossing links; only visible paint on already authored road footprints','status':'partial visible marking reconstruction; accessibility and full crossing coverage not accepted'}
(OUT/'crossings_input.json').write_text(json.dumps({'report':report,'items':items},ensure_ascii=False,separators=(',',':')));print(json.dumps(report,ensure_ascii=False))
