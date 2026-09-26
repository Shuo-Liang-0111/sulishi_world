"""Fresh-native architectural and retained-context checks; no visual-use claim."""
from pathlib import Path
import hashlib,json,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest
from blender_photo_clip import subtract_box,area

s=bpy.context.scene;assert s['version'] in ['G1_027r5','G1_027r6','G1_027r7','G1_027r8','G1_027r9','G1_027r10','G1_027r11']
version=s['version']
d=json.loads(read_path('derived/sternen_grill/build_input.json').read_text())
r=json.loads(read_path(f'evidence/{version}/build_report.json').read_text())
cp=json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==cp['native_sha256']
C=bpy.data.collections['45_STERNEN_GRILL_FRONTAGES']
assert set(r['created_objects'])=={o.name for o in C.objects}
assert all(o.type in {'MESH','LIGHT','EMPTY'} for o in C.objects)
assert all(len(o.data.polygons) and np.isfinite([v.co[:] for v in o.data.vertices]).all() for o in C.objects if o.type=='MESH')
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
A=np.array(d['A']);U=np.array(d['U']);N=np.array(d['N']);W=d['width']
def Q(p):return np.array([(p[:2]-A)@U,(p[:2]-A)@N,p[2]])
def P(u,v,z):return Vector((*list(A+U*u+N*v),z))

# Recheck actual remaining triangles, rather than merely trusting removal counts.
boxes=d['photo_cut_boxes']+[d['roof_cut_box']]+r.get('extra_photo_cut_boxes',[]);max_overlap=0.;max_inset_overlap=0.;photo_faces=0
for row in r['photo_cuts']:
    ob=bpy.data.objects[row['object']]
    expected=r.get('subsequent_photo_counts',{}).get(row['object'],row['new_faces'])
    assert len(ob.data.polygons)==expected
    if row['object'] in {'CTX_I3S_34256','CTX_I3S_34216','CTX_I3S_34267'}:continue
    for f in ob.data.polygons:
        poly=[Q(np.array(ob.matrix_world@ob.data.vertices[i].co)) for i in f.vertices]
        for box in boxes:
            outside,inside=subtract_box(poly,box)
            overlap=area(inside);max_overlap=max(max_overlap,overlap)
            # Float32 mesh storage at ~250m local coordinates has ~15um spacing.
            # Test the volume inset by 0.1mm; record raw boundary sliver area too.
            inset=[v+(.0001 if i%2==0 else -.0001) for i,v in enumerate(box)]
            _,strict_inside=subtract_box(poly,inset)
            strict_area=area(strict_inside);max_inset_overlap=max(max_inset_overlap,strict_area)
            assert strict_area<1e-8,(ob.name,f.index,overlap,strict_area)
        photo_faces+=1

# 24 upper openings must have recessed transparent glass, not an opaque wall.
openings=[]
for side_name,centers in [('FRONT',d['front_centers']),('LANE',d['side_centers'])]:
    for li,level in enumerate(d['levels']):
        for wi,u in enumerate(centers):
            ob=bpy.data.objects[f'SG_{side_name}_LEVEL{li+2}_W{wi}_GLASS']
            p=np.array([Q(np.array(ob.matrix_world@v.co)) for v in ob.data.vertices])
            depth=p[:,1] if side_name=='FRONT' else p[:,0]-W
            assert np.allclose([depth.min(),depth.max()],[-.381,-.365],atol=.00003)
            m=ob.data.materials[0];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            assert bs.inputs['Transmission Weight'].default_value==1
            openings.append(ob.name)

# Prior lamps/flags are numerically identical; photograph replacement evolves.
fittings=json.loads(read_path('evidence/G1_027r4/construction.json').read_text())
for name,digest in fittings['geometry'].items():
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[name].data)))==digest,name

# All residual test pixels now pass the former hanging sheets.
probe=json.loads(read_path('derived/bridge_residuals/source_probe.json').read_text())
deps=bpy.context.evaluated_depsgraph_get();camera=bpy.data.objects['BF_QA_FLAGS'];frame=camera.data.view_frame(scene=s)
x0,x1=min(p.x for p in frame),max(p.x for p in frame);y0,y1=min(p.y for p in frame),max(p.y for p in frame)
pixel_results=[]
for sample in probe['samples']:
    x,y=sample['pixel'];q=Vector((x0+(x+.5)/1280*(x1-x0),y1-(y+.5)/840*(y1-y0),frame[0].z))
    direction=(camera.matrix_world.to_3x3()@q).normalized()
    hit,p,n,face,ob,m=s.ray_cast(deps,camera.matrix_world.translation,direction,distance=220)
    assert not hit or (p-Vector(sample['point'])).length>.05
    pixel_results.append(dict(pixel=[x,y],now_hit=ob.name if hit else None,point=list(p) if hit else None))

camera_rows=[]
for row in r['cameras']:
    camera=bpy.data.objects[row['name']];floor=bpy.data.objects[row['floor']]
    tree=BVHTree.FromPolygons([floor.matrix_world@v.co for v in floor.data.vertices],[list(p.vertices) for p in floor.data.polygons])
    p,n,face,distance=tree.ray_cast(camera.location,Vector((0,0,-1)),4)
    assert p is not None and abs(distance-1.7)<.0001,(camera.name,distance)
    camera_rows.append(dict(name=camera.name,ground=floor.name,eye_height_m=distance))
