"""Restore the real multilevel AV16002/AV36232 bridgehead, from cached data.

Upper pavement must not be deleted simply because a lower public passage has
the same XY. Photo-supported top levels remain distinct from inferred slab
thickness and concealed structure. Existing surfaces/cameras stay unchanged.
"""
from pathlib import Path
import hashlib,json,math,struct
import numpy as np
from shapely.geometry import shape,Point,Polygon,LineString,box,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,nearest_points
from shapely import STRtree,constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridgehead_portal';D.mkdir(exist_ok=True)
U=json.loads((R/'derived/bellevue/bridgehead_bank/build_input.json').read_text())
B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
C=json.loads((R/'derived/bellevue/bridgehead_bank/context.json').read_text())
source=next(f for f in C['adjacent_structures'] if f['id'].endswith('.16002'))
wall=shape(source['geometry']);upper=shape(U['source']['geometry']);lower=shape(B['corridor']);O=np.array(U['origin'])

def polygons(g):
    if g.geom_type=='Polygon':return [g] if g.area>1e-8 else []
    return [p for q in getattr(g,'geoms',[]) for p in polygons(q)]

overlap=unary_union(polygons(upper.intersection(lower)))
deck=unary_union([overlap,wall]);paving=overlap.difference(wall)
old_paving=shape(U['paving']);join=paving.boundary.intersection(old_paving.buffer(.002))
assert join.length>4 and paving.area>20
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())['items']
photo=next(q for q in manifest if str(q['node'])=='34256')
raw=Path(photo['geometry']).read_bytes();n=struct.unpack_from('<I',raw)[0]
tri=np.frombuffer(raw,dtype='<f4',count=n*3,offset=8).reshape(-1,3,3).astype(float)+photo['mbs'][:3]
floor_region=upper.intersection(wall.buffer(4)).difference(wall.buffer(.15))
floor_faces=[];cap_faces=[]
for i,t in enumerate(tri):
    normal=np.cross(t[1]-t[0],t[2]-t[0]);length=np.linalg.norm(normal)
    if not length:continue
    nz=normal[2]/length;poly=Polygon(t[:,:2])
    if nz>.97 and t[:,2].min()>409.20 and t[:,2].max()<410.03 and poly.intersection(floor_region).area>.06:floor_faces.append(i)
    if nz>.93 and t[:,2].min()>410 and poly.intersection(wall.buffer(.10)).area>.1:cap_faces.append(i)
assert len(floor_faces)==14 and len(cap_faces)==3

def fit(ids,center):
    points=np.unique(tri[ids].reshape(-1,3),axis=0)
    a=np.c_[np.ones(len(points)),points[:,:2]-center]
    coeff=np.linalg.lstsq(a,points[:,2],rcond=None)[0];residual=a@coeff-points[:,2]
    return dict(center=list(center),coefficients=coeff.tolist(),source_faces=ids,
                sample_vertices=len(points),median_abs_m=float(np.median(abs(residual))),max_abs_m=float(max(abs(residual))))

floor_fit=fit(floor_faces,[2683495.,1246815.]);cap_fit=fit(cap_faces,list(wall.centroid.coords[0]))
assert floor_fit['max_abs_m']<.08 and cap_fit['max_abs_m']<.12
old_tri=[]
for p in U['parts']:
    if p['role']!='paving' or shape(p['plan']).distance(overlap)>3:continue
    vertices=np.array(p['vertices'])+O
    for ids in p['faces']:
        if len(ids)!=3:continue
        t=vertices[ids]
        if np.cross(t[1]-t[0],t[2]-t[0])[2]>1e-10:old_tri.append(t)
old_polys=[Polygon(t[:,:2]) for t in old_tri];tree=STRtree(old_polys)

def old_level(x,y):
    p=Point(x,y);i=int(tree.nearest(p));t=old_tri[i]
    q=np.array(nearest_points(old_polys[i],p)[0].coords[0])
    uv=np.linalg.solve((t[1:,:2]-t[0,:2]).T,q-t[0,:2])
    return float(t[0,2]+uv@(t[1:,2]-t[0,2]))

