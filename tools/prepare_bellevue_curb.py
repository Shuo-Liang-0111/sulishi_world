"""Close the documented platform edge without moving its cadastral outline."""
import json
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,Point
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles
from inspect_platform_road_join import Surface,platform,road,data,origin

ROOT=Path(__file__).resolve().parents[1];out=ROOT/'derived/bellevue/transport'
island=orient(shape(data['island']),sign=1)
from shapely.affinity import translate
local=translate(island,-origin[0],-origin[1]);outer=Polygon(local.exterior)
band=outer.difference(outer.buffer(-.22,join_style=2)).intersection(local)
inside=local.difference(band);top=Surface(platform);bottom=Surface(road)
parts={'platform':[],'curb_top':[],'curb_face':[],'curb_joint':[]}
for triangle in platform:
    p=Polygon(triangle[:,:2])
    for name,mask,offset in [('platform',inside,0),('curb_top',band,.002)]:
        g=p.intersection(mask)
        pp=list(g.geoms) if hasattr(g,'geoms') else [g]
        for polygon in pp:
            if polygon.geom_type!='Polygon' or polygon.area<1e-9:continue
            for t in constrained_delaunay_triangles(polygon).geoms:
                coords=list(t.exterior.coords)[:3]
                vv=[[x,y,top.sample((x,y))[0]+offset] for x,y in coords]
                if np.cross(np.array(vv[1])-vv[0],np.array(vv[2])-vv[0])[2]<0:vv.reverse()
                parts[name].append(vv)
ring=local.exterior
# Keep every original plan vertex; extra half-metre splits bound grade interpolation.
stations=set([0.,ring.length]);stations.update(float(v) for v in np.arange(0,ring.length,.5))
for xy in list(ring.coords)[:-1]:stations.add(float(ring.project(Point(xy))))
stations=sorted(stations)
for a,b in zip(stations,stations[1:]):
    if b-a<1e-7:continue
    xy=[np.array(ring.interpolate(s).coords[0]) for s in (a,b)]
    z=[top.sample(p)[0]+.002 for p in xy]
    lower=[min(bottom.sample(p)[0]-.04,zv-.02) for p,zv in zip(xy,z)]
    v=[[xy[0][0],xy[0][1],z[0]],[xy[1][0],xy[1][1],z[1]],[xy[1][0],xy[1][1],lower[1]],[xy[0][0],xy[0][1],lower[0]]]
    parts['curb_face'].extend([[v[0],v[2],v[1]],[v[0],v[3],v[2]]])
# Fine joint strips express individual kerbstones, not a second displaced road skin.
# Module and joint width are explicit reconstruction assumptions, not surveyed.
for s in np.arange(.6,ring.length,1.2):
    q=np.array(ring.interpolate(s).coords[0]);d=np.array(ring.interpolate(min(ring.length,s+.03)).coords[0])-np.array(ring.interpolate(max(0,s-.03)).coords[0]);d/=np.linalg.norm(d);inward=np.array([-d[1],d[0]])
    q2=q+inward*.219
    for p0,p1 in [(q,q2)]:
        corners=[p0-d*.0015,p0+d*.0015,p1+d*.0015,p1-d*.0015]
        vv=[[p[0],p[1],top.sample(p)[0]+.003] for p in corners]
        parts['curb_joint'].extend([[vv[0],vv[1],vv[2]],[vv[0],vv[2],vv[3]]])
    rz=bottom.sample(q)[0];tz=top.sample(q)[0]
    if tz>rz+.025:
        # Face joint is shallow; the solid curb face remains behind it.
        q=q-inward*.001
        vv=[[*(q-d*.0015),tz],[*(q+d*.0015),tz],[*(q+d*.0015),rz-.01],[*(q-d*.0015),rz-.01]]
        parts['curb_joint'].extend([[vv[0],vv[1],vv[2]],[vv[0],vv[2],vv[3]]])
uv={}
for name,triangles in parts.items():
    if name=='curb_face':
        uv[name]=[]
        for t in triangles:
            ss=[ring.project(Point(v[:2])) for v in t]
            if max(ss)-min(ss)>ring.length/2:ss=[s+ring.length if s<ring.length/2 else s for s in ss]
            uv[name].append([[s/2,v[2]/2] for s,v in zip(ss,t)])
    else:uv[name]=[[[v[0]/(2.05 if name=='platform' else 2),v[1]/(2.05 if name=='platform' else 2)] for v in t] for t in triangles]
record={'source_id':data['ground_fit']['island_id'],'perimeter_m':ring.length,'width_m_inferred':.22,'joint_module_m_inferred':1.2,'joint_width_m_inferred':.003,'top_height_basis':'Unchanged authored photo-supported platform surface + 2mm surface finish. Vertical face reaches inferred road grade; uncertain ramp tips remain flagged in platform_join.json.','material_basis':'Photo shows light grey, weathered mineral curb; generic CC0 concrete_floor_01 represents inferred finish, not a scan of this curb.','parts':parts,'uv':uv,'accepted':False}
(out/'curb_input.json').write_text(json.dumps(record,separators=(',',':')))
print(json.dumps({k:v for k,v in record.items() if k not in ('parts','uv')}));print({k:len(v) for k,v in parts.items()})
