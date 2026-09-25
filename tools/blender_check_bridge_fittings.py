"""Fresh-native checks for physical connections and exact retained photo data."""
from pathlib import Path
import hashlib,json,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

s=bpy.context.scene;assert s['version']=='G1_027r4'
spec_path=read_path('derived/bridge_fittings/build_input.json');spec=json.loads(spec_path.read_text())
built=json.loads(read_path('evidence/G1_027r4/construction.json').read_text())
assert hashlib.sha256(spec_path.read_bytes()).hexdigest()==built['input_sha256']
assert hashlib.sha256(read_path('derived/bridge_fittings/source_probe.json').read_bytes()).hexdigest()==spec['source_probe_sha256']
probe=json.loads(read_path('derived/bridge_fittings/source_probe.json').read_text())
photos={o['name']:o for o in probe['context']}
C=bpy.data.collections['44_BRIDGE_FITTINGS']
assert set(built['geometry'])=={o.name for o in C.objects}
for name,digest in built['geometry'].items():
    ob=bpy.data.objects[name]
    assert json.loads(json.dumps(mesh_digest(ob.data)))==digest,name
    assert all(p.area>1e-10 for p in ob.data.polygons),name
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
kept_faces=0
for row in spec['photo_removals']:
    ob=bpy.data.objects[row['object']];data=ob.data;ref=photos[ob.name]
    keep=[i for i in range(len(ref['faces'])) if i not in row['face_ids']]
    assert [list(p.vertices) for p in data.polygons]==[ref['faces'][i] for i in keep]
    assert np.array_equal(np.array([list(ob.matrix_world@v.co) for v in data.vertices]),ref['vertices'])
    actual=np.array([list(data.uv_layers.active.data[i].uv) for p in data.polygons for i in p.loop_indices])
    expected=np.array([uv for i in keep for uv in ref['uv_faces'][i]])
    assert np.array_equal(actual,expected),ob.name
    kept_faces+=len(keep)
lamp_checks=[]
for spec_lamp,lamp in zip(spec['lamps'],built['lamps']):
    assert lamp['id']==spec_lamp['id']
    mast=bpy.data.objects['BD_MAST_'+spec_lamp['mast']['id'].split('.')[-1]]
    p=np.array([list(mast.matrix_world@v.co) for v in mast.data.vertices])
    xy=(p[:,:2].max(0)+p[:,:2].min(0))/2
    assert np.linalg.norm(xy-np.array(lamp['mount_xy']))<.0001
    assert 4.0<lamp['height_above_mast_foot']<5.2
    housing=bpy.data.objects['BF_L'+lamp['id']+'_HOUSING']
    v=np.array([list(housing.matrix_world@q.co) for q in housing.data.vertices])
    assert v[:,2].min()-p[:,2].min()>4.0
    assert all(bpy.data.objects[name]['mount_mast']==spec_lamp['mast']['id'] for name in lamp['objects'])
    lamp_checks.append(dict(id=lamp['id'],source_mast_xy_retained=True,body_clearance_m=float(v[:,2].min()-p[:,2].min())))
flag_checks=[]
for flag in built['flags']:
    pole=bpy.data.objects['BF_'+flag['id']+'_POLE'];cloth=bpy.data.objects[flag['cloth']]
    ground=bpy.data.objects[flag['ground_object']]
    tree=BVHTree.FromPolygons([ground.matrix_world@v.co for v in ground.data.vertices],[list(p.vertices) for p in ground.data.polygons])
    hit,normal,face,distance=tree.ray_cast(Vector((*flag['xy'],15)),Vector((0,0,-1)),8)
    assert hit is not None and abs(hit.z-flag['ground_z'])<1e-4
    pv=np.array([list(pole.matrix_world@v.co) for v in pole.data.vertices]);cv=np.array([list(cloth.matrix_world@v.co) for v in cloth.data.vertices])
    assert pv[:,2].min()<hit.z and pv[:,2].max()>cv[:,2].max()
    assert list(cloth['rest_cloth_size_m'])==[4.,4.]
    assert cv[:,2].min()-hit.z>10
    # Hoist edge remains attached along the mast, rather than floating cloth.
    left=cv[np.arange(0,len(cv),65)]
    assert np.allclose(np.linalg.norm(left[:,:2]-np.array(flag['xy']),axis=1),.12,atol=4e-5)
    flag_checks.append(dict(id=flag['id'],ground_object=ground.name,foot_embedded_m=float(hit.z-pv[:,2].min()),
        lowest_cloth_clearance_m=float(cv[:,2].min()-hit.z),position_is_inferred=True))
camera_checks=[]
for name in ['BF_QA_LAMP','BF_QA_FLAGS']:
    camera=bpy.data.objects[name];floor=bpy.data.objects[camera['floor_source']]
    tree=BVHTree.FromPolygons([floor.matrix_world@v.co for v in floor.data.vertices],[list(p.vertices) for p in floor.data.polygons])
    hit,normal,face,distance=tree.ray_cast(camera.location,Vector((0,0,-1)),3)
    assert hit is not None and abs(distance-1.7)<1e-4,(name,distance)
    camera_checks.append(dict(name=name,floor=floor.name,eye_height_m=distance))
report=dict(version=s['version'],lamps=lamp_checks,flags=flag_checks,cameras=camera_checks,fixture_meshes=len(C.objects),
    photo_faces_removed=sum(len(r['face_ids']) for r in spec['photo_removals']),photo_faces_retained_exactly=kept_faces,
    original_reference_objects=2039,unresolved_extra_ewz_fixture=37745,
    checks='Mesh fingerprints, retained source coordinates/UVs, source mast alignment, fixture clearance, pole ground contact and cloth attachment.',
    runtime_collision_verified=False,natural_use_verified=False,visual_acceptance=False)
write_path('evidence/G1_027r4/fittings_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BRIDGE_FITTINGS_VERIFIED',json.dumps({k:v for k,v in report.items() if k not in ['lamps','flags']}),flush=True)