def plane(f,x,y):return float(np.array(f['coefficients'])@np.r_[1.,np.array([x,y])-f['center']])

def floor(x,y):
    # Match actual retained mesh triangles, not a different analytic terrain.
    t=min(1.,Point(x,y).distance(join)/1.5);w=t*t*(3-2*t)
    return old_level(x,y)*(1-w)+plane(floor_fit,x,y)*w

def cap(x,y):return plane(cap_fit,x,y)

parts=[]
def solid(name,g,top,bottom,role):
    for k,p in enumerate(polygons(g)):
        p=orient(p.segmentize(.25),1);v=[];faces=[]
        for triangle in constrained_delaunay_triangles(p).geoms:
            q=list(orient(triangle,1).exterior.coords)[:3]
            for fn,reverse in [(top,False),(bottom,True)]:
                start=len(v);v.extend([[x-O[0],y-O[1],fn(x,y)-O[2]] for x,y in (q[::-1] if reverse else q)])
                faces.append([start,start+1,start+2])
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
                start=len(v);v.extend([[a[0]-O[0],a[1]-O[1],bottom(*a)-O[2]],
                    [b[0]-O[0],b[1]-O[1],bottom(*b)-O[2]],
                    [b[0]-O[0],b[1]-O[1],top(*b)-O[2]],[a[0]-O[0],a[1]-O[1],top(*a)-O[2]]])
                faces.append([start,start+1,start+2,start+3])
        parts.append(dict(name=name+f'_{k}',vertices=v,faces=faces,plan=mapping(p),area_m2=p.area,role=role,
                          source='AV16002 / AV36232; original34256 photo supports tops, structure inferred'))

for x in np.arange(math.floor(deck.bounds[0]),deck.bounds[2],1.):
    for y in np.arange(math.floor(deck.bounds[1]),deck.bounds[3],1.):
        tile=box(x,y,x+1,y+1);tag=f'{int(x-O[0])}_{int(y-O[1])}'
        solid('DECK_'+tag,deck.intersection(tile),lambda x,y:floor(x,y)-.055,lambda x,y:floor(x,y)-.30,'concrete')
        solid('PAVING_'+tag,paving.intersection(tile),floor,lambda x,y:floor(x,y)-.055,'paving')
solid('WALL_BODY',wall,lambda x,y:cap(x,y)-.055,lambda x,y:floor(x,y)-.30,'concrete')
solid('WALL_CAP',wall,cap,lambda x,y:cap(x,y)-.055,'coping')
route=LineString(B['route'])
stations=np.linspace(0,join.length,max(2,int(join.length/.15)))
seams=[abs(floor(*join.interpolate(st).coords[0])-old_level(*join.interpolate(st).coords[0])) for st in stations]
report=dict(version='G1_026',wall_plan_m2=wall.area,upper_lower_xy_overlap_m2=overlap.area,
    restored_upper_paving_m2=paving.area,structural_deck_m2=deck.area,
    join_length_m=join.length,join_height_max_error_m=max(seams),floor_fit=floor_fit,cap_fit=cap_fit,
    slab_thickness_inferred_m=.245,asphalt_thickness_inferred_m=.055,cap_thickness_inferred_m=.055,
    reconstructed_photographic_relief_not_surveyed_asbuilt=True,existing_objects_moved=False,natural_use_verified=False)
out=dict(version='G1_026',origin=O.tolist(),source=source,deck=mapping(deck),paving=mapping(paving),join=mapping(join),
    photo_floor_region=mapping(floor_region),parts=parts,report=report,
    original_photo_geometry=photo['geometry'],original_photo_geometry_sha256=hashlib.sha256(raw).hexdigest(),
    inherited_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in
       ['derived/bellevue/bridgehead_bank/build_input.json','derived/bellevue/quaibruecke_connection/build_input.json']})
(D/'build_input.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print(json.dumps(dict(report,parts=len(parts)),indent=2))
