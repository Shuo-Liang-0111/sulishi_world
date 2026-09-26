"""Dimension the photographed bank front and a continuous near-front pavement.

Keeps measured XY/envelope separate from inferred openings, floor and joinery.
This is a construction specification, not a claim of a surveyed interior.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from workspace_paths import read_path,write_path

paths=[read_path('derived/ubs_theaterstrasse20/'+name) for name in
       ['site_constraints.json','r8_geometry_probe.json','r8_paving_context.json']]
d,probe,paving=[json.loads(p.read_text()) for p in paths]
A,U,N=[np.array(d[k]) for k in ['A','U','N']];W=d['street_width_m']

def local(points):
    p=np.asarray(points);return np.column_stack(((p[:,:2]-A)@U,(p[:,:2]-A)@N,p[:,2]))

triangles=[];identities=[]
for row in probe['photo_objects']:
    t=local(row['vertices_world'])[np.asarray(row['triangles'])]
    cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(cross,axis=1)
    # The front frame is left-handed in XY; test upward normals in world space.
    orientation=float(np.linalg.det(np.stack([U,N])))
    valid=(length>1e-8)&(cross[:,2]*orientation>length*.96)
    valid&=(t[:,:,2].min(1)>8.25)&(t[:,:,2].max(1)<8.90)
    triangles.extend(t[valid]);identities.extend([row['name']]*int(valid.sum()))
T=np.asarray(triangles);lo=T[:,:,:2].min(1);hi=T[:,:,:2].max(1)
def hit(u,v):
    xy=np.array([u,v]);found=[]
    for idx in np.flatnonzero(((lo-1e-7<=xy)&(hi+1e-7>=xy)).all(1)):
        tri=T[idx];a,b=np.linalg.solve(np.column_stack((tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2])),xy-tri[0,:2])
        if a>=-1e-6 and b>=-1e-6 and a+b<=1.000001:
            found.append((float(tri[0,2]+a*(tri[1,2]-tri[0,2])+b*(tri[2,2]-tri[0,2])),identities[idx]))
    return sorted(found)[0] if found else None

photo_hit=hit
photo_T=T;photo_ids=identities.copy();photo_lo=lo;photo_hi=hi
sg=next(r for r in paving['meshes'] if r['name']=='SG_R7_CONTINUOUS_STREET_APPROACH')
sgv=local(sg['vertices']);T=sgv[np.asarray(sg['faces'])]
identities=[sg['name']]*len(T);lo=T[:,:,:2].min(1);hi=T[:,:,:2].max(1)
# The public cafe edge is an angled measured boundary in this building's frame.
# Derive it from mesh vertices, rather than assuming the two buildings are square.
left0=sgv[np.argmax(sgv[:,0])];left1=sgv[np.argmax(sgv[:,1])]
def left_u(v):return float(left0[0]+(v-left0[1])*(left1[0]-left0[0])/(left1[1]-left0[1]))
vmax=4.4;vs=np.linspace(0,vmax,41);side_anchors=[]
for v in vs:
    u=left_u(v);match=hit(u-.001,v)
    assert match is not None,('unmatched cafe edge',u,v)
    side_anchors.append(dict(u=u,v=float(v),z=match[0],source=sg['name']))
T=photo_T;identities=photo_ids;lo=photo_lo;hi=photo_hi
us=np.linspace(left_u(vmax),W+.025,121);anchors=[]
for u in us:
    match=hit(u,vmax)
    assert match is not None,('unsupported outer pavement boundary',u,vmax)
    anchors.append(dict(u=float(u),v=vmax,z=match[0],source=match[1]))
outer=np.array([r['z'] for r in anchors]);assert np.ptp(outer)<.22,(outer.min(),outer.max())
floor=8.58
def front_z(u):
    # The negative-u edge meets the existing side lane at its current level.
    # Raise only inside the building's front pier toward the inferred entrance.
    return float(8.474+np.clip(u/1.42,0,1)*(floor-8.474))
vertices=[];faces=[]
for j,v in enumerate(vs):
    xs=np.linspace(left_u(v),W+.025,len(us));fraction=v/vmax
    base_left=front_z(xs[0])*(1-fraction)+np.interp(xs[0],us,outer)*fraction
    for u in xs:
        z=front_z(u)*(1-fraction)+np.interp(u,us,outer)*fraction
        z+=max(0,1-(u-xs[0])/1.5)*(side_anchors[j]['z']-base_left)
        vertices.append([*list(A+U*u+N*v),float(z)])
n=len(us)
for j in range(len(vs)-1):
    for i in range(n-1):
        a=j*n+i;b=a+n;faces.extend([[a,b,b+1],[a,b+1,a+1]])
# A separate recessed entry strip stops inside the measured side wall; it does
# not overlap the pre-existing public side-lane pavement behind the corner.
start=len(vertices);inner_us=np.linspace(.10,W+.025,100)
for v in [-.82,0.]:
    for u in inner_us:vertices.append([*list(A+U*u+N*v),front_z(u)])
for i in range(len(inner_us)-1):
    a=start+i;b=a+len(inner_us);faces.extend([[a,b,b+1],[a,b+1,a+1]])
V=np.array(vertices);f=np.array(faces);cross=np.cross(V[f[:,1]]-V[f[:,0]],V[f[:,2]]-V[f[:,0]])
angles=np.degrees(np.arccos(cross[:,2]/np.linalg.norm(cross,axis=1)))
assert (cross[:,2]>0).all() and angles.max()<6.5,angles.max()

# Side wall follows the actual surveyed angled line; no orthogonal snapping.
C=np.array([2683628.157,1246859.681])-np.array(d['origin_lv95_ln02'][:2])
SU=(C-A)/np.linalg.norm(C-A);SN=np.array([-SU[1],SU[0]])
spec=dict(d)
spec.update(version='G1_027r9',base_version='G1_027r8',floor_z=floor,
    floor_basis='Inferred8.580m entrance, with a continuous corner transition to the existing cafe and side-lane levels. Official base5.103m is not used; outer edge is constrained by photography, left edge by the actual cafe pavement. Fabricated detail, not a surveyed entrance elevation.',
    side_A=A.tolist(),side_U=SU.tolist(),side_N=SN.tolist(),side_length_m=float(np.linalg.norm(C-A)),
    facade_eave_z=28.108,attic_floor_z=25.22,
    main_bays=[dict(a=1.42,b=5.01,panes=6),dict(a=5.96,b=10.81,panes=8),dict(a=11.70,b=15.43,panes=6)],
    bow_bay=dict(a=16.55,b=20.70,projection_m=.44,panels=6),
    levels=[dict(bottom=11.82,top=15.11,sill=12.33,head=14.55),
            dict(bottom=15.11,top=18.52,sill=15.86,head=18.08),
            dict(bottom=18.52,top=21.95,sill=19.16,head=21.38),
            dict(bottom=21.95,top=25.22,sill=22.60,head=24.64)],
    pavement=dict(vertices=vertices,faces=faces,outer_anchors=anchors,cafe_edge_anchors=side_anchors,local_bounds=[float(us[0]),float(us[-1]),-.82,vmax],max_slope_degrees=float(angles.max()),floor_is_inferred=True),
    front_cut_boxes=[[-.06,W+.06,-1.82,1.18,8.30,28.14]],
    side_cut_boxes=[[-.06,float(np.linalg.norm(C-A))+.035,-1.65,.68,8.30,28.14]],
    roof_cut_boxes=[[-1.45,W+.08,-17.80,1.31,27.91,33.30]],
    ground_cut_boxes=[[float(us[0]),float(us[-1]),0.,vmax,8.18,8.91],[.10,float(us[-1]),-.82,0.,8.18,8.91]],
    input_files=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
    detail_basis='MML front photograph constrains three divided office-window groups, projecting right bay, limestone, canopies and attic. Exact opening dimensions, floor divisions, side opening layout, panel fabrication and shallow interiors are inference.',
    limits=['No full bank/store interior or operational ATM is claimed.',
            'Higher foreground scan outside the rebuilt frontage remains pending separate identity/reconstruction.',
            'Unseen rear facade retains the source. Ground completion is not runtime walking acceptance.'])
out=write_path('derived/ubs_theaterstrasse20/build_input.json');out.write_text(json.dumps(spec,indent=2),encoding='utf-8')
print(json.dumps(dict(file=str(out),street_width_m=W,side_length_m=spec['side_length_m'],ground_anchors=len(anchors),ground_triangles=len(faces),max_slope_degrees=float(angles.max()))))
