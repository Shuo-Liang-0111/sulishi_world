"""Tile and masonry solids, generated with official planar constraints."""
from pathlib import Path
import json,math
import numpy as np
from shapely.geometry import Polygon,box,Point,MultiPoint
from shapely.ops import unary_union,triangulate
from shapely import constrained_delaunay_triangles
OUT=Path(__file__).resolve().parent
d=json.loads((OUT/'derived/build_input.json').read_text());W=d['width_m'];land=d['landing_z']
centers=[2.10,W/2,W-2.10];r=1.005;spring=13.955
holes=[]
for u in centers:
    pts=[(u-r,land-.2),(u+r,land-.2),(u+r,spring)]+[(u+r*math.cos(t),spring+r*math.sin(t)) for t in np.linspace(0,math.pi,65)]+[(u-r,land-.2)]
    holes.append(Polygon(pts))
voids=unary_union(holes)
pieces=[]
def surface_mesh(poly,grid_step=.20):
    ring=list(poly.exterior.coords)[:-1];dense=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        a=np.array(a);b=np.array(b)
        dense.extend([list(a+(b-a)*t) for t in np.linspace(0,1,max(1,int(np.ceil(np.linalg.norm(b-a)/.08)))+1)[:-1]])
    dense=[tuple(round(c,8) for c in p) for p in dense]
    footprint=Polygon(dense);points=list(dense);xmin,ymin,xmax,ymax=footprint.bounds
    for x in np.arange(xmin+grid_step*.5,xmax,grid_step):
        for y in np.arange(ymin+grid_step*.5,ymax,grid_step):
            if footprint.contains(Point(x,y)):points.append((x,y))
    points=sorted(set(tuple(round(c,8) for c in p) for p in points))
    cover=footprint.buffer(1e-10)
    candidates=[t for t in triangulate(MultiPoint(points)) if cover.covers(t)]
    if abs(sum(t.area for t in candidates)-footprint.area)>1e-7:
        # Concave tile cut-outs need actual constrained boundary edges.
        candidates=list(constrained_delaunay_triangles(footprint).geoms)
    vtx=[];index={};tris=[];edge_count={};oriented={};area=0
    def vert(xy):
        key=tuple(round(c,8) for c in xy)
        if key not in index:index[key]=len(vtx);vtx.append(key)
        return index[key]
    for tri in candidates:
        ii=[];area+=tri.area
        for xy in list(tri.exterior.coords)[:-1]:
            ii.append(vert(xy))
        tris.append(ii)
    # Conforming edge refinement. Shared edges get the same midpoint, avoiding
    # the T-junctions of independently tessellated terrain triangles.
    for iteration in range(12):
        mids={}
        for tri in tris:
            for a,b in zip(tri,tri[1:]+tri[:1]):
                key=tuple(sorted([a,b]))
                if key not in mids and np.linalg.norm(np.array(vtx[a])-vtx[b])>grid_step:
                    mids[key]=vert((np.array(vtx[a])+vtx[b])*.5)
        if not mids:break
        refined=[]
        for tri in tris:
            flags=[tuple(sorted([tri[i],tri[(i+1)%3]])) in mids for i in range(3)]
            count=sum(flags)
            if not count:refined.append(tri);continue
            if count==1:
                k=flags.index(True);a,b,c=[tri[(k+j)%3] for j in range(3)];m=mids[tuple(sorted([a,b]))]
                refined.extend([[a,m,c],[m,b,c]])
            elif count==2:
                k=flags.index(False);a,b,c=[tri[(k+j)%3] for j in range(3)];m=mids[tuple(sorted([b,c]))];n=mids[tuple(sorted([c,a]))]
                refined.extend([[c,n,m],[a,b,n],[b,m,n]])
            else:
                a,b,c=tri;m=mids[tuple(sorted([a,b]))];n=mids[tuple(sorted([b,c]))];p=mids[tuple(sorted([c,a]))]
                refined.extend([[a,m,p],[m,b,n],[p,n,c],[m,n,p]])
        tris=refined
    else:raise RuntimeError('Terrain refinement did not converge')
    # Source clipping occasionally leaves sub-micrometre collinear cap slivers.
    # Drop those before deriving the solid's boundary, so side walls close the
    # surviving cap exactly at Blender float32 world-coordinate precision.
    uv=np.array(vtx);world=(np.array(d['A'])+uv[:,0,None]*np.array(d['U'])+uv[:,1,None]*np.array(d['N'])).astype('float32').astype('float64')
    f=np.array(tris);aa=world[f[:,1]]-world[f[:,0]];bb=world[f[:,2]]-world[f[:,0]]
    areas=np.abs(aa[:,0]*bb[:,1]-aa[:,1]*bb[:,0])*.5
    removed=int((areas<1e-9).sum());tris=[t for t,area in zip(tris,areas) if area>=1e-9]
    used=sorted(set(i for t in tris for i in t));mapping={i:j for j,i in enumerate(used)}
    vtx=[vtx[i] for i in used];tris=[[mapping[i] for i in t] for t in tris]
    for ii in tris:
        for a,b in zip(ii,ii[1:]+ii[:1]):
            k=tuple(sorted([a,b]));edge_count[k]=edge_count.get(k,0)+1;oriented[k]=(a,b)
    assert abs(area-footprint.area)<1e-7,(area,footprint.area)
    assert all(n in [1,2] for n in edge_count.values())
    return dict(vertices=vtx,triangles=tris,boundary_edges=[oriented[k] for k,n in edge_count.items() if n==1],removed_float32_cap_slivers=removed)

