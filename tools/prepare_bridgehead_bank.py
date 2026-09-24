"""Build the complete AV36232 upper promenade from cached survey context.

Inventory identities/XY/heights and source boundaries are fixed. Surface grade
uses the retained survey TIN, tied to the already saved stair landing. Tree pits,
individual morphology, construction depths and rail fabrication are inferred.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json,math
import numpy as np
from shapely.geometry import shape,mapping,Point,Polygon,box,LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,nearest_points
from shapely import STRtree,constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridgehead_bank'
C=json.loads((D/'context.json').read_text(encoding='utf-8'))
O=np.array(C['origin']);foot=shape(C['source']['geometry'])
B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text(encoding='utf-8'))
features={f['id']:f for f in C['adjacent_structures']}
stair=shape(B['south_stair']);corridor=shape(B['corridor'])
terrain=np.load(D/'survey_terrain.npz')['triangles']
polys=[Polygon(t[:,:2]) for t in terrain];index=STRtree(polys)
landing=shape(next(q['plan'] for q in B['parts'] if q['name']=='SOUTH_STAIR_LANDING'))
landing_z=B['report']['south_stair_top_terrain_interpreted_ln02_m']
water_input=R/'derived/bellevue/quaibruecke_water/build_input.json'
bridge=shape(json.loads(water_input.read_text(encoding='utf-8'))['bridge'])
bridge_anchor=np.array(B['bridge_anchor']);bridge_along=np.array(B['bridge_along'])
bridge_across=np.array(B['bridge_across']);deck_coeff=np.array(B['bridge_deck_coefficients'])

@lru_cache(maxsize=200000)
def ground(x,y):
    point=Point(x,y);i=int(index.nearest(point));q=np.array(nearest_points(polys[i],point)[0].coords[0])
    t=terrain[i];w=np.linalg.solve((t[1:,:2]-t[0,:2]).T,q-t[0,:2])
    z=float(t[0,2]+w@(t[1:,2]-t[0,2]))
    # Retain the saved landing height at its actual shared edge and blend only
    # over the adjacent upper walkway. No lower-route profile is flattened.
    d=point.distance(landing);blend=max(0.,1-d/1.4)**2
    z=z*(1-blend)+landing_z*blend
    # The terrain TIN spans both levels at the bridge corner. It must not
    # make the upper sidewalk descend through the bridge to the underpass.
    # Use the independent photo-supported bridge deck only at this actual
    # intersection, fading to the retained terrain within three metres.
    distance=point.distance(bridge)
    if distance<3.:
        delta=np.array([x,y])-bridge_anchor
        station=delta@bridge_along;cross=delta@bridge_across
        deck=float(deck_coeff@np.array([1,station,station*station,cross]))
        t=distance/3.;weight=1-t*t*(3-2*t)
        z=z*(1-weight)+deck*weight
    return z

def polygons(g):
    return [p for p in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[])) if p.geom_type=='Polygon' and p.area>1e-8]

wall_features=[f for f in C['adjacent_structures'] if f['properties'].get('art_txt')=='Mauer.Mauer']
walls=unary_union([shape(f['geometry']) for f in wall_features])
guards=unary_union([shape(f['geometry']).buffer(.08) for f in C['adjacent_structures']
                   if f['properties'].get('art_txt') in ['Unterstand','wichtige_Treppe'] and not f['id'].endswith('.6191')])
walk=foot.difference(walls).difference(guards).difference(stair).difference(corridor)
trees=[f for f in C['trees'] if foot.covers(shape(f['geometry']))]
assert len(trees)==12 and all('Platanus' in f['properties']['baumart_lat'] for f in trees)
trees.sort(key=lambda f:f['properties']['objectid'])
pits=[]
for tree in trees:
    ident=tree['properties']['objectid'];xy=np.array(tree['geometry']['coordinates'])[:2]
    h=tree['properties']['hoehe'];rng=np.random.default_rng(ident)
    diameter=float(np.clip(.030*h+rng.uniform(-.09,.11),.48,.96))
    radius=1.02+diameter*.30
    hole=Point(xy).buffer(radius,quad_segs=36).intersection(walk.buffer(-.12))
    assert hole.geom_type=='Polygon' and hole.covers(Point(xy)),ident
    crown=[float(h*.245+rng.uniform(-.50,.40)),float(h*.225+rng.uniform(-.45,.45))]
    pits.append(dict(source=tree,origin=O.tolist(),height_m=h,ground_ln02_m=ground(*xy)-.03,
        pit=mapping(hole),radius_m_inferred=radius,
        inferred=dict(seed=ident,trunk_diameter_m=diameter,crown_radius_m=crown,branch_clearance_m=3.7+rng.uniform(-.2,.35)),
        basis='AV36232 + retained survey TIN, inventory2022 XY/species/height. Pit size, individual crown, girth, roots and every branch inferred; not a tree-specific scan.'))
soil=unary_union([shape(p['pit']) for p in pits]);paving=walk.difference(soil)
parts=[]
def solid(name,g,top,bottom,role,source,max_boundary_step=None):
    for k,p in enumerate(polygons(g)):
        if max_boundary_step:
            # LV95 intersections can split a sub-nanometre sliver when GEOS
            # inserts collinear samples. Keep the single measurable polygon.
            sampled=polygons(p.segmentize(max_boundary_step))
            assert len(sampled)==1 and abs(sampled[0].area-p.area)<1e-6
            p=sampled[0]
        p=orient(p,1);v=[];faces=[]
        for tr in constrained_delaunay_triangles(p).geoms:
            q=list(orient(tr,1).exterior.coords)[:3]
            for fn,rev in [(top,False),(bottom,True)]:
                j=len(v);v.extend([[x-O[0],y-O[1],fn(round(x,6),round(y,6))-400] for x,y in (q[::-1] if rev else q)])
                faces.append([j,j+1,j+2])
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
                j=len(v);v.extend([[a[0]-O[0],a[1]-O[1],bottom(*a)-400],
                    [b[0]-O[0],b[1]-O[1],bottom(*b)-400],[b[0]-O[0],b[1]-O[1],top(*b)-400],
                    [a[0]-O[0],a[1]-O[1],top(*a)-400]])
                faces.append([j,j+1,j+2,j+3])
        parts.append(dict(name=name+(f'_{k}' if k else ''),vertices=v,faces=faces,plan=mapping(p),area_m2=p.area,role=role,source=source))

# Spatial tiles are geometric sampling only, not a visible uniform paving grid.
# The asphalt material projects in physical metres continuously across tiles.
for x in np.arange(math.floor(foot.bounds[0]/2)*2,foot.bounds[2],2):
    for y in np.arange(math.floor(foot.bounds[1]/2)*2,foot.bounds[3],2):
        tile=box(x,y,x+2,y+2)
        if not tile.intersects(paving):continue
        solid(f'GROUND_{int(x-O[0])}_{int(y-O[1])}',paving.intersection(tile),ground,
              lambda x,y:ground(x,y)-.18,'paving',C['source']['id'])

# Soil fan is relief geometry, below pavement with a fixed collar and boundary.
for p in pits:
    ident=p['source']['properties']['objectid'];poly=shape(p['pit']);center=np.array(p['source']['geometry']['coordinates'])[:2]
    ring=np.array(poly.exterior.coords)[:-1];n=len(ring);xy=[center];faces=[];rings=12
    for j in range(1,rings+1):xy.extend(center+(ring-center)*j/rings)
    for k in range(n):faces.append([0,1+k,1+(k+1)%n])
    for j in range(1,rings):
        a=1+(j-1)*n;b=1+j*n
        for k in range(n):faces.extend([[a+k,b+k,b+(k+1)%n],[a+k,b+(k+1)%n,a+(k+1)%n]])
    v=[]
    for q in xy:
        edge=poly.boundary.distance(Point(q));rad=np.linalg.norm(q-center)
        fade=min(1,edge/.10)*np.clip((rad-p['inferred']['trunk_diameter_m']*.65)/.16,0,1)
        relief=.003*math.sin((q[0]-O[0])*18)*math.sin((q[1]-O[1])*23+ident)*fade
        v.append([q[0]-O[0],q[1]-O[1],ground(*q)-.03+relief-400])
    ff=np.array(faces);vv=np.array(v);cross=np.cross(vv[ff[:,1]]-vv[ff[:,0]],vv[ff[:,2]]-vv[ff[:,0]])[:,2]
    ff[cross<0]=ff[cross<0][:,::-1]
    parts.append(dict(name=f'SOIL_{ident}',vertices=v,faces=ff.tolist(),plan=p['pit'],area_m2=poly.area,role='soil',source=p['source']['id']))

# Retain the existing lower retaining-wall body. Add a physical coping and
# source-aligned vertical-picket guarding, with a gap at the actual steel stair.
existing_wall=shape(B['retaining'])
selected_wall=shape(features['av_ei_flaechenelement_a.15891']['geometry'])
cap=selected_wall.intersection(foot.buffer(.65)).difference(stair.buffer(.035))
missing_body=cap.difference(existing_wall)
solid('WALL_EXTENSION',missing_body,ground,lambda x,y:ground(x,y)-1.65,'concrete','AV15891; hidden base inferred',.20)
solid('WALL_COPING',cap,lambda x,y:ground(x,y)+.04,lambda x,y:ground(x,y)-.035,'coping','AV15891; coping section inferred',.20)
rail_raw=foot.boundary.intersection(selected_wall.buffer(.025)).difference(stair.buffer(.08))
rails=[rail_raw] if rail_raw.geom_type=='LineString' else [g for g in getattr(rail_raw,'geoms',[]) if g.geom_type=='LineString']
rails=[g for g in rails if g.length>.60]
rail_records=[]
rail_support=cap.buffer(-.09)
assert not rail_support.is_empty
for i,line in enumerate(rails):
    points=[]
    for st in np.linspace(0,line.length,max(2,int(line.length/.28)+1)):
        q=np.array(line.interpolate(st).coords[0]);nearest=np.array(nearest_points(rail_support,Point(q))[0].coords[0])
        points.append([*nearest,ground(*nearest)+.04])
    rail_records.append(dict(index=i,points=points,length_m=line.length,source='AV36232/15891 shared boundary; historic reference supports vertical metal pickets, details inferred'))

levels=[ground(x,y) for x,y in np.array(foot.exterior.coords)]
report=dict(version='G1_025',source_plan_m2=foot.area,paving_m2=paving.area,soil_m2=soil.area,
    protected_or_other_level_m2=foot.area-walk.area,coverage_error_m2=abs(walk.area-paving.area-soil.area),
    inventory_trees=len(pits),retained_steel_stair_id='av_ei_flaechenelement_a.6191',
    ground_range_ln02_m=[min(levels),max(levels)],grade_basis='Retained survey TIN; bounded tie to saved steel landing; actual bridge overlap uses independent photo-supported deck with 3m transition',
    copied_stair_landing_ln02_m=landing_z,rail_length_m=sum(q['length_m'] for q in rail_records),
    geometry_is_inferred_between_source_constraints=True,natural_use_verified=False)
out=dict(version='G1_025',origin=O.tolist(),source=C['source'],parts=parts,trees=pits,rails=rail_records,
    walk=mapping(walk),paving=mapping(paving),soil=mapping(soil),guard=mapping(guards),cap=mapping(cap),
    replacement_ground=mapping(unary_union([foot,cap,existing_wall,stair,corridor.intersection(foot.buffer(1.2))])),
    report=report,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [D/'context.json',D/'survey_terrain.npz',R/'derived/bellevue/quaibruecke_connection/build_input.json',water_input]})
(D/'build_input.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print(json.dumps(dict(report,parts=len(parts)),indent=2))
