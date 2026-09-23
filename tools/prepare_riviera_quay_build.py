"""Recover the full AV145 promenade and AV35398 steps from cached survey lines.

Survey XY is retained. Heights, slab build-ups and joint construction are declared
inference; no as-built height precision is claimed for these new pieces.
"""
from pathlib import Path
import json
import math
import hashlib
from functools import lru_cache

import numpy as np
from shapely.geometry import shape, Polygon, LineString, Point, box, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, nearest_points
from shapely.affinity import affine_transform
from shapely import constrained_delaunay_triangles, STRtree

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/riviera_quay'
source=json.loads((D/'sources.json').read_text(encoding='utf-8'))
O=np.array(source['origin']); A=np.array([2683500.277,1246895.644])
T=np.array([2683473.339,1246971.039])-A;T/=np.linalg.norm(T);N=np.array([-T[1],T[0]])
features={f['id']:f for f in source['features']}
def sd(g):return affine_transform(g,[*T,*N,-A@T,-A@N])
def xy(q):return A+q[0]*T+q[1]*N
def feature(code):return sd(shape(features[code]['geometry']))
foot=feature('av_bo_boflaeche_a.145')
stairs=feature('av_ei_flaechenelement_a.35398')
wall_ids=[35223,37826,37827,37828,37832,38011,38597,18091]
walls={f'av_ei_flaechenelement_a.{i}':feature(f'av_ei_flaechenelement_a.{i}') for i in wall_ids}
main_walls=unary_union([g for k,g in walls.items() if not k.endswith('.18091')])
walk=foot.difference(stairs).difference(main_walls)

# Fit the observed promenade grade, rejecting people, foliage and water samples.
zdata=np.load(D/'source_geometry.npz');tri=zdata['photo_triangles'];c=tri.mean(axis=1)
delta=c[:,:2]-A; coords=np.c_[delta@T,delta@N]
norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(norm,axis=1)/2
sel=(coords[:,0]>0)&(coords[:,0]<122)&(coords[:,1]>.4)&(coords[:,1]<7)&(c[:,2]>407.2)&(c[:,2]<408.2)&(abs(norm[:,2])>1.8*area)
cells={}
for q,z in zip(coords[sel],c[sel,2]):cells.setdefault(tuple(np.floor(q)),[]).append([*q,z])
support=np.array([np.median(v,axis=0) for v in cells.values()]);design=np.c_[np.ones(len(support)),support[:,:2]]
w=np.ones(len(support))
for _ in range(12):
    coef=np.linalg.lstsq(design*w[:,None],support[:,2]*w,rcond=None)[0]
    res=support[:,2]-design@coef;w=np.minimum(1,.065/np.maximum(abs(res),1e-9))
assert -.05 < coef[2] < -.005 and len(support)>80

# Exact preceding mesh is the boundary datum, not a second independently fitted
# walkway. Nearest distance is checked before accepting its height.
lm=json.loads((R/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text())
lt=np.array(lm['parts']['asphalt']);lp=[Polygon(q[:,:2]) for q in lt];lidx=STRtree(lp)
def preceding_height(global_xy):
    p=Point(global_xy-O[:2]);i=int(lidx.nearest(p));distance=p.distance(lp[i])
    q=np.array(nearest_points(lp[i],p)[0].coords[0]);tr=lt[i]
    w=np.linalg.solve((tr[1:,:2]-tr[0,:2]).T,q-tr[0,:2])
    return float(tr[0,2]+w@(tr[1:,2]-tr[0,2])+400),distance

@lru_cache(maxsize=60000)
def datum(s):
    z,d=preceding_height(xy((s,0)))
    if d<.12:return z
    return float(coef@[1,s,0])
def grade(s,d):return datum(round(float(s),7))+float(coef[2])*d

parts=[]
def polys(g):return [p for p in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[])) if p.geom_type=='Polygon' and p.area>1e-7]
def add_slab(name,g,top,bottom,role,source_id):
    for index,poly in enumerate(polys(g)):
        poly=orient(poly,1);v=[];faces=[];surface=[]
        # Independent small faces use metric UVs; geometrical closure is checked
        # later by spatial boundary and top area, not by vertex index equality.
        for tr in constrained_delaunay_triangles(poly).geoms:
            ring=list(tr.exterior.coords)[:3]
            if Polygon(ring).exterior.is_ccw is False:ring=ring[::-1]
            start=len(v);v.extend([[*xy(q)-O[:2],top(*q)-400] for q in ring]);faces.append(list(range(start,start+3)));surface.append('top')
            start=len(v);v.extend([[*xy(q)-O[:2],bottom(*q)-400] for q in ring[::-1]]);faces.append(list(range(start,start+3)));surface.append('bottom')
        for ring in [poly.exterior,*poly.interiors]:
            points=list(ring.coords)
            for a,b in zip(points,points[1:]):
                start=len(v);v.extend([[*xy(a)-O[:2],bottom(*a)-400],[*xy(b)-O[:2],bottom(*b)-400],[*xy(b)-O[:2],top(*b)-400],[*xy(a)-O[:2],top(*a)-400]])
                faces.append(list(range(start,start+4)));surface.append('side')
        parts.append({'name':name+(f'_{index}' if index else ''),'vertices':v,'faces':faces,'surface':surface,'role':role,'source':source_id,'plan_sd':mapping(poly),'area_m2':poly.area})

