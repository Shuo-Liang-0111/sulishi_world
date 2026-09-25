"""Repair027r5 ground loss, balcony junction and shallow glazed visual interiors.

Only the new Sternen collection and explicitly bounded photo remnants change.
Interior finishes follow the viewed PSP photographs; the unsurveyed layout is
design inference, remains closed, and is not a natural-use acceptance claim.
"""
from pathlib import Path
import ast, hashlib, importlib, json, math, shutil, sys
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
importlib.invalidate_caches()
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state
from blender_photo_clip import cut_object, subtract_box, area

s = bpy.context.scene
assert s['version'] == 'G1_027r5'
version = 'G1_027r6'
target = write_path('native/G1_027r6_sternen_connected_frontages.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
cp = json.loads(read_path('evidence/G1_027r5/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == cp['native_sha256']
d = json.loads(read_path('derived/sternen_grill/build_input.json').read_text())
previous = json.loads(read_path('evidence/G1_027r5/build_report.json').read_text())
C = bpy.data.collections['45_STERNEN_GRILL_FRONTAGES']
original_names = {o.name for o in C.objects}
before = {o.name: object_state(o) for o in s.objects if o.name not in original_names}
source = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
source_ids = {o.name: o.data.as_pointer() for o in source.objects}
A = np.array(d['A']); U = np.array(d['U']); N = np.array(d['N'])
W = d['width']; D = d['depth']; floor = d['floor_z']; zf = d['balcony_floor_z']; zu = d['upper_start_z']
groups = {}
# Reuse only pure authoring helpers, never import the old executable builder.
builder = read_path('tools/blender_build_sternen_grill.py')
helper_names = {'P', 'Q', 'side', 'add', 'box', 'tube', 'mat'}
tree = ast.parse(builder.read_text(encoding='utf-8'))
helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in helper_names]
assert {n.name for n in helpers} == helper_names
exec(compile(ast.Module(body=helpers, type_ignores=[]), 'sternen_geometry_helpers', 'exec'))

stone = bpy.data.materials['SG | pale fine-grained limestone 3']
metal = bpy.data.materials['SG | dark bronze aluminium frames']
floor_mat = bpy.data.materials['SG | grey threshold stone']
soffit = bpy.data.materials['SG | balcony mineral soffit']
glass = bpy.data.materials['SG | clear double glazing']
bs = next(n for n in glass.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bs.inputs['Roughness'].default_value = .022
bs.inputs['Base Color'].default_value = (.965, .985, .985, 1)
bs.inputs['IOR'].default_value = 1.5
glass['revision_basis'] = 'Clear architectural glazing; prior0.11 roughness visibly frosted the view. Optical values are inferred.'
plaster = mat('r6 shaded mineral plaster', (.26, .25, .23), .9)
tile = mat('r6 bottle green glazed tile', (.028, .078, .046), .22, micro=.00006)
grout = mat('r6 dark tile grout', (.025, .03, .026), .93)
steel = mat('r6 brushed counter steel', (.42, .45, .46), .28, .88, .00004)
timber = mat('r6 oiled beech', (.30, .14, .045), .42, micro=.00010)
blackboard = mat('r6 dark menu panel', (.012, .017, .015), .82)
opal = mat('r6 opal pendant glass', (.72, .67, .53), .35, micro=0)
bs = next(n for n in opal.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bs.inputs['Emission Color'].default_value = (.96, .80, .50, 1)
bs.inputs['Emission Strength'].default_value = 2.2

def prism(name, ring, low, high, material, bevel=.003):
    n = len(ring)
    pts = [P(u,v,z) for z in (low,high) for u,v in ring]
    faces = [tuple(range(n-1,-1,-1)), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    add(name,pts,faces,material,bevel)

def corner_band(inner, outer, left=0.):
    return [(left,inner),(W+inner,inner),(W+inner,-D),(W+outer,-D),(W+outer,outer),(left,outer)]

def sphere(name, center, radius, material):
    pts=[]; faces=[]; segments=20; rings=12
    for j in range(rings+1):
        theta=math.pi*j/rings
        for i in range(segments):
            phi=math.tau*i/segments
            pts.append(P(center[0]+radius*math.sin(theta)*math.cos(phi),
                         center[1]+radius*math.sin(theta)*math.sin(phi),center[2]+radius*math.cos(theta)))
    for j in range(rings):
        for i in range(segments):
            faces.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
    add(name,pts,faces,material,smooth=True)

def round_table(name, u, v, base, height=.76, radius=.38):
    ring=[(u+radius*math.cos(a),v+radius*math.sin(a)) for a in np.arange(32)*math.tau/32]
    prism(name+'_TOP',ring,base+height-.035,base+height,timber,.005)
    tube(name+'_COLUMN',[P(u,v,base+.05),P(u,v,base+height-.035)],.035,metal,14)
    r=.28
    prism(name+'_FOOT',[(u+r*math.cos(a),v+r*math.sin(a)) for a in np.arange(24)*math.tau/24],base+.003,base+.035,metal,.005)

def stool(name,u,v,base,height=.47):
    r=.18
    prism(name+'_SEAT',[(u+r*math.cos(a),v+r*math.sin(a)) for a in np.arange(24)*math.tau/24],base+height-.028,base+height,timber,.004)
    for a in np.arange(3)*math.tau/3:
        tube(name+'_LEG',[P(u+.17*math.cos(a),v+.17*math.sin(a),base+.006),
                          P(u+.10*math.cos(a),v+.10*math.sin(a),base+height-.03)],.021,timber,10)

remove = []
for ob in C.objects:
    name=ob.name
    if name.endswith('_ROOM') or any(part in name for part in [
        '_BALCONY_FLOOR','_BALCONY_FASCIA','_BALCONY_CAP','_BALCONY_RAIL',
        '_RESTAURANT_GLAZING','_RESTAURANT_MULLION','_RESTAURANT_RAIL','_RESTAURANT_BACK',
        '_SHOP_BACK','_SHOP_FLOOR','_SHOP_CEILING','_SHOP_RETURN','_SOFFIT']):
        remove.append(name)
for name in remove: bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)

# A continuous L-shaped slab/fascia/coping joins the two real street frontages.
prism('SG_R6_BALCONY_SLAB',corner_band(-.645,.81,-.035),zf-.22,zf,floor_mat,.005)
prism('SG_R6_BALCONY_FASCIA',corner_band(.33,.81),zf-.63,zf+.01,stone,.003)
prism('SG_R6_BALCONY_COPING',corner_band(.28,.84),zf+.01,zf+.065,stone,.004)
for z,r in [(zf+.15,.012),(zf+.54,.014),(zf+.91,.023)]:
    pts=[P(0,.66,z),P(W+.56,.66,z)]
    pts += [P(W+.56+.10*math.cos(a),.56+.10*math.sin(a),z) for a in np.linspace(math.pi/2,0,7)]
    pts += [P(W+.66,-D,z)]
    tube('SG_R6_BALCONY_CONTINUOUS_RAIL',pts,r,metal,12)
tube('SG_R6_BALCONY_CORNER_POST',[P(W+.62,.62,zf+.065),P(W+.62,.62,zf+.915)],.017,metal,10)
# Soffit returns are continuous at the convex corner as well.
prism('SG_R6_RESTAURANT_CEILING',corner_band(-4.6,.255),zu-.18,zu,soffit,.002)

# Glazing meets at a real corner mullion, without overlapping pale room returns.
for label,start,end,frame in [('FRONT',0.,W-.93,P),('LANE',.93,D,side)]:
    for i in range(5):
        a=start+(end-start)*i/5; b=start+(end-start)*(i+1)/5
        box('SG_R6_'+label+'_RESTAURANT_GLAZING',((a+b)/2,-.93,(zf+zu)/2),(b-a-.065,.018,zu-zf-.32),glass,0,frame)
    for u in np.linspace(start,end,6):
        box('SG_R6_'+label+'_RESTAURANT_MULLION',(u,-.93,(zf+zu)/2),(.065,.09,zu-zf-.11),metal,.002,frame)
    for z in [zf+.11,zu-.15]:
        box('SG_R6_'+label+'_RESTAURANT_RAIL',((start+end)/2,-.93,z),(end-start,.09,.065),metal,.002,frame)

# Photograph-guided visual interior bands. The rear building is not represented
# as a surveyed plan, nor opened or declared accessible in this construction.
for label,base,height,offset in [('GROUND',floor,zf-.67-floor,-.70),('RESTAURANT',zf,zu-zf-.18,-.94)]:
    prism('SG_R6_'+label+'_FLOOR',corner_band(-4.58,offset),base-.10,base,floor_mat,.001)
    prism('SG_R6_'+label+'_CEILING',corner_band(-4.58,offset),base+height,base+height+.09,soffit,.001)
    box('SG_R6_'+label+'_BACK',( (W-4.58)/2,-4.58,base+height/2),(W-4.58,.12,height),plaster,.002)
    box('SG_R6_'+label+'_LANE_BACK',(W-4.58,(-D-4.58)/2,base+height/2),(.12,D-4.58,height),plaster,.002)
    box('SG_R6_'+label+'_LEFT',(0,(-4.58+offset)/2,base+height/2),(.09,4.58+offset,height),plaster,.001)
    box('SG_R6_'+label+'_LANE_END',(W-(4.58-offset)/2,-D,base+height/2),(4.58+offset,.09,height),plaster,.001)
# BeautySpace is a different tenancy; maintain a partition, rather than extend
# the restaurant visibly through every ground-floor opening.
box('SG_R6_TENANCY_PARTITION',(W/4,-2.66,floor+1.23),(.10,3.82,2.46),plaster,.002)

for side_name,centers,frame in [('FRONT',d['front_centers'],P),('LANE',d['side_centers'],side)]:
    for li,L in enumerate(d['levels']):
        for wi,u in enumerate(centers):
            # Recesses are physically deeper while staying within the footprint.
            # Corner bays meet a perpendicular wall, so stop at2.3m there.
            depth=2.3 if (side_name=='FRONT' and wi==3) or (side_name=='LANE' and wi==0) else 3.6
            w=d['window_width']; low=L['bottom']+.04; high=L['top']-.14
            prefix=f'SG_R6_{side_name}_OFFICE_{li}_{wi}'
            box(prefix+'_BACK',(u,-depth,(low+high)/2),(w+.2,.10,high-low),plaster,.001,frame)
            for x in [u-w/2-.03,u+w/2+.03]:
                box(prefix+'_SIDE',(x,-(depth+.35)/2,(low+high)/2),(.06,depth-.35,high-low),plaster,.001,frame)
            for z in [low,high]:
                box(prefix+'_SLAB',(u,-(depth+.35)/2,z),(w+.12,depth-.35,.07),soffit,.001,frame)

# Actual photographed material families: steel counter/hood, green ceramic
# backing, wood tables/stools, opal lamps. Arrangement below is inferred.
box('SG_R6_COUNTER_BASE',(6.60,-3.27,floor+.49),(5.8,.74,.96),steel,.008)
box('SG_R6_COUNTER_TOP',(6.60,-3.27,floor+1.005),(5.92,.84,.055),steel,.006)
box('SG_R6_COUNTER_PLINTH',(6.60,-3.27,floor+.065),(5.55,.61,.13),metal,.004)
for x in [4.25,5.42,6.59,7.76,8.93]:
    box('SG_R6_COUNTER_DRAWER',(x,-2.89,floor+.62),(1.125,.019,.51),steel,.005)
    tube('SG_R6_COUNTER_HANDLE',[P(x-.20,-2.85,floor+.78),P(x+.20,-2.85,floor+.78)],.010,metal,10)
box('SG_R6_COUNTER_SCREEN',(6.60,-3.07,floor+1.31),(5.65,.012,.55),glass,0)
for x in [3.80,5.66,7.52,9.40]:
    tube('SG_R6_COUNTER_SCREEN_POST',[P(x,-3.07,floor+1.03),P(x,-3.07,floor+1.59)],.012,steel,10)
box('SG_R6_TILE_BACKING',(6.35,-4.48,floor+1.33),(5.85,.08,2.55),grout,.001)
for j in range(15):
    for i in range(22):
        x=3.55+i*.259+(.13 if j%2 else 0)
        if x>9.12:continue
        box('SG_R6_GLAZED_TILES',(x,-4.425,floor+.095+j*.163),(.255,.032,.158),tile,.002)
box('SG_R6_EXTRACT_HOOD',(6.55,-3.64,floor+2.14),(5.65,1.27,.38),steel,.007)
box('SG_R6_MENU_HEADER',(6.55,-2.93,floor+2.05),(5.5,.045,.47),blackboard,.004)
for x in np.arange(4.1,9.12,.075):
    box('SG_R6_HOOD_FILTER',(x,-3.61,floor+1.935),(.042,.75,.025),metal,.001)
for i,u in enumerate([4.9,10.8]):
    round_table('SG_R6_GROUND_TABLE_'+str(i),u,-1.68,floor,1.00,.34)
    for j,dx in enumerate([-.46,.46]):stool(f'SG_R6_GROUND_STOOL_{i}_{j}',u+dx,-2.10,floor,.67)
for i,(u,v) in enumerate([(2.0,-2.15),(4.7,-2.15),(7.4,-2.15),(10.5,-2.15),
                           (W-2.1,-5.4),(W-2.1,-8.5),(W-2.1,-11.6),(W-2.1,-14.5)]):
    round_table('SG_R6_RESTAURANT_TABLE_'+str(i),u,v,zf)
    for j,dx in enumerate([-.49,.49]):stool(f'SG_R6_RESTAURANT_STOOL_{i}_{j}',u+dx,v,zf)

lamp_positions=[]
for level,base,ceiling_z,positions in [
    ('GROUND',floor,11.11,[(4.6,-1.9),(7.0,-1.9),(9.4,-1.9)]),
    ('RESTAURANT',zf,zu-.20,[(2.0,-2.15),(5.0,-2.15),(8.0,-2.15),(W-2.1,-5.4),(W-2.1,-9.5)])]:
    for i,(u,v) in enumerate(positions):
        center_z=ceiling_z-.35
        tube('SG_R6_'+level+'_PENDANT_ROD',[P(u,v,center_z+.14),P(u,v,ceiling_z)],.008,metal,8)
        sphere('SG_R6_'+level+'_OPAL_GLOBE', (u,v,center_z),.14,opal)
        lamp_positions.append((level,i,u,v,center_z-.19))

# The outer boundary has useful survey heights, but the scan immediately next
# to shopfronts contains holes/bumps. Retain that outer boundary and interpolate
# to the authored threshold; do not blindly reintroduce the defective surface.
context=json.loads(read_path('derived/sternen_grill/context_probe.json').read_text())
ground_triangles=[];edge_u=set(np.linspace(-.045,W+.10,60).tolist())
for row in context['rows']:
    vertices=np.array(row['vertices']);valid=[]
    for fi,face in enumerate(row['faces']):
        raw=vertices[face]; n=np.cross(raw[1]-raw[0],raw[2]-raw[0]); length=np.linalg.norm(n)
        if length<1e-8 or abs(n[2])/length<.87 or raw[:,2].min()<8.3 or raw[:,2].max()>8.8:continue
        valid.append(face)
        local=[Q(p) for p in raw]
        ground_triangles.append((row['name'],np.array(local)))
        for a,b in zip(local,local[1:]+local[:1]):
            if (a[1]-1.65)*(b[1]-1.65)<0:
                x=float(a[0]+(b[0]-a[0])*(1.65-a[1])/(b[1]-a[1]))
                if -.045<x<W+.10:edge_u.add(x)
ground_source=[];verts=[];faces=[];row_v=[.345,.55,.9,1.25,1.65]
for u in sorted(edge_u):
    hits=[]
    # Float64 barycentrics include shared source-triangle edges. Float32 BVH
    # rays can fall between the two neighbors exactly at these seam vertices.
    for name,t in ground_triangles:
        matrix=np.column_stack((t[1,:2]-t[0,:2],t[2,:2]-t[0,:2]))
        if abs(np.linalg.det(matrix))<1e-12:continue
        a,b=np.linalg.solve(matrix,np.array([u,1.65])-t[0,:2])
        if a>=-1e-8 and b>=-1e-8 and a+b<=1+1e-8:
            hits.append((float(t[0,2]+a*(t[1,2]-t[0,2])+b*(t[2,2]-t[0,2])),name))
    assert hits,('missing source boundary',u)
    z,name=max(hits);ground_source.append(dict(u=u,v=1.65,height=z,source=name))
    for v in row_v:
        t=(v-.345)/(1.65-.345);height=(floor+.01)*(1-t)+z*t
        verts.append(P(u,v,height))
for i in range(len(edge_u)-1):
    for j in range(len(row_v)-1):
        a=i*len(row_v)+j;b=a+len(row_v)
        # P uses a clockwise plan frame: reverse the face for an upward normal.
        faces.extend([(a,b+1,b),(a,a+1,b+1)])
add('SG_R6_RESTORED_STREET_GROUND',verts,faces,bpy.data.materials['asphalt_03'])

# Finish and validate the new editable geometry before changing photo context.
created=[]
for (name,_),g in groups.items():
    assert name not in bpy.data.objects,name
    me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    assert not me.validate(clean_customdata=False),name
    ob=bpy.data.objects.new(name,me);C.objects.link(ob);me.materials.append(g['mat'])
    for p in me.polygons:p.use_smooth=g['smooth']
    uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axes=[i for i in range(3) if i!=int(np.argmax(abs(np.array(face.normal))))]
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/3,p[axes[1]]/3)
    if g['bevel']:
        kinds={i.identifier for i in ob.modifiers.bl_rna.functions['new'].parameters['type'].enum_items}
        assert {'BEVEL','WEIGHTED_NORMAL'}.issubset(kinds)
        mod=ob.modifiers.new('physical edge','BEVEL');mod.width=g['bevel'];mod.segments=2
        ob.modifiers.new('construction normals','WEIGHTED_NORMAL')
    ob['provenance']='Photograph-guided fabrication / inferred visual interior; street outer boundary heights retained, threshold transition inferred.'
    created.append(name)
for level,i,u,v,z in lamp_positions:
    # Small real downward luminaires, independent of camera/exposure.
    assert 'AREA' in {item.identifier for item in bpy.types.Light.bl_rna.properties['type'].enum_items}
    data=bpy.data.lights.new(f'SG_R6_{level}_LIGHT_{i}',type='AREA')
    data.energy=12 if level=='GROUND' else 18; data.color=(1.0,.82,.57); data.size=.22
    ob=bpy.data.objects.new(data.name,data);C.objects.link(ob);ob.location=P(u,v,z)
    created.append(ob.name)

# Keep existing architectural lettering but lower it into the visible fascia
# above its shop glazing, where the photographic sign is actually located.
sign=bpy.data.objects['SG_RESTAURANT_LETTERING']
sign.location.z-=.38

# Only deepen within the measured building and clear the witnessed corner sliver.
extra_boxes=[[-.04,W+.10,-4.68,-1.80,8.60,25.15],
             [W-4.68,W-1.80,-16.03,.10,8.60,25.15],
             [W+1.0,W+1.32,-.12,.20,10.39,11.46]]
cuts=[]
for row in context['rows']:
    ob=bpy.data.objects[row['name']]
    result=cut_object(ob,Q,extra_boxes)
    if result:cuts.append(result)
fragment=json.loads(read_path('derived/sternen_grill/remaining_bridge_fragment.json').read_text())
ob=bpy.data.objects[fragment['object']]
assert json.loads(json.dumps(mesh_digest(ob.data)))==fragment['mesh_digest']
component=next(c for c in fragment['components'] if c['component']==1)
assert component['faces']==12 and set([10,169]).issubset(component['face_ids'])
assert component['min']==[-277.771,119.223,11.61] and component['max']==[-276.618,119.817,12.689]
result=cut_object(ob,lambda p:p,[],component['face_ids']);assert result;cuts.append(result)

assert source_ids=={o.name:o.data.as_pointer() for o in source.objects}
changed={r['object'] for r in cuts}
assert not [name for name,state in before.items() if name not in changed and object_state(bpy.data.objects[name])!=state]
bpy.context.view_layer.update()
# Recheck the previously missing32 locations with actual world geometry.
probe=json.loads(read_path('evidence/G1_027r5/followup_probe.json').read_text())
deps=bpy.context.evaluated_depsgraph_get();ground_checks=[]
for r in probe['ground']:
    hit,p,n,face,ob,m=s.ray_cast(deps,Vector((*r['xy'],9.3)),Vector((0,0,-1)),distance=2)
    assert hit and p.z<8.82,(r['u'],r['v'])
    ground_checks.append(dict(u=r['u'],v=r['v'],point=list(p),normal=list(n),object=ob.name))

# Add an ordinary downward glance, without changing any prior review camera.
eye=P(W*.52,6.5,10.2);hit,p,n,face,ob,m=s.ray_cast(deps,Vector((*eye[:2],9.3)),Vector((0,0,-1)),distance=2)
assert hit and n.z>.5
eye[2]=p.z+1.7;look=P(W*.52,-.2,8.96)
cam=bpy.data.cameras.new('SG_QA_THRESHOLD');cam.lens=28;cam.clip_end=1600
camera=bpy.data.objects.new(cam.name,cam);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(camera)
camera.location=eye;camera.rotation_euler=(Vector(look)-camera.location).to_track_quat('-Z','Y').to_euler()
camera_rows=previous['cameras']+[dict(name=camera.name,eye=eye.tolist(),look=look.tolist(),lens=28,floor=ob.name,eye_height_m=1.7)]

s['version']=version;s['latest_construction']='Sternen ground recovery, continuous balcony joint, clear glazing and photograph-guided interior depth'
s.camera=bpy.data.objects['SG_QA_CORNER']
merged={r['object']:r for r in previous['photo_cuts']};merged.update({r['object']:r for r in cuts})
missing=[bpy.path.abspath(im.filepath,library=im.library) for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath,library=im.library)).is_file()]
assert not missing
report=dict(version=version,base_native=cp['native'],base_native_sha256=cp['native_sha256'],
    created_objects=sorted(o.name for o in C.objects),added_objects=created,removed_objects=remove,
    photo_cuts=list(merged.values()),incremental_photo_cuts=cuts,extra_photo_cut_boxes=extra_boxes,
    old_cameras_unchanged=True,cameras=camera_rows,original_source_meshes_unchanged=2039,
    ground_boundary_samples=ground_source,restored_ground_checks=ground_checks,
    ground_transition_basis='Outer edge recovered from pre-cut source triangles; interior of lost strip interpolated to8.580m threshold, replacing scan defects. Not an engineering survey.',
    unrelated_objects_unchanged=len(before)-len(changed),missing_images=missing,
    helper_source_sha256=hashlib.sha256(builder.read_bytes()).hexdigest(),
    limits=['Unsurveyed interior arrangement is inference','Doors are closed; not a complete accessible interior',
            'Neighboring buildings, street photo cars and wider district remain unfinished','No runtime export or natural-use acceptance'])
write_path(f'evidence/{version}/build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
receipt={k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(dict(version=version,native=str(target),native_sha256=digest,native_bytes=target.stat().st_size,
    objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,runtime_exported=False,natural_use_verified=False))
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STERNEN_REPAIR_SAVED',json.dumps({k:receipt[k] for k in ['version','native','native_sha256','native_bytes','objects']}),flush=True)