def append_polys(poly,role,**kwargs):
    if poly.is_empty:return
    if poly.geom_type!='Polygon':
        for p in poly.geoms:append_polys(p,role,**kwargs)
        return
    if poly.area<.000005:return
    assert not poly.interiors,(role,poly.wkt)
    outline=list(poly.exterior.coords)[:-1]
    if role=='forecourt_slab':kwargs['surface_mesh']=surface_mesh(poly)
    pieces.append(dict(role=role,outline=outline,**kwargs))
for row,(z0,z1) in enumerate(zip(np.linspace(land,15.42,11)[:-1],np.linspace(land,15.42,11)[1:])):
    for col in range(-1,13):
        a=col*1.12+(row%2)*.56;b=a+1.12
        poly=box(max(-.03,a+.0012),z0+.0012,min(W+.03,b-.0012),z1-.0012) if min(W+.03,b-.0012)>max(-.03,a+.0012) else Polygon()
        append_polys(poly.difference(voids),'facade_ashlar',index=len(pieces),tone=(row*3+col*7)%8)
stepmask=unary_union([Polygon(s['outline']) for s in d['steps']]+[Polygon(p) for p in d['wall_outlines']])
u0,u1=d['scope_local']['u'];v0,v1=d['scope_local']['v']
apron=Polygon(d.get('apron_outline',[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]))
for j in range(15):
    y0=v0+j*.63;y1=min(v1,y0+.63)
    if y0>=v1:continue
    for i in range(-4,28):
        x0=u0+i*.64;x1=x0+.64
        append_polys(box(x0+.002,y0+.002,x1-.002,y1-.002).intersection(apron).difference(stepmask),'forecourt_slab',index=len(pieces),tone=(i*3+j*7)%11)
top=Polygon(d['steps'][-1]['outline'])
for j in range(6):
    for i in range(24):
        append_polys(top.intersection(box(-.2+i*.6+.0015,-.6+j*.6+.0015,-.2+(i+1)*.6-.0015,-.6+(j+1)*.6-.0015)),'landing_slab',index=len(pieces),tone=(i*7+j*5)%11)
# True stone tread bodies are nested measured outlines. Their visible tread zones
# receive individually cut stone segments, avoiding texture-only step seams.
for k in range(3):
    zone=Polygon(d['steps'][k]['outline']).difference(Polygon(d['steps'][k+1]['outline']))
    for i in range(13):
        append_polys(zone.intersection(box(-.5+i*1.07+.0015,-1,-.5+(i+1)*1.07-.0015,5)),'tread_stone',index=len(pieces),step_index=k,tone=(i*5+k*2)%11)
bed=surface_mesh(apron,.16)
(OUT/'derived/part_outlines.json').write_text(json.dumps(dict(centers=centers,opening_radius=r,spring_z=spring,parts=pieces,apron_subbase=bed),separators=(',',':')))
print('Prepared',len(pieces),'cut masonry/paving pieces')