# Public paving is subdivided along actual longitudinal stationing. Boundaries
# are coincident, without inventing curbs across the shared promenade edge.
for i,s0 in enumerate(np.arange(-.25,122.5,2)):
    g=walk.intersection(box(s0,-2,s0+2,14))
    add_slab(f'PAVING_{i:03}',g,grade,lambda s,d:grade(s,d)-.18,'asphalt','av_bo_boflaeche_a.145')

step_lines=[];dividers=[]
for f in source['step_lines']:
    line=sd(shape(f['geometry']))
    if line.distance(stairs)>.025:continue
    q=np.array(line.coords); span=np.ptp(q,axis=0)
    if span[0]>span[1]*3:step_lines.append((f['id'],line))
    else:dividers.append((f['id'],line))

# All transverse cross-bands in the survey delimit separate prefabricated stair
# runs. Tiny sub-divisions at boat landings remain part of the same geometric
# construction; the actual longitudinal riser line endpoints are interpolated.
cuts=sorted([stairs.bounds[0],stairs.bounds[2],*[np.mean(np.array(g.coords)[:,0]) for _,g in dividers]])
cuts=[s for i,s in enumerate(cuts) if i==0 or s-cuts[i-1]>.06]
riser_records=[];stair_cells=[]
for bay,(s0,s1) in enumerate(zip(cuts,cuts[1:])):
    middle=(s0+s1)/2; region=stairs.intersection(box(s0,0,s1,14)).difference(main_walls)
    if region.is_empty:continue
    q0,q1=region.bounds[1],region.bounds[3]
    found=[]
    for ident,line in step_lines:
        q=np.array(line.coords);q=q[np.argsort(q[:,0])]
        if q[0,0]-.025<=middle<=q[-1,0]+.025:
            d=float(np.interp(middle,q[:,0],q[:,1]));found.append((d,ident,q))
    found.sort()
    unique=[]
    for item in found:
        if not unique or item[0]-unique[-1][0]>.05:unique.append(item)
    # Survey cross-bands (~0.6m wide) are sloped solid stringers separating the
    # runs, not fictitious traversable stair treads. They remain flush at top.
    if not unique:
        add_slab(f'STAIR_STRINGER_{bay:02}',region,
            lambda s,d:grade(s,q0)-min(10,max(0,(d-q0)/.30))*.165,
            lambda s,d:405.25,'stair_stringer','av_ei_flaechenelement_a.35398')
        continue
    boundaries=[(q0,None,None),*unique,(q1,None,None)]
    for k,(first,last) in enumerate(zip(boundaries,boundaries[1:])):
        def edge(item,s):
            if item[2] is None:return item[0]
            return float(np.interp(s,item[2][:,0],item[2][:,1]))
        poly=Polygon([(s0,edge(first,s0)),(s1,edge(first,s1)),(s1,edge(last,s1)),(s0,edge(last,s0))])
        g=region.intersection(poly)
        # At the lower end some 2022 riser records terminate against parapets.
        # No extra step lines are introduced to fill those source omissions.
        top=lambda s,d,k=k,q0=q0:grade(s,q0)-k*.165-.003*max(0,d-edge(first,s))
        name=f'TREAD_B{bay:02}_{k:02}'
        before=len(parts);add_slab(name,g,top,lambda s,d:405.25,'stair','av_ei_flaechenelement_a.35398')
        for part in parts[before:]:part['step_index']=k;part['bay']=bay;part['riser_source']=last[1]
        stair_cells.extend(polys(g))
        if last[1]:riser_records.append({'source':last[1],'bay':bay,'xy':mapping(last[2] is None and LineString([]) or LineString(last[2])),'rise_m_inferred':.165})

