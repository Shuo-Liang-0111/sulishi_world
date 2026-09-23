"""Prepare source-shaped low promenade, retaining wall, steel stair and benches.

AV fixes XY. Resolved upper pavement and interpreted photo observations fix the
connection datums; materials, fabrication, benches and detailed profiles are
explicit inference. The bridge underpass is not flattened or claimed complete.
"""
from pathlib import Path
import json
import hashlib
from functools import lru_cache
import numpy as np
from shapely.geometry import Polygon, LineString, Point, shape, box, mapping
from shapely.geometry.polygon import orient
from shapely.ops import nearest_points, unary_union
from shapely import constrained_delaunay_triangles, STRtree

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/riviera_lower'
context=json.loads((D/'context.json').read_text(encoding='utf-8'))
F={f['id']:f for f in context['features']};O=np.array(context['origin'])
foot=shape(F['av_bo_boflaeche_a.40750']['geometry'])
wall=shape(F['av_ei_flaechenelement_a.20735']['geometry'])
stair=shape(F['av_ei_flaechenelement_a.47309']['geometry'])
northwall=shape(F['av_ei_flaechenelement_a.18091']['geometry'])
low=context['report']['photo_floor_median_ln02_m']
lm=json.loads((R/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text())
lt=np.array(lm['parts']['asphalt']);lp=[Polygon(t[:,:2]) for t in lt];idx=STRtree(lp)

@lru_cache(maxsize=12000)
def upper(x,y):
    p=Point(x-O[0],y-O[1]);i=int(idx.nearest(p));q=np.array(nearest_points(lp[i],p)[0].coords[0]);t=lt[i]
    w=np.linalg.solve((t[1:,:2]-t[0,:2]).T,q-t[0,:2])
    return float(t[0,2]+w@(t[1:,2]-t[0,2])+400)

coords=np.array(foot.exterior.coords)
south=int(np.argmin(np.linalg.norm(coords-np.array([2683487.847,1246848.89]),axis=1)))
outer=LineString(coords[south:])
assert 45<outer.length<65
start=np.array([2683490.118,1246892.123]);end=np.array([2683500.174,1246895.608])
direction=end-start;length=np.linalg.norm(direction);direction/=length
ramp=Polygon([start,end,[2683501.248,1246892.65],[2683491.306,1246889.177]])

def floor(x,y):
    p=np.array([x,y]);t=float(np.clip((p-start)@direction/length,0,1))
    # Only the actual north spur climbs to the already authored upper pavement.
    # The AV end edge has a ~14mm kink outside the four-corner ramp diagram.
    # Classify the whole real spur, not that simplified diagram, to avoid a
    # spurious vertical tear in the remaining boundary sliver.
    if y>1246888.9 and (p-start)@direction>-.003:
        far=p+(1-t)*length*direction
        return low+t*(upper(*np.round(far,6))-low)
    return low

parts=[]
def polygons(g):
    return [q for q in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[]))
            if q.geom_type=='Polygon' and q.area>1e-8]

def slab(name,g,top,bottom,role,source):
    for index,p in enumerate(polygons(g)):
        p=orient(p,1);verts=[];faces=[];surfaces=[]
        for tri in constrained_delaunay_triangles(p).geoms:
            ring=list(orient(tri,1).exterior.coords)[:3]
            k=len(verts);verts.extend([[x-O[0],y-O[1],top(x,y)-400] for x,y in ring]);faces.append([k,k+1,k+2]);surfaces.append('top')
            k=len(verts);verts.extend([[x-O[0],y-O[1],bottom(x,y)-400] for x,y in ring[::-1]]);faces.append([k,k+1,k+2]);surfaces.append('bottom')
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
                k=len(verts);verts.extend([[a[0]-O[0],a[1]-O[1],bottom(*a)-400],
                    [b[0]-O[0],b[1]-O[1],bottom(*b)-400],
                    [b[0]-O[0],b[1]-O[1],top(*b)-400],[a[0]-O[0],a[1]-O[1],top(*a)-400]])
                faces.append([k,k+1,k+2,k+3]);surfaces.append('side')
        parts.append({'name':name+(f'_{index}' if index else ''),'vertices':verts,'faces':faces,'surface':surfaces,
                      'role':role,'source':source,'plan':mapping(p),'area_m2':p.area})

# Subdivision preserves the true polygon, with no bounding-box fill or water cap.
ground=foot.difference(northwall).difference(wall)
for k,y in enumerate(np.arange(1246847,1246897,1.)):
    piece=ground.intersection(box(2683480,y,2683505,y+1))
    # Split at the actual ramp junction so its inferred grade cannot leak west.
    for suffix,cell in [('flat',piece.difference(ramp)),('ramp',piece.intersection(ramp))]:
        slab(f'LOW_PAVING_{k:02}_{suffix}',cell,floor,lambda x,y:floor(x,y)-.22,'paving','av_bo_boflaeche_a.40750')

# Structural skirt follows the real water-facing edge, inside the owned footprint.
skirt=outer.buffer(.22,cap_style='flat').intersection(foot)
slab('RIVER_FASCIA',skirt,lambda x,y:floor(x,y)-.015,lambda x,y:404.505,'concrete','av_bo_boflaeche_a.40750')
for k,y in enumerate(np.arange(1246843,1246894,2.0)):
    slab(f'RETAINING_WALL_{k:02}',wall.intersection(box(2683480,y,2683505,y+2)),
         lambda x,y:upper(round(x,6),round(y,6)),lambda x,y:low-.35,'wall','av_ei_flaechenelement_a.20735')

# The thirteen AV lines are risers; the original authors describe steel stairs.
lines=sorted([f for f in context['features'] if f['id'].startswith('av_ei_linienelement.')],
             key=lambda f:np.mean(np.array(f['geometry']['coordinates'])[:,1]))
