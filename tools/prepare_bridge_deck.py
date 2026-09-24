"""Source-shaped bridge surfaces, real rail lines and complete public edges.

AV/VBZ XY and known mast heights remain source evidence. Paving thickness,
curb profile, rail/guard fabrication and marking cadence are interpretations.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json,math
import numpy as np
from shapely.geometry import shape,Point,Polygon,LineString,box,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,nearest_points,linemerge,substring
from shapely import STRtree,constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_deck';D.mkdir(exist_ok=True)
B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
W=json.loads((R/'derived/bellevue/quaibruecke_water/build_input.json').read_text())
O=np.array(B['origin']);A=np.array(B['bridge_anchor']);T=np.array(B['bridge_along']);N=np.array(B['bridge_across']);coef=np.array(B['bridge_deck_coefficients'])
bridge=shape(W['bridge'])
def xy(st,d):return A+st*T+d*N
def station(p):return float((np.array(p)-A)@T)
def transverse(p):return float((np.array(p)-A)@N)
def polys(g):
    if g.geom_type=='Polygon':return [g] if g.area>1e-7 else []
    return [p for q in getattr(g,'geoms',[]) for p in polys(q)]
def lines(g):
    if g.geom_type=='LineString':return [g] if g.length>.01 else []
    return [p for q in getattr(g,'geoms',[]) for p in lines(q)]

# Complete real bridge; only its east approach is part of the new ground work.
approach=Polygon([xy(-18,-1),xy(0,-1),xy(0,33),xy(-18,33)])
region=unary_union([bridge,approach])
old=json.loads((D/'existing_approaches.json').read_text());old_tri=np.array([q for row in old['surfaces'] for q in row['triangles']])+O
old_polys=[Polygon(t[:,:2]) for t in old_tri];tree=STRtree(old_polys)
old_plan=unary_union(old_polys)
old_edge=old_plan.boundary
def retained_z(p):
    i=int(tree.nearest(Point(p)));tri=old_tri[i];q=np.array(nearest_points(old_polys[i],Point(p))[0].coords[0])
    uv=np.linalg.solve((tri[1:,:2]-tri[0,:2]).T,q-tri[0,:2]);return float(tri[0,2]+uv@(tri[1:,2]-tri[0,2]))
def raw_deck(x,y):
    st,d=(np.array([x,y])-A)@np.array([T,N]).T
    return float(coef@[1,st,st*st,d])
@lru_cache(maxsize=None)
def level(x,y,raised=False):
    nominal=raw_deck(x,y)+(.12 if raised else 0.)
    if station([x,y])>5:return nominal
    distance=old_plan.distance(Point(x,y));t=min(1.,distance/2.5);w=t*t*(3-2*t)
    return retained_z([x,y])*(1-w)+nominal*w

features={f['id']:f for f in json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']}
ids=[5939,5940,5941,5942,5943,5944,36555,549]
zones=[]
for ident in ids:
    f=features[f'av_bo_boflaeche_a.{ident}'];g=shape(f['geometry']).intersection(region).difference(old_plan.buffer(.00002))
    if g.area<.001:continue
    kind='walk' if ident in [5939,5943] else 'cycle' if ident in [5940,5944] else 'track' if ident==36555 else 'road'
    zones.append(dict(id=f['id'],kind=kind,geometry=g,raised=kind in ['walk','cycle']))
surface=unary_union([z['geometry'] for z in zones])
assert surface.intersection(old_plan).area<.001
overlaps=sum(z['geometry'].area for z in zones)-surface.area
assert overlaps<.03,overlaps
roads=unary_union([z['geometry'] for z in zones if not z['raised']])
raised=unary_union([z['geometry'] for z in zones if z['raised']])
rails=[]
for f in json.loads((R/'sources/features/vbz/strecke_schienen.geojson').read_text())['features']:
    for k,g in enumerate(lines(shape(f['geometry']).intersection(roads))):
        if g.length>.10:rails.append(dict(id=f['id'],line=g))
assert len(rails)>=8
heads=unary_union([r['line'].buffer(.0325,cap_style=2,join_style=2) for r in rails]).intersection(roads)
channels=unary_union([r['line'].buffer(.0825,cap_style=2,join_style=2) for r in rails]).intersection(roads)
parts=[];beams=[];pipes=[]
def solid(name,g,top,bottom,role,source):
    for k,p in enumerate(polys(g)):
        p=orient(p.segmentize(1.),1);v=[];faces=[]
        for tri in constrained_delaunay_triangles(p).geoms:
            pts=list(orient(tri,1).exterior.coords)[:3]
            for fn,rev in [(top,False),(bottom,True)]:
                off=len(v);v.extend([[x-O[0],y-O[1],fn(x,y)-O[2]] for x,y in (pts[::-1] if rev else pts)])
                faces.append([off,off+1,off+2])
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
                off=len(v);v.extend([[a[0]-O[0],a[1]-O[1],bottom(*a)-400],
                    [b[0]-O[0],b[1]-O[1],bottom(*b)-400],[b[0]-O[0],b[1]-O[1],top(*b)-400],
                    [a[0]-O[0],a[1]-O[1],top(*a)-400]])
                faces.append([off,off+1,off+2,off+3])
        parts.append(dict(name=name+f'_{k}',vertices=v,faces=faces,role=role,source=source,plan=mapping(p),area_m2=p.area))

for z in zones:
    g=z['geometry'].difference(channels) if not z['raised'] else z['geometry']
    for i,st in enumerate(np.arange(-20,126,2.)):
        tile=Polygon([xy(st,-2),xy(st+2,-2),xy(st+2,34),xy(st,34)])
        solid(f"SURFACE_{z['id'].split('.')[-1]}_{i:03}",g.intersection(tile),
              lambda x,y,raised=z['raised']:level(x,y,raised),lambda x,y:level(x,y,False)-.113,
              'asphalt_walk' if z['raised'] else 'asphalt_track' if z['kind']=='track' else 'asphalt_road',z['id'])
for i,st in enumerate(np.arange(-20,126,2.)):
    tile=Polygon([xy(st,-2),xy(st+2,-2),xy(st+2,34),xy(st,34)])
    solid(f'RAIL_HEAD_{i:03}',heads.intersection(tile),lambda x,y:level(x,y)+.003,lambda x,y:level(x,y)-.06,'rail','VBZ actual individual rail lines')
    solid(f'RAIL_RECESS_{i:03}',channels.difference(heads).intersection(tile),lambda x,y:level(x,y)-.035,lambda x,y:level(x,y)-.10,'drain','VBZ rail groove; profile inferred')

# Real raised edge between cycle space and carriageways, plus asphalt-to-rail
# groove side walls provided by the closed surface solids above.
curb_lines=raised.boundary.intersection(roads.buffer(.002)).intersection(bridge.buffer(-.1))
curb_area=unary_union([g.buffer(.13,cap_style=2,join_style=2) for g in lines(curb_lines)]).intersection(raised)
for i,st in enumerate(np.arange(-18,125,1.25)):
    tile=Polygon([xy(st,-2),xy(st+1.247,-2),xy(st+1.247,34),xy(st,34)])
    solid(f'CURB_{i:03}',curb_area.intersection(tile),lambda x,y:level(x,y,True)+.002,lambda x,y:level(x,y)-.08,'curb','AV cycle/carriageway boundary; modular stone inferred')

# Source-bounded white divisions, matching the orthophoto's road/lane logic.
paint=[]
for walk,cycle in [(5939,5940),(5943,5944)]:
    a=shape(features[f'av_bo_boflaeche_a.{walk}']['geometry'])
    b=shape(features[f'av_bo_boflaeche_a.{cycle}']['geometry'])
    seam=a.boundary.intersection(b.buffer(.006)).intersection(surface)
    g=unary_union([l.buffer(.055,cap_style=2) for l in lines(seam)]).intersection(raised)
    paint.append(dict(name=f'WALK_DIVIDER_{walk}',geometry=g,raised=True))
for ident in [5941,5942]:
    g=shape(features[f'av_bo_boflaeche_a.{ident}']['geometry']);d=transverse(g.centroid.coords[0])
    for i,st in enumerate(np.arange(3,122,6.)):
        stripe=LineString([xy(st,d),xy(st+3,d)]).buffer(.065,cap_style=2).intersection(g).intersection(surface)
        paint.append(dict(name=f'LANE_DASH_{ident}_{i:02}',geometry=stripe,raised=False))
for rec in paint:
    solid(rec['name'],rec['geometry'],lambda x,y,r=rec['raised']:level(x,y,r)+.0014,
          lambda x,y,r=rec['raised']:level(x,y,r)+.0004,'paint','SWISSIMAGE visible line arrangement; cadence/width inferred')

# Source-aligned outer edge; inset only within the same cadastral walkway.
guards=[]
for ident in [5939,5943]:
    footprint=shape(features[f'av_bo_boflaeche_a.{ident}']['geometry']).intersection(bridge)
    boundary=footprint.boundary.intersection(bridge.boundary.buffer(.005))
    # The boundary may be one continuous chain including the bridge-end
    # returns. Choosing the longest chain would close the public exit.
    longitudinal=[]
    for candidate in lines(boundary):
        for a,b in zip(candidate.coords,list(candidate.coords)[1:]):
            delta=np.array(b)-a;length=np.linalg.norm(delta)
            if length>.001 and abs(float(delta@T))/length>.98:
                longitudinal.append(LineString([a,b]))
    assert longitudinal,ident
    merged=unary_union(longitudinal)
    candidates=lines(linemerge(merged) if merged.geom_type!='LineString' else merged)
    edge=max(candidates,key=lambda q:q.length)
    assert edge.length>100,(ident,[(p.length,p.bounds) for p in candidates])
    edge=substring(edge,.15,edge.length-.15)
    coords=np.array(edge.segmentize(1.5).coords)
    normal=N*(1 if ident==5943 else -1)
    # Verify the inward choice against actual cadastral coverage.
    mid=coords[len(coords)//2]
    if not footprint.buffer(.001).covers(Point(mid+normal*.12)):normal=-normal
    coords=coords+normal*.12
    assert all(footprint.buffer(.001).covers(Point(p)) for p in coords),ident
    deltas=np.diff(coords,axis=0)
    alignment=np.abs(deltas@T)/np.linalg.norm(deltas,axis=1)
    assert alignment.min()>.98,(ident,alignment.min())
    line=LineString(coords);positions=np.linspace(0,line.length,int(math.ceil(line.length/1.7))+1)
    posts=[]
    for i,st in enumerate(positions):
        p=np.array(line.interpolate(st).coords[0]);z=level(*p,True);posts.append([*p,z])
        beams.append(dict(name=f'GUARD_POST_{ident}_{i:03}',a=[*p,z+.015],b=[*p,z+1.15],width=.052,depth=.052,role='guard',source=f'AV{ident} edge; guard profile inferred'))
        foot=Polygon([p+T*a+N*b for a,b in [(-.12,-.11),(.12,-.11),(.12,.11),(-.12,.11)]])
        solid(f'GUARD_FOOT_{ident}_{i:03}',foot,lambda x,y:level(x,y,True)+.018,lambda x,y:level(x,y,True)-.01,'guard',f'AV{ident} edge; plate inferred')
    for k,h in enumerate([.12,1.12]):
        pipes.append(dict(name=f'GUARD_RAIL_{ident}_{k}',points=[[*p,level(*p,True)+h] for p in coords],radius=.024 if k else .016,role='guard',source=f'AV{ident} edge; horizontal member inferred'))
    for i,st in enumerate(np.arange(.085,line.length,.14)):
        p=np.array(line.interpolate(st).coords[0]);z=level(*p,True)
        beams.append(dict(name=f'GUARD_INFILL_{ident}_{i:04}',a=[*p,z+.12],b=[*p,z+1.12],width=.018,depth=.018,role='guard',source=f'AV{ident} edge; infill inferred'))
    guards.append(dict(source=f'av_bo_boflaeche_a.{ident}',length_m=line.length,posts=posts,path=coords.tolist(),
                       min_longitudinal_alignment=float(alignment.min()),transverse_end_returns=False))

infra=R/'sources/features/quaibruecke_deck'
masts=[]
for f in json.loads((infra/'fahrleitungen_mast.geojson').read_text())['features']:
    p=np.array(shape(f['geometry']).centroid.coords[0]);props=f['properties']
    if not bridge.buffer(.5).covers(Point(p)):continue
    base=float(props['hoehemastuk']);top=float(props['hoehemastok']);ground=level(*p,True)
    masts.append(dict(id=f['id'],xy=p.tolist(),base_ln02_m=base,top_ln02_m=top,ground_interpreted_ln02_m=ground,
                      source_base_minus_interpreted_ground_m=base-ground))

# Retain every complete source span whose endpoints are bridge masts. Span
# heights are known; contact wire heights will be interpolated at intersections.
spans=[];mast_points=[Point(m['xy']) for m in masts]
for f in json.loads((infra/'fahrleitungen_tragwerk_linie.geojson').read_text())['features']:
    for line in lines(shape(f['geometry'])):
        pts=np.array(line.coords);pr=f['properties']
        if any(min(Point(p).distance(m) for m in mast_points)>.05 for p in [pts[0],pts[-1]]):continue
        z0=pr.get('hoeheanfang');z1=pr.get('hoeheende')
        if z0 is None or z1 is None:continue
        spans.append(dict(id=f['id'],line=line,start=float(z0),end=float(z1)))
        samples=[line.interpolate(t,normalized=True).coords[0] for t in np.linspace(0,1,25)]
        pipes.append(dict(name='SPAN_'+f['id'].split('.')[-1],points=[[*p,z0+(z1-z0)*t-.09*4*t*(1-t)] for p,t in zip(samples,np.linspace(0,1,25))],radius=.008,role='wire',source=f['id']+'; endpoints surveyed, sag/radius inferred'))
wire_supports=[]
for f in json.loads((infra/'fahrleitungen_fahrdraht.geojson').read_text())['features']:
    for j,line in enumerate(lines(shape(f['geometry']).intersection(bridge))):
        if line.length<.1:continue
        endpoints=[]
        for p in [Point(line.coords[0]),Point(line.coords[-1])]:
            span=min(spans,key=lambda s:s['line'].distance(p));t=span['line'].project(p,normalized=True)
            z=span['start']+(span['end']-span['start'])*t-.09*4*t*(1-t)-.11
            endpoints.append(z)
        pts=[line.interpolate(t,normalized=True).coords[0] for t in np.linspace(0,1,19)]
        pipes.append(dict(name=f"CONTACT_{f['id'].split('.')[-1]}_{j}",points=[[*p,endpoints[0]*(1-t)+endpoints[1]*t-.045*4*t*(1-t)] for p,t in zip(pts,np.linspace(0,1,19))],radius=.0055,role='wire',source=f['id']+'; source XY, height from nearby source spans, sag inferred'))
        wire_supports.append(dict(id=f['id'],endpoint_heights_ln02_m=endpoints))

report=dict(version='G1_027',source_surface_area_m2=surface.area,plan_overlap_m2=overlaps,
            bridge_plan_m2=bridge.area,zones={z['id']:dict(kind=z['kind'],area_m2=z['geometry'].area) for z in zones},
            road_m2=roads.area,raised_walk_cycle_m2=raised.area,rail_heads_m2=heads.area,rail_channels_m2=channels.area,
            rail_length_m=sum(r['line'].length for r in rails),source_rail_ids=sorted(set(r['id'] for r in rails)),
            curb_height_inferred_m=.12,rail_groove_depth_inferred_m=.035,guard_height_inferred_m=1.15,
            masts=len(masts),cross_spans=len(spans),contact_segments=len(wire_supports),
            g1_scope_expanded=False,old_geometry_moved=False,natural_use_verified=False)
out=dict(version='G1_027',origin=O.tolist(),parts=parts,beams=beams,pipes=pipes,masts=masts,guards=guards,
         surface=mapping(surface),region=mapping(region),bridge=mapping(bridge),heads=mapping(heads),channels=mapping(channels),
         zones=[dict(id=z['id'],kind=z['kind'],raised=z['raised'],geometry=mapping(z['geometry'])) for z in zones],
         report=report,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'existing_approaches.json',infra/'receipt.json']})
(D/'build_input.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print(json.dumps(dict(parts=len(parts),beams=len(beams),pipes=len(pipes),report=report)),flush=True)