# Real river-facing parapet footprints, set above the low stair landing. The
# dimensions of caps and the cast surface remain an explicit interpretation.
for ident,g in walls.items():
    if ident.endswith('.18091'):
        top=lambda s,d:grade(s,max(0,d))+.045
        bottom=lambda s,d:406.20
    elif ident.endswith('.38597'):
        top=lambda s,d:grade(s,min(d,7.35))+.02
        bottom=lambda s,d:405.30
    else:
        top=lambda s,d:grade(s,7.35)-.75
        bottom=lambda s,d:405.25
    add_slab('PARAPET_'+ident.split('.')[-1],g,top,bottom,'parapet',ident)

# Check exact coverage before a Blender mutation. The interstitial strips are
# retained with the same source boundary, not hidden underneath a larger box.
covered=unary_union([shape(p['plan_sd']) for p in parts if p['role']!='parapet'])
expected=foot.union(stairs).difference(main_walls)
coverage_gap=expected.difference(covered).area
outside=covered.difference(expected).area
report={'footprint_m2':foot.area,'main_stair_m2':stairs.area,'walk_m2':walk.area,
    'source_stair_outside_paving_m2':stairs.difference(foot).area,
    'survey_longitudinal_step_lines':len(step_lines),'survey_cross_lines':len(dividers),'recovered_risers':len(riser_records),
    'grade_photo_cells':len(support),'grade_fit_coefficients':coef.tolist(),'grade_fit_residual_quantiles':np.quantile(res,[0,.05,.5,.95,1]).tolist(),
    'coverage_gap_m2':coverage_gap,'outside_source_m2':outside,'inferred_rise_m':.165,
    'height_basis':'Robust cached photo grade; exact previous native pavement datum along common edge. Step rise0.165m, structural thickness/caps and below-water footing are inference.',
    'source_geometry_unmodified':True,'runtime_use_verified':False}
assert outside<.003,(outside,coverage_gap)
# Any tiny polygonal cross-band remnants are explicitly surfaced; no unchecked
# hole is ignored because its shape is awkward to triangulate.
gap=expected.difference(covered)
for i,g in enumerate(polys(gap)):
    if g.area>.000001:
        add_slab(f'STAIR_BOUNDARY_FILL_{i}',g,lambda s,d:grade(s,7.36)-np.clip((d-7.36)/.30,0,10)*.165,lambda s,d:405.25,'stair_stringer','av_ei_flaechenelement_a.35398')
report['coverage_gap_after_m2']=expected.difference(unary_union([shape(p['plan_sd']) for p in parts if p['role']!='parapet'])).area
assert report['coverage_gap_after_m2']<.0001
plan={'base':'G1_020r4','version':'G1_021','origin':O.tolist(),'anchor':A.tolist(),'along':T.tolist(),'across':N.tolist(),
      'source_plan_lv95':features['av_bo_boflaeche_a.145']['geometry'],'parts':parts,'risers':riser_records,'report':report,
      'source_context_sha256':hashlib.sha256((D/'sources.json').read_bytes()).hexdigest()}
(D/'build_input.json').write_text(json.dumps(plan,separators=(',',':')),encoding='utf-8')
print(json.dumps({'parts':len(parts),'report':report},indent=2))