boundaries=[np.array([[2683496.752,1246854.848],[2683495.365,1246855.51]])]
boundaries.extend([np.array(f['geometry']['coordinates']) for f in lines])
last=boundaries[-1];v=(last[0]-last[1]);v/=np.linalg.norm(v);n=np.array([-v[1],v[0]])
landing=stair.intersection(Polygon([last[0]+v*50,last[1]-v*50,
                                   last[1]-v*50+n*50,last[0]+v*50+n*50]))
upper_level=upper(2683499.35,1246860.10)
rise=(upper_level-low)/len(lines)
assert .145<rise<.185
treads=[]
for i,(a,b) in enumerate(zip(boundaries,boundaries[1:])):
    poly=Polygon([a[0],b[0],b[1],a[1]]).intersection(stair)
    treads.append({'name':f'STEEL_TREAD_{i:02}','polygon':mapping(poly),'z_ln02_m':low+i*rise,
                   'upper_riser_source':lines[i]['id'],'rise_m':rise,
                   'inner_edge':[a[0].tolist(),b[0].tolist()],'outer_edge':[a[1].tolist(),b[1].tolist()]})
# Landing is supported over the existing wall cap, with its street exit open.
connector=Polygon([[2683498.304,1246859.106],[2683498.918,1246860.792],
                   [2683499.52,1246860.70],[2683498.92,1246858.996]]).intersection(wall)
landing=landing.union(connector)
slab('STEEL_TOP_LANDING',landing,lambda x,y:upper(x,y),lambda x,y:upper(x,y)-.065,'steel','av_ei_flaechenelement_a.47309')

# Arc-length bank seating. This is reference-guided fabrication, not an inventory
# claiming an exact surveyed bench count. All feet and slats stay on the deck.
benches=[]
count=int(np.floor((outer.length-1.4)/2.35));spacing=(outer.length-1.4)/count
for i in range(count+1):
    sta=.7+i*spacing
    p=np.array(outer.interpolate(sta).coords[0]);a=np.array(outer.interpolate(max(0,sta-.05)).coords[0]);b=np.array(outer.interpolate(min(outer.length,sta+.05)).coords[0])
    t=(b-a)/np.linalg.norm(b-a);n=np.array([t[1],-t[0]])
    if not foot.covers(Point(p+n*.30)):n=-n
    assert foot.covers(Point(p+n*.30))
    benches.append({'station_m':sta,'edge_xy':p.tolist(),'along':t.tolist(),'inward':n.tolist(),'z_ln02_m':floor(*p)})

# Actual inner wall front: do not extend its rail across the stair's upper exit.
ring=np.array(wall.exterior.coords)
ix0=int(np.argmin(np.linalg.norm(ring-[2683490.217,1246847.057],axis=1)))
ix1=int(np.argmin(np.linalg.norm(ring-[2683501.248,1246892.65],axis=1)))
front=LineString(ring[ix0:ix1+1])
assert 50<front.length<70
rail=[]
for sta in np.linspace(.1,front.length-.1,int(front.length/.12)+1):
    p=np.array(front.interpolate(sta).coords[0]);a=np.array(front.interpolate(max(0,sta-.05)).coords[0]);b=np.array(front.interpolate(min(front.length,sta+.05)).coords[0])
    t=(b-a)/np.linalg.norm(b-a);n=np.array([t[1],-t[0]])
    if not wall.buffer(.002).covers(Point(p+n*.22)):n=-n
    p=p+n*.22
    if connector.buffer(.12).covers(Point(p)):continue
    rail.append({'station':float(sta),'xy':p.tolist(),'along':t.tolist(),'z':upper(*np.round(p,6))})

covered=unary_union([shape(p['plan']) for p in parts if p['role']=='paving'])
assert ground.symmetric_difference(covered).area<1e-5
total_stair=unary_union([shape(t['polygon']) for t in treads]).union(landing.intersection(stair))
gap=stair.difference(total_stair)
assert gap.area<.07, gap.area
# Tiny curved-edge remnants are solid steel side trim, not missing tread area.
if gap.area>1e-7:
    slab('STEEL_EDGE_TRIM',gap,lambda x,y:low+np.clip((y-1246855.2)/4.1,0,1)*(upper_level-low),
         lambda x,y:low-.05,'steel','av_ei_flaechenelement_a.47309')
report={'footprint_m2':foot.area,'ground_m2':ground.area,'ground_coverage_error_m2':ground.symmetric_difference(covered).area,
        'retaining_wall_m2':wall.area,'photo_interpreted_floor_ln02_m':low,
        'upper_stair_ln02_m':upper_level,'rises':len(lines),'rise_m':rise,
        'curved_outer_edge_m':outer.length,'seat_bays_inferred':count,
        'construction_scope':'AV40750 northern low promenade, AV20735 retaining wall, AV47309 steel stair. Bridge AV39461 is reserved, not claimed rebuilt.',
        'inference':'Photo floor datum, ramp grade, wall fabric, bench subdivision, steel sections and rail details are interpreted. Official XY/identities retained.',
        'natural_use_verified':False}
out={'version':'G1_022','origin':O.tolist(),'parts':parts,'treads':treads,'stairs_boundaries':[q.tolist() for q in boundaries],
     'benches':benches,'upper_wall_rail':rail,'upper_landing':mapping(landing),'stair_rise_m':rise,
     'stair_top_ln02_m':upper_level,'floor_ln02_m':low,'footprint':mapping(foot),'wall':mapping(wall),
     'report':report,'source_context_sha256':hashlib.sha256((D/'context.json').read_bytes()).hexdigest()}
(D/'build_input.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print(json.dumps({'parts':len(parts),'upper_rail_pickets':len(rail),'report':report},indent=2))
