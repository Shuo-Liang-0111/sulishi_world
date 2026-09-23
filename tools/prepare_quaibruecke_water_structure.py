"""Complete actual bridge/water component context after the rejected023 images.

Footprints are source AV, four piers are retained individually, and the hidden
river channel under the bridge is distinct from the bank's buried water records.
Mean water406.00 is the historical section datum, not a current gauge reading.
Unobserved water depth, steel sections, bearings and waves are interpretations.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/quaibruecke_water'
D.mkdir(exist_ok=True)
basepath=R/'derived/bellevue/quaibruecke_connection/build_input.json'
B=json.loads(basepath.read_text(encoding='utf-8'));O=np.array(B['origin'])
paths=[R/'sources/features/av_bo_boflaeche_a.geojson',R/'sources/features/av_ei_flaechenelement_a.geojson',
       R/'sources/features/quaibruecke/av_ei_context_extension.geojson']
F={}
for path in paths:
    for f in json.loads(path.read_text(encoding='utf-8'))['features']:
        if f['id'] in F:
            assert shape(f['geometry']).equals_exact(shape(F[f['id']]['geometry']),1e-7),f['id']
        F[f['id']]=f
def geom(ident):return shape(F[ident]['geometry'])
A=np.array(B['bridge_anchor']);T=np.array(B['bridge_along']);N=np.array(B['bridge_across']);coef=np.array(B['bridge_deck_coefficients'])
def xy(st,d):return A+st*T+d*N
def deck(x,y):
    st,d=(np.array([x,y])-A)@np.array([T,N]).T
    return float(coef@[1,st,st*st,d])
def polys(g):
    return [p for p in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[])) if p.geom_type=='Polygon' and p.area>1e-8]

bridge=geom('av_ei_flaechenelement_a.33090')
pier_ids=['av_ei_flaechenelement_a.'+str(i) for i in [37263,30702,33057,33079]]
piers=[geom(i) for i in pier_ids]
centres=[float((np.array(g.centroid.coords[0])-A)@T) for g in piers]
assert all(22<q<27 for q in np.diff(centres))
# Source pier centres and the historic five spans agree within source alignment;
# do not force the actual AV positions onto perfectly repeated design intervals.
station_end=centres[-1]+22.625
spans=[0.,*centres,station_end]
water_ids=['av_bo_boflaeche_a.16660','av_bo_boflaeche_a.21372']
open_water=unary_union([geom(i) for i in water_ids])
channel=geom('av_ei_flaechenelement_a.39381')
trough=shape(B['corridor'])
old_low=json.loads((R/'derived/bellevue/riviera_lower/build_input.json').read_text(encoding='utf-8'))
old_walk=unary_union([shape(p['plan']) for p in old_low['parts'] if p['role']=='paving'])
exclusions=unary_union([*piers,trough,old_walk])
water=unary_union([open_water,channel]).difference(exclusions).buffer(0)
assert water.intersection(trough).area<1e-6
assert all(water.intersection(g).area<1e-6 for g in piers)

parts=[]
def solid(name,g,top,bottom,role,source):
    for k,p in enumerate(polys(g)):
        p=orient(p,1);verts=[];faces=[]
        for tri in constrained_delaunay_triangles(p).geoms:
            q=list(orient(tri,1).exterior.coords)[:3]
            for fn,rev in [(top,False),(bottom,True)]:
                start=len(verts);verts.extend([[x-O[0],y-O[1],fn(x,y)-400] for x,y in (q[::-1] if rev else q)])
                faces.append([start,start+1,start+2])
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
                j=len(verts);verts.extend([[a[0]-O[0],a[1]-O[1],bottom(*a)-400],
                    [b[0]-O[0],b[1]-O[1],bottom(*b)-400],[b[0]-O[0],b[1]-O[1],top(*b)-400],
                    [a[0]-O[0],a[1]-O[1],top(*a)-400]])
                faces.append([j,j+1,j+2,j+3])
        parts.append(dict(name=name+(f'_{k}' if k else ''),vertices=verts,faces=faces,
                          role=role,source=source,plan=mapping(p),area_m2=p.area))

# Join the existing eastern22.625m slab, keeping its geometry. Remaining AV edge
# bands fill the small KUBA-vs-AV footprint difference instead of duplicating it.
old_bay=shape(B['bridge_bay'])
new_deck=bridge.difference(old_bay)
for i,st in enumerate(np.arange(-1.,station_end+1,2.)):
    mask=Polygon([xy(st,-2),xy(st+2,-2),xy(st+2,33),xy(st,33)])
    solid(f'DECK_{i:03}',new_deck.intersection(mask),lambda x,y:deck(x,y)-.11,
          lambda x,y:deck(x,y)-.40,'concrete','AV33090; source-photo deck curve; inferred thickness')

girders=[];bearings=[]
for k,d in enumerate([4.69,11.79,18.89,25.99]):
    stations=np.unique(np.r_[np.linspace(22.625,station_end,397),centres])
    rows=[]
    for st in stations:
        si=min(int(np.searchsorted(spans,st,side='right')-1),4)
        left,right=spans[si:si+2];u=(st-(left+right)/2)/((right-left)/2)
        end_depth=1.95 if si==4 and u>0 else 3.0
        depth=1.1+u*u*(end_depth-1.1)
        if st<=centres[0]:
            # Match the actual retained first-span lower edge, not a new curve.
            prior=np.array(B['girders'][k]['stations']);low=float(prior[-1,4])
            top=deck(*xy(st,d))-.42;depth=top-low
        p=xy(st,d);top=deck(*p)-.42
        rows.append([float(st),*p,top,top-depth])
    girders.append(dict(index=k,across=d,stations=rows))

for j,(ident,p,st) in enumerate(zip(pier_ids,piers,centres)):
    levels=[float(np.interp(st,np.array(g['stations'])[:,0],np.array(g['stations'])[:,4])) for g in girders]
    cap=min(levels)-.18
    solid(f'PIER_{ident.split(".")[-1]}',p,lambda x,y,z=cap:z,lambda x,y:402.8,'pier',ident)
    # Bearing block, pad and top plate actually bridge the cap-to-girder gap.
    for k,d in enumerate([4.69,11.79,18.89,25.99]):
        c=xy(st,d);bottom=cap;top=levels[k]
        foot=Polygon([c+T*a+N*b for a,b in [(-.48,-.48),(.48,-.48),(.48,.48),(-.48,.48)]])
        assert p.buffer(.002).covers(foot)
        solid(f'BEARING_{j}_{k}_PLINTH',foot,lambda x,y,z=top-.095:z,lambda x,y,z=bottom:z,'pier','inferred bearing plinth on '+ident)
        solid(f'BEARING_{j}_{k}_PAD',foot.buffer(-.04),lambda x,y,z=top-.018:z,lambda x,y,z=top-.095:z,'rubber','inferred elastomer bearing')
        solid(f'BEARING_{j}_{k}_PLATE',foot.buffer(-.02),lambda x,y,z=top+.006:z,lambda x,y,z=top-.018:z,'steel','inferred bearing plate')
        bearings.append(dict(pier=ident,girder=k,xy=c.tolist(),cap_ln02_m=cap,girder_lower_ln02_m=top))

# West abutment is outside the G1 walking area but required to support the whole
# visible bridge. Plan clipped to actual bridge, with hidden mass inferred.
west=bridge.intersection(Polygon([xy(station_end-.10,-2),xy(station_end+1.5,-2),xy(station_end+1.5,33),xy(station_end-.10,33)]))
solid('WEST_ABUTMENT',west,lambda x,y:deck(x,y)-2.35,lambda x,y:402.8,'pier','AV33090; west abutment mass inferred')

# Water top uses spatially uniform2m cells, keeping all cadastral boundaries.
# Continuous small geometry waves; shading carries fine ripples independently.
def water_z(x,y):
    u=x-O[0];v=y-O[1]
    return 406.+.006*math.sin(u*.83+v*.41)+.004*math.sin(u*.37-v*.61+.7)
verts=[];faces=[];top_faces=0
step=2.;bounds=water.bounds
for x in np.arange(math.floor(bounds[0]/step)*step,bounds[2],step):
    for y in np.arange(math.floor(bounds[1]/step)*step,bounds[3],step):
        cell=water.intersection(box(x,y,x+step,y+step))
        for p in polys(cell):
            for tri in constrained_delaunay_triangles(p).geoms:
                q=list(orient(tri,1).exterior.coords)[:3];off=len(verts)
                verts.extend([[a-O[0],b-O[1],water_z(a,b)-400] for a,b in q]);faces.append([off,off+1,off+2]);top_faces+=1
for face in list(faces):
    q=[verts[i] for i in face[::-1]];off=len(verts)
    verts.extend([[x,y,-5.] for x,y,z in q]);faces.append([off,off+1,off+2])
for p in polys(water):
    p=orient(p,1)
    for ring in [p.exterior,*p.interiors]:
        # Match grid intersections on the boundary to avoid T-junctions.
        points=[]
        for a,b in zip(list(ring.coords),list(ring.coords)[1:]):
            a=np.array(a);b=np.array(b);ts=[0.]
            for axis in [0,1]:
                if abs(b[axis]-a[axis])>1e-10:
                    cuts=np.arange(math.ceil(min(a[axis],b[axis])/step)*step,max(a[axis],b[axis]),step)
                    ts.extend(float(t) for t in (cuts-a[axis])/(b[axis]-a[axis]) if 1e-9<t<1-1e-9)
            points.extend(a+(b-a)*t for t in sorted(set(ts)))
        for a,b in zip(points,points[1:]+points[:1]):
            off=len(verts);verts.extend([[a[0]-O[0],a[1]-O[1],-5],[b[0]-O[0],b[1]-O[1],-5],
                [b[0]-O[0],b[1]-O[1],water_z(*b)-400],[a[0]-O[0],a[1]-O[1],water_z(*a)-400]])
            faces.append([off,off+1,off+2,off+3])
parts.append(dict(name='WATER_CONTINUOUS',vertices=verts,faces=faces,role='water',source='AV16660+21372+39381;1985 mean-water datum',
                  plan=mapping(water),area_m2=water.area,top_faces=top_faces))
report=dict(water_surface_plan_m2=water.area,mean_water_level_ln02_m=406.0,water_gauge_date_verified=False,
            bathymetry_surveyed=False,volume_bottom_inferred_ln02_m=395.,water_wave_max_amplitude_bound_m=.010,
            source_pier_ids=pier_ids,source_pier_stations_m=centres,historic_span_lengths_m=[22.625,24.76,26.52,24.76,22.625],
            actual_centreline_span_interpretation_m=np.diff(spans).tolist(),additional_bridge_slab_plan_m2=new_deck.area,
            g1_walking_scope_expanded=False,public_underpass_excluded_from_water=True,
            bank_buried_water_records_not_opened=['av_ei_flaechenelement_a.28347','av_ei_flaechenelement_a.28358','av_ei_flaechenelement_a.12074'])
out=dict(version='G1_024',origin=O.tolist(),parts=parts,girders=girders,bearings=bearings,spans=spans,
         water=mapping(water),bridge=mapping(bridge),piers=[dict(id=i,geometry=mapping(g)) for i,g in zip(pier_ids,piers)],
         source_features=[F[i] for i in [*water_ids,'av_ei_flaechenelement_a.39381','av_ei_flaechenelement_a.33090',*pier_ids]],
         report=report,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [basepath,*paths]})
(D/'build_input.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print(json.dumps({'parts':len(parts),'water_triangles':top_faces,'report':report}))