repairs={}
if version in ['G1_027r6','G1_027r7','G1_027r8','G1_027r9','G1_027r10','G1_027r11']:
    ground=[]
    # Fresh evaluation of every old missing-ground location, not saved reports.
    samples=json.loads(read_path('evidence/G1_027r5/followup_probe.json').read_text())['ground']
    for sample in samples:
        hit,p,n,face,ob,m=s.ray_cast(deps,Vector((*sample['xy'],9.3)),Vector((0,0,-1)),distance=2)
        assert hit and 8.48<p.z<8.80 and n.z>.75,(sample,ob.name if hit else None)
        ground.append(dict(u=sample['u'],v=sample['v'],z=p.z,normal_z=n.z,object=ob.name))
    slab=bpy.data.objects['SG_R6_BALCONY_SLAB']
    tree=BVHTree.FromObject(slab,deps);corner=[]
    for u,v in [(W+.1,.1),(W+.45,.1),(W+.1,.45),(W+.45,.45)]:
        p,n,face,distance=tree.ray_cast(P(u,v,d['balcony_floor_z']+.5),Vector((0,0,-1)),1)
        assert p is not None and abs(p.z-d['balcony_floor_z'])<.0001 and n.z>.99
        corner.append(list(p))
    corner_pixel=json.loads(read_path('evidence/G1_027r5/followup_probe.json').read_text())['pixels'][4]
    assert corner_pixel['camera']=='SG_QA_CORNER' and corner_pixel['pixel']==[636,680]
    cam=bpy.data.objects['SG_QA_CORNER'];direction=(Vector(corner_pixel['point'])-cam.location).normalized()
    hit,p,n,face,ob,m=s.ray_cast(deps,cam.location,direction,distance=100)
    assert not hit or (p-Vector(corner_pixel['point'])).length>.05
    repairs=dict(ground_samples=ground,balcony_corner_supported=corner,former_corner_spike_new_hit=ob.name if hit else None,
        glass_roughness=next(n for n in bpy.data.materials['SG | clear double glazing'].node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value)
if version in ['G1_027r7','G1_027r8','G1_027r9','G1_027r10','G1_027r11']:
    sign=bpy.data.objects['SG_RESTAURANT_LETTERING']
    vertices=np.array([Q(np.array(sign.matrix_world@v.co)) for v in sign.data.vertices])
    # Check against the third opening's physical pier limits, not only the
    # target center stored by the builder.
    assert vertices[:,0].min()>W/2+.30 and vertices[:,0].max()<W*3/4-.30
    assert 10.8<vertices[:,2].min()<vertices[:,2].max()<11.10
    assert not any(o.type=='LIGHT' for o in C.objects)
    emitters=[]
    for level in ['GROUND','RESTAURANT']:
        ob=bpy.data.objects['SG_R6_'+level+'_OPAL_GLOBE']
        bs=next(n for n in ob.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        strength=bs.inputs['Emission Strength'].default_value
        assert 10<strength<35
        assert ob.visible_camera and ob.visible_glossy and ob.visible_transmission
        emitters.append(dict(object=ob.name,emission_strength=strength))
    approach=bpy.data.objects['SG_R7_CONTINUOUS_STREET_APPROACH']
    tree=BVHTree.FromObject(approach,deps);walk_contacts=[];outer_obstructions=[]
    # Fresh independent samples on both sides of the formerly open corner.
    for offset in [.46,.78,1.22,1.6,2.0]:
        for v in [-15.6,-10.2,-5.1,-1.0,-.15,.08,.31,.52,.94,1.47,2.25,3.9]:
            u=W+offset
            point,normal,_,_=tree.ray_cast(P(u,v,9.15),Vector((0,0,-1)),1.3)
            assert point is not None and 8.35<point.z<8.8 and normal.z>.98,(u,v)
            hit,p,n,face,ob,m=s.ray_cast(deps,P(u,v,9.15),Vector((0,0,-1)),distance=1.3)
            assert hit
            row=dict(u=u,v=v,support_z=point.z,top_z=p.z,object=ob.name)
            if abs(p.z-point.z)>.02 or n.z<.98:
                assert offset>1.5,('inner approach remains obstructed',row)
                outer_obstructions.append(row)
            else:walk_contacts.append(row)
    assert len(walk_contacts)>=40
    local_mat=approach.data.materials[0]
    assert local_mat.name=='SG | r7 neutral street asphalt'
    assert local_mat!=bpy.data.materials['asphalt_03']
    assert any(n.type=='HUE_SAT' and abs(n.inputs['Saturation'].default_value-.06)<1e-6 for n in local_mat.node_tree.nodes)
    repairs['r7']=dict(sign_bounds=[vertices.min(0).tolist(),vertices.max(0).tolist()],
        physical_emitters=emitters,inner_approach_contacts=walk_contacts,
        retained_outer_scan_obstructions=outer_obstructions,whole_lane_clear=False,
        runtime_collision_checked=False)
report=dict(version=s['version'],new_meshes=sum(o.type=='MESH' for o in C.objects),upper_recessed_glazed_openings=len(openings),
    retained_photo_faces_checked=photo_faces,max_raw_boundary_sliver_m2=max_overlap,
    floating_point_inset_tolerance_m=.0001,max_replacement_overlap_beyond_tolerance_m2=max_inset_overlap,
    unchanged_fixture_meshes=len(fittings['geometry']),corrected_residual_rays=pixel_results,cameras=camera_rows,
    original_reference_objects=2039,ground_level_is_inferred=True,door_interaction=False,
    complete_interior=False,runtime_exported=False,natural_use_verified=False,visual_acceptance=False,repairs=repairs)
write_path(f'evidence/{version}/sternen_checks.json').write_text(json.dumps(report,indent=2))
print('STERNEN_FRONTAGES_VERIFIED',json.dumps(report),flush=True)
