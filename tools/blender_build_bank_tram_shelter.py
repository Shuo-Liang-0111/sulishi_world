"""Current r11 -> r12: bank-side Bellevue platform, canopy and ordinary fixtures."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state
from blender_apply_barycentric_cut import apply as apply_cut


def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


s = bpy.context.scene
assert s['version'] == 'G1_027r11'
assert sha(bpy.data.filepath) == '90df6b61e3dc1beef7d0a33abf9365a98dcf7af35eafd06209ebd46bf30f74db'
lease = json.loads(read_path('runtime/coordination/blender_lease.json').read_text())
assert lease['owner_role'] == 'main' and lease['main_may_launch'] and not lease['secondary_may_launch']
version = 'G1_027r12'
target = write_path('native/G1_027r12_bank_tram_shelter.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
checkpoint = json.loads(read_path('evidence/G1_027r11/checkpoint.json').read_text())
paths = [read_path('derived/bellevue/bank_tram_shelter/' + name) for name in
         ['build_input.json', 'platform_input.json', 'fixtures_input.json', 'photo_replacement.json']]
d, platform, fixtures, cut = [json.loads(p.read_text()) for p in paths]
assert platform['report']['ready_for_native_build']
for parent, key in [(d, 'source_files'), (platform['report'], 'source_files'), (fixtures, 'sources'), (cut, 'preparation_inputs')]:
    for row in parent[key]: assert sha(row['path']) == row['sha256'], row['path']
bpy.context.view_layer.update()
before = {o.name: object_state(o) for o in s.objects}
pointers = {o.name: o.data.as_pointer() for o in s.objects if o.type == 'MESH'}
old_cameras = {o.name: dict(matrix=[list(v) for v in o.matrix_world], lens=o.data.lens, sensor_width=o.data.sensor_width)
               for o in s.objects if o.type == 'CAMERA'}
source = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
source_pointers = {o.name: o.data.as_pointer() for o in source.objects}; assert len(source_pointers) == 2039
for row in cut['rows']:
    ob = bpy.data.objects[row['object']]
    assert json.loads(json.dumps(mesh_digest(ob.data))) == row['source_mesh_digest']
    assert [list(r) for r in ob.matrix_world] == row['source_matrix_world']
for row in platform['report']['current_native_road_basis']['current_road_objects']:
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['name']].data))) == row['actual_mesh_digest']

collection = bpy.data.collections.new('47_BELLEVUE_BANK_TRAM_SHELTER')
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(collection)
collection['source_id'] = 'EGID302063028 / VBZ73 / AV355+456+457'
collection['public_runtime_enabled'] = False
collection['evidence_basis'] = d['basis']
A, U, N = [np.array(d[k]) for k in ['axis_start_local_xy', 'axis_unit_xy', 'side_unit_xy']]
length = d['axis_length_m']


def frame(center, axis, normal=None):
    c, u = np.asarray(center), np.asarray(axis)
    n = np.asarray(normal) if normal is not None else np.array([-u[1], u[0]])
    assert abs(np.linalg.det(np.stack([u, n], axis=1))-1) < 1e-6
    return lambda x, y, z: np.r_[c+u*x+n*y, z]


P = frame(A, U, N)
floor_tri = np.array(platform['parts']['asphalt'] + platform['parts']['curb_top'])
roof_tri = np.array(d['parts']['soffit'])


def sample(triangles, xy):
    xy = np.asarray(xy)
    candidates = np.flatnonzero(np.all(xy >= triangles[:, :, :2].min(1)-1e-7, axis=1) &
                               np.all(xy <= triangles[:, :, :2].max(1)+1e-7, axis=1))
    for i in candidates:
        t = triangles[i]; matrix = (t[1:, :2]-t[0, :2]).T
        if abs(np.linalg.det(matrix)) < 1e-11: continue
        w = np.linalg.solve(matrix, xy-t[0, :2])
        if min(w) >= -1e-6 and w.sum() <= 1.000001:
            return float(t[0, 2]+w @ (t[1:, 2]-t[0, 2]))
    raise AssertionError(('Missing constructed supporting triangle', xy.tolist()))


def ground(xy): return sample(floor_tri, xy)


def material(name, color, rough=.5, metal=0):
    m = bpy.data.materials.new('BST | ' + name); m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
    m['basis'] = 'Photo-guided material family. Optical values and bounded wear are inference.'
    return m


concrete = material('painted concrete soffit', (.48, .465, .429), .77)
roof = material('standing seam zinc', (.31, .325, .33), .43, .72)
metal = material('satin aluminium frames', (.36, .39, .40), .29, .85)
dark = material('graphite frame finish', (.026, .032, .035), .51, .38)
seal = material('rubber gaskets', (.008, .009, .01), .84)
grey = material('equipment enamel', (.39, .414, .409), .43, .22)
blue = material('ZVV equipment blue', (.009, .111, .27), .43, .12)
white = material('neutral paper', (.74, .721, .68), .9)
screen = material('screen dark cover', (.034, .07, .088), .16, .03)
light = material('recessed opal lens', (.64, .615, .54), .37)
bs = next(n for n in light.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bs.inputs['Emission Color'].default_value = (1, .84, .64, 1); bs.inputs['Emission Strength'].default_value = 1.3
glass = material('windscreen clear glass', (.91, .95, .98), .055)
bs = next(n for n in glass.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bs.inputs['Transmission Weight'].default_value = 1.; bs.inputs['IOR'].default_value = 1.46
asphalt = bpy.data.materials['asphalt_03'].copy(); asphalt.name = 'BST | source-scale asphalt'
curb = bpy.data.materials.get('BE | fine mineral curb proxy', bpy.data.materials['concrete_floor_01']).copy()
curb.name = 'BST | fine mineral kerb'
wood = bpy.data.materials['oak_veneer_01'].copy(); wood.name = 'BST | bench wood'
joint = material('kerb joint mortar', (.115, .119, .116), .94)
poster_mats = [material('original poster navy', (.028, .058, .092), .91),
               material('original poster ochre', (.31, .157, .056), .92)]
# Millimetre-scale finish, not global dirt. Low-amplitude broad variation keeps
# the curved concrete readable without making it look like mottled plaster.
for mat, amplitude in [(concrete, .00011), (roof, .000025), (grey, .000012)]:
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nodes.new('ShaderNodeTexCoord'); noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 160; noise.inputs['Detail'].default_value = 2
    links.new(tex.outputs['Object'], noise.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump'); bump.inputs['Distance'].default_value = amplitude; bump.inputs['Strength'].default_value = .22
    links.new(noise.outputs['Fac'], bump.inputs['Height']); links.new(bump.outputs['Normal'], bs.inputs['Normal'])

groups = {}


def add(name, vertices, faces, mat, role, source_id, bevel=0, smooth=False):
    key = (name, mat.name)
    g = groups.setdefault(key, dict(vertices=[], faces=[], mat=mat, role=role, source_id=source_id,
                                   bevel=bevel, smooth=smooth))
    offset = len(g['vertices']); g['vertices'].extend([list(p) for p in vertices])
    g['faces'].extend([[offset+i for i in face] for face in faces])


def triangles(name, rows, mat, role, source_id, smooth=False):
    vertices = np.asarray(rows).reshape(-1, 3)
    add(name, vertices, np.arange(len(vertices)).reshape(-1, 3), mat, role, source_id, smooth=smooth)


def box(name, center, size, mat, role, source_id, f=P, bevel=.003):
    c, z = np.asarray(center), np.asarray(size)/2
    vertices = [f(*(c+z*np.array(v))) for v in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                 (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    add(name, vertices, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],
        mat, role, source_id, bevel)


def tube(name, points, radius, mat, role, source_id, sides=12):
    points = np.asarray(points); vertices, faces = [], []
    for j, p in enumerate(points):
        axis = points[min(j+1,len(points)-1)]-points[max(0,j-1)]; axis /= np.linalg.norm(axis)
        seed = [0,0,1] if abs(axis[2]) < .95 else [1,0,0]
        x = np.cross(axis, seed); x /= np.linalg.norm(x); y = np.cross(axis, x)
        vertices.extend(p+radius*(x*np.cos(a)+y*np.sin(a)) for a in np.arange(sides)*math.tau/sides)
    for j in range(len(points)-1):
        for k in range(sides):
            a, b = j*sides+k, j*sides+(k+1)%sides; faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)), tuple((len(points)-1)*sides+k for k in range(sides))])
    add(name, vertices, faces, mat, role, source_id, smooth=True)


footings = []
def foot(name, x, y, ztop, width, depth, mat, source_id, f, role='facility_support'):
    xy = np.array(f(x,y,0))[:2]
    bottom = min(ground(np.array(f(x+a,y+b,0))[:2]) for a,b in
                 [(-width/2,-depth/2),(width/2,-depth/2),(width/2,depth/2),(-width/2,depth/2)])-.003
    assert ztop > bottom
    box(name, (x,y,(ztop+bottom)/2), (width,depth,ztop-bottom), mat, role, source_id, f)
    footings.append(dict(object=name, xy=xy.tolist(), bottom=bottom, top=ztop, source_id=source_id))


for key, rows in platform['parts'].items():
    triangles('BST_PLATFORM_'+key.upper(), rows,
              asphalt if key=='asphalt' else joint if key=='curb_joint' else curb,
              'walk_surface' if key in ['asphalt','curb_top'] else 'kerb', 'AV355/456/457')
for key, rows in d['parts'].items():
    triangles('BST_CANOPY_'+key.upper(), rows, concrete if key=='soffit' else roof,
              'canopy', 'Roof177510/EGID302063028', smooth=key in ['roof_metal','soffit'])
for i, points in enumerate(d['standing_seams']):
    tube('BST_ROOF_FOLDS', points, .0042, roof, 'roof_fabrication', 'inferred: folded sheet metal', sides=8)
zmin, zmax = d['source_height_envelope_local']
box('BST_CENTRAL_DRAIN_CHANNEL', (length/2,0,zmax-.173), (length,.12,.018), dark,
    'drainage', 'Immobilia2016: central drainage', bevel=.002)
# Each mushroom head meets the actual triangulated soffit at its whole rim.
column_checks = []
for index, xy in enumerate(d['inferred_support_centres_local_xy']):
    xy = np.array(xy); z = ground(xy); floor_support = []
    angle = np.arange(64)*math.tau/64
    rings = []
    for radius, height in [(.205,z-.006),(.205,z+.022),(.176,z+.055),(.176,zmin-.78),(.19,zmin-.69),
                            (.22,zmin-.50),(.265,zmin-.29),(.32,zmin-.12),(.405,None)]:
        ring = []
        for a in angle:
            p = xy+radius*np.array([math.cos(a),math.sin(a)])
            zz = sample(roof_tri,p)+.005 if height is None else height
            if height == z-.006: zz = ground(p)-.006; floor_support.append([*p,zz])
            ring.append([*p,zz])
        rings.append(ring)
    vertices = np.array(rings).reshape(-1,3); faces = []
    for j in range(len(rings)-1):
        for k in range(64): faces.append((j*64+k,j*64+(k+1)%64,(j+1)*64+(k+1)%64,(j+1)*64+k))
    faces.extend([tuple(range(63,-1,-1)), tuple((len(rings)-1)*64+k for k in range(64))])
    name = f'BST_COLUMN_{index}'
    add(name, vertices, faces, concrete, 'column', 'inferred three mushroom supports', smooth=True)
    column_checks.append(dict(object=name, xy=xy.tolist(), floor_z=z, buried_base=floor_support, top_ring=rings[-1]))
    f = frame(xy,U,N)
    box(name+'_SERVICE_COVER',(0,.176,z+.47),(.11,.009,.25),grey,'service_hatch','inferred access cover',f, .004)
    for dz in [-.095,.095]:
        tube(name+'_COVER_FIXINGS',[f(0,.18,z+.47+dz),f(0,.187,z+.47+dz)],.006,metal,'fixing','inferred service fastener',8)
for u in np.linspace(.7,length-.7,6):
    xy=P(u,.42,0)[:2]; z=sample(roof_tri,xy)
    tube('BST_RECESSED_LIGHT_TRIM',[np.r_[xy,z-.012],np.r_[xy,z+.008]],.043,dark,'light','inferred recessed lighting',24)
    tube('BST_RECESSED_LIGHT_LENS',[np.r_[xy,z-.014],np.r_[xy,z-.012]],.034,light,'light','inferred recessed lighting',24)

lettering = []
def label(name, body, x, y, z, size, mat, f, axis, normal):
    lettering.append(dict(name=name,body=body,position=list(f(x,y,z)),size=size,mat=mat,axis=list(axis),normal=list(normal)))


for index, row in enumerate(fixtures['ads']):
    ident=row['source_id']; f=frame(row['center_xy'],row['axis'],row['front']); z=row['floor_z'];w=row['inferred_width_m'];h=row['inferred_height_m'];bottom=z+.38
    box(f'BST_AD_{index}_CORE',(0,0,bottom+h/2),(w,.075,h),dark,'advertising_case',ident,f,.009)
    for side in [-1,1]:
        box(f'BST_AD_{index}_PRINT_{side}',(0,side*.039,bottom+h/2),(w-.075,.002,h-.075),poster_mats[index],'inferred_artwork',ident,f,.001)
        box(f'BST_AD_{index}_GLASS_{side}',(0,side*.046,bottom+h/2),(w-.068,.008,h-.068),glass,'glazing',ident,f,.002)
        for x in [-w/2+.018,w/2-.018]:box(f'BST_AD_{index}_FRAME',(x,side*.045,bottom+h/2),(.036,.03,h),metal,'frame',ident,f)
        for zz in [bottom+.019,bottom+h-.019]:box(f'BST_AD_{index}_FRAME',(0,side*.045,zz),(w,.03,.038),metal,'frame',ident,f)
        side_axis=np.array(row['axis'])*(-side)
        side_normal=np.array(row['front'])*side
        # Text uses its own vertical basis, so place against the actual normal
        # instead of passing a reflected frame to the solid-geometry helper.
        tf=lambda x,y,z,ff=f,sg=side:ff(-sg*x,sg*y,z)
        label(f'BST_AD_{index}_TITLE_{side}', ['Zürich','Am Wasser'][index],-.45,.041,bottom+h-.30,.15,white,tf,side_axis,side_normal)
        label(f'BST_AD_{index}_SUBTITLE_{side}','Wege und Begegnungen',-.45,.041,bottom+.24,.048,white,tf,side_axis,side_normal)
        for k in range(5):
            points=[f(x,side*.041,bottom+.64+k*.115+.055*math.sin(x*4+k*.8)) for x in np.linspace(-.45,.45,26)]
            tube(f'BST_AD_{index}_ART',points,.0012,white,'inferred_artwork',ident,6)
    for x in [-w/2+.018,w/2-.018]:
        foot(f'BST_AD_{index}_LEG_{x:.3f}',x,0,bottom,.045,.075,metal,ident,f)

for index,row in enumerate(fixtures['benches']):
    ident=row['source_id']; f=frame(row['centre_xy'],row['axis'],row['front']);z=row['floor_z'];L=row['inferred_length_m']
    for k in range(6):box(f'BST_BENCH_{index}_SEAT',(0,-.228+k*.091,z+.465),(L,.079,.038),wood,'seat',ident,f,.008)
    for k in range(5):box(f'BST_BENCH_{index}_BACK',(0,-.263-k*.01,z+.60+k*.081),(L,.035,.069),wood,'seat_back',ident,f,.006)
    for j,u in enumerate([-L*.37,L*.37]):
        for v in [-.225,.225]:
            gz=ground(f(u,v,0)[:2]);foot(f'BST_BENCH_{index}_FOOT_{j}_{v}',u,v,gz+.015,.095,.09,dark,ident,f)
            tube(f'BST_BENCH_{index}_LEG',[f(u,v,gz+.007),f(u,v*.86,z+.416)],.021,dark,'seat_support',ident)
        tube(f'BST_BENCH_{index}_SEAT_RAIL',[f(u,-.262,z+.418),f(u,.263,z+.418)],.02,dark,'seat_support',ident)
        tube(f'BST_BENCH_{index}_BACK_RAIL',[f(u,-.20,z+.41),f(u,-.30,z+.56),f(u,-.342,z+.95)],.019,dark,'seat_support',ident)
        tube(f'BST_BENCH_{index}_ARM',[f(u,-.30,z+.66),f(u,-.17,z+.70),f(u,.225,z+.69),f(u,.245,z+.60)],.017,metal,'armrest',ident)

row=fixtures['ticket'];ident=row['source_id'];f=frame(row['center_xy'],row['axis'],row['front']);z=row['floor_z'];w=row['width_m'];depth=row['depth_m']
box('BST_TICKET_BODY',(0,0,z+1.23),(w,depth,1.55),grey,'ticket_machine',ident,f,.022)
for x in [-w*.35,w*.35]:
    gz=ground(f(x,0,0)[:2]);foot(f'BST_TICKET_FOOT_{x}',x,0,gz+.018,.11,.18,metal,ident,f)
    tube('BST_TICKET_LEGS',[f(x,0,gz+.012),f(x,0,z+1.96)],.027,metal,'equipment_support',ident)
box('BST_TICKET_BLUE_FACE',(-.075,depth/2+.006,z+1.235),(.62,.02,1.41),blue,'equipment_front',ident,f,.013)
box('BST_TICKET_SCREEN_GASKET',(-.08,depth/2+.020,z+1.36),(.466,.015,.418),seal,'gasket',ident,f,.008)
box('BST_TICKET_SCREEN',(-.08,depth/2+.030,z+1.36),(.435,.006,.385),screen,'display_inactive',ident,f,.004)
box('BST_TICKET_PAYMENT_RECESS',(.31,depth/2+.014,z+1.37),(.18,.02,.88),dark,'equipment_front',ident,f,.011)
box('BST_TICKET_CARD_READER',(.31,depth/2+.048,z+1.20),(.136,.074,.234),grey,'card_reader',ident,f,.009)
box('BST_TICKET_CARD_LCD',(.31,depth/2+.088,z+1.26),(.094,.009,.055),screen,'display_inactive',ident,f,.003)
for i in range(3):
    for j in range(3):box('BST_TICKET_PIN_KEYS',(.278+j*.032,depth/2+.088,z+1.205-i*.025),(.023,.008,.016),metal,'key',ident,f,.002)
box('BST_TICKET_CARD_SLOT',(.31,depth/2+.089,z+1.118),(.094,.009,.009),seal,'slot',ident,f,.001)
box('BST_TICKET_COIN_PLATE',(.31,depth/2+.032,z+1.654),(.13,.03,.14),metal,'payment',ident,f,.008)
box('BST_TICKET_COIN_SLOT',(.31,depth/2+.049,z+1.654),(.071,.006,.008),seal,'slot',ident,f,.001)
box('BST_TICKET_OUTPUT',(-.08,depth/2+.033,z+.80),(.31,.04,.079),dark,'ticket_tray',ident,f,.005)
box('BST_TICKET_OUTPUT_LIP',(-.08,depth/2+.06,z+.764),(.31,.027,.014),metal,'ticket_tray',ident,f,.003)
for k in range(9):box('BST_TICKET_REAR_VENT',(0,-depth/2-.003,z+.64+k*.021),(.45,.008,.006),dark,'vent',ident,f,.001)
label('BST_TICKET_ZVV','ZVV',.35,depth/2+.022,z+1.84,.075,white,f,-np.array(row['axis']),row['front'])
label('BST_TICKET_BILLETS','Billette',.06,depth/2+.058,z+.89,.027,white,f,-np.array(row['axis']),row['front'])
info=row['nearby_info'];ip=np.array(info['anchor_xy']);inf=frame(ip,row['axis'],row['front'])
# The unresolved type85 identity is retained without fabricating route numbers
# or departures. This small co-mounted board is explicitly an inferred detail.
iz=z+2.18
box('BST_INFO2354_FRAME',(0,0,iz),(.54,.045,.30),grey,'inferred_information_board',info['source_id'],inf,.008)
box('BST_INFO2354_FACE',(0,.025,iz),(.50,.007,.255),blue,'inferred_information_board',info['source_id'],inf,.003)
label('BST_INFO2354_TITLE','Bellevue',.22,.031,iz-.025,.067,white,inf,-np.array(row['axis']),row['front'])
for x in [-.19,.19]:tube('BST_INFO2354_BRACKET',[inf(x,0,z+1.93),inf(x,0,iz-.145)],.012,metal,'bracket',info['source_id'])

created=[]
for (name,_),g in groups.items():
    me=bpy.data.meshes.new(name);me.from_pydata(g['vertices'],[],g['faces']);me.update()
    assert not me.validate(clean_customdata=False),name
    if name in ['BST_CANOPY_ROOF_METAL','BST_CANOPY_SOFFIT']:
        bm=bmesh.new();bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        bm.to_mesh(me);bm.free();me.update()
    ob=bpy.data.objects.new(name,me);collection.objects.link(ob);me.materials.append(g['mat'])
    for poly in me.polygons:poly.use_smooth=g['smooth']
    uv=me.uv_layers.new(name='metric_surface')
    for face in me.polygons:
        axes=np.argsort(abs(np.array(face.normal)))[:2]
        for li in face.loop_indices:
            q=np.array(me.vertices[me.loops[li].vertex_index].co)
            if g['mat']==wood:
                owner=next(b for b in fixtures['benches'] if b['source_id']==g['source_id']);delta=q[:2]-owner['centre_xy']
                uv.data[li].uv=(float(delta @ owner['axis'])/2,(q[2]-owner['floor_z'] if abs(face.normal.z)<.5 else float(delta @ owner['front']))/2)
            elif g['mat']==curb:uv.data[li].uv=(q[axes[0]]/.667,q[axes[1]]/.667)
            elif name.startswith('BST_PLATFORM_'):uv.data[li].uv=(q[0]/2.05,q[1]/2.05)
            else:uv.data[li].uv=(q[axes[0]]/2,q[axes[1]]/2)
    if g['bevel']:
        mod=ob.modifiers.new('material-scale edge','BEVEL');mod.width=g['bevel'];mod.segments=3
        ob.modifiers.new('face normals','WEIGHTED_NORMAL')
    ob['source_id']=g['source_id'];ob['bst_role']=g['role'];ob['construction_batch']=version
    ob['evidence_basis']=d['basis']+' Fixture manufacturing and unknown type85 panel are inference.'
    ob['public_runtime_enabled']=False;ob['collision_role']='solid_pending_runtime'
    created.append(ob.name)
for row in lettering:
    cu=bpy.data.curves.new(row['name'],'FONT');cu.body=row['body'];cu.size=row['size'];cu.resolution_u=5;cu.extrude=.00015
    ob=bpy.data.objects.new(row['name'],cu);collection.objects.link(ob);ob.location=row['position']
    x=Vector((*row['axis'],0));y=Vector((0,0,1));n=Vector((*row['normal'],0));assert x.cross(y).dot(n)>.999
    ob.rotation_euler=Matrix((x,y,n)).transposed().to_euler();cu.materials.append(row['mat'])
    ob['bst_role']='lettering';ob['collision_role']='visual_nonblocking';ob['evidence_basis']='Original neutral artwork or actual place/service name, not installed advertisement or live timetable.'
    created.append(ob.name)
bpy.context.view_layer.update()
cuts=[apply_cut(bpy.data.objects[row['object']],row) for row in cut['rows']]
changed={r['object'] for r in cuts}
assert all(object_state(bpy.data.objects[name])==state for name,state in before.items())
assert all(bpy.data.objects[n].data.as_pointer()==p for n,p in pointers.items() if n not in changed)
assert {o.name:o.data.as_pointer() for o in source.objects}==source_pointers

camera_rows=[]
for name,along,across,look,lens in [
    ('BST_QA_NORTH',-6.,.25,(length*.42,0,10.8),30),
    ('BST_QA_SOUTH',length+7.,.8,(length*.45,0,10.6),32),
    ('BST_QA_SEATING',length*.62,2.10,(length*.55,.35,9.6),28)]:
    eye=P(along,across,0);eye[2]=ground(eye[:2])+1.65
    cam=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,cam);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob)
    ob.location=eye;ob.rotation_euler=(Vector(P(*look))-ob.location).to_track_quat('-Z','Y').to_euler();cam.lens=lens;cam.clip_end=1200
    camera_rows.append(dict(name=name,eye=eye.tolist(),target=P(*look).tolist(),eye_height_m=1.65,lens=lens))
for name,row in old_cameras.items():
    ob=bpy.data.objects[name]
    assert dict(matrix=[list(v) for v in ob.matrix_world],lens=ob.data.lens,sensor_width=ob.data.sensor_width)==row

s['version']=version;s['latest_construction']='Bank-side Bellevue platform, real shelter envelope, columns and source-located ordinary facilities'
report=dict(version=version,base_native_sha256=checkpoint['native_sha256'],
    prepared_files=[dict(path=str(p),sha256=sha(p)) for p in paths],created=created,
    author_states={o.name:object_state(o) for o in collection.objects},
    author_meshes={o.name:mesh_digest(o.data) for o in collection.objects if o.type=='MESH'},
    bounded_photo_cuts=cuts,old_cameras=old_cameras,review_cameras=camera_rows,column_checks=column_checks,footings=footings,
    source_objects_unchanged=2039,old_objects_unchanged=len(before),public_runtime_enabled=False,
    visual_acceptance=False,natural_use_verified=False,
    limits=['Platform preparation is constrained reconstruction, not surveyed pavement engineering.','Info2354/type85 subtype and exact assembly unresolved: small panel inferred.','Facilities have editable physical geometry but natural operation/runtime remain pending.'])
write_path(f'evidence/{version}/bank_shelter_build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for name in ['build_report.json','ubs_build_report.json','nearfront_build_report.json','sf1_merge_report.json']:
    old=json.loads(read_path(f'evidence/G1_027r11/{name}').read_text());old['version']=version;old['preserved_report_base']='G1_027r11'
    counts={n:len(bpy.data.objects[n].data.polygons) for n in changed}
    if name=='build_report.json':old.setdefault('subsequent_photo_counts',{}).update(counts)
    if name=='ubs_build_report.json':old['final_photo_counts'].update({n:v for n,v in counts.items() if n in old['final_photo_counts']})
    if name=='nearfront_build_report.json':
        for row in old['photo_cuts']:
            if row['object'] in changed:row['new_faces']=counts[row['object']]
    write_path(f'evidence/{version}/{name}').write_text(json.dumps(old,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
receipt={k:checkpoint[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version,native=str(target),native_sha256=sha(target),native_bytes=target.stat().st_size,
               objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,runtime_exported=False,natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BANK_SHELTER_SAVED',json.dumps({k:receipt[k] for k in ['native','native_sha256','native_bytes','objects']}),flush=True)
