"""Remove a ray-identified photo remnant and prevent trunk-atlas root repetition."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_016'
assert 'BE_QA_SOUTH_EAST_BIN_OPENING' in bpy.data.objects
E=R/'evidence/G1_016r1';E.mkdir(exist_ok=True)
ob=bpy.data.objects['CTX_I3S_33492'];mesh=ob.data
vertices=np.array([v.co[:] for v in mesh.vertices]);faces=np.array([p.vertices[:] for p in mesh.polygons]);tri=vertices[faces]
world=np.array([[ob.matrix_world@Vector(p) for p in t] for t in tri])
mask=(world[:,:,2].max(1)<9)&(world[:,:,0].min(1)>-183)&(world[:,:,0].max(1)<-180)&(world[:,:,1].min(1)>110)&(world[:,:,1].max(1)<113)
assert mask.sum()==71
for i in [292,463,469]:assert mask[i]
# Every removed face must be backed by already modeled paving, not empty ground.
ground=[o for o in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects if o.type=='MESH' and
        (o.name in ['BS_ASPHALT','BS_CURB_TOP','BE_PUBLIC_PLATFORM'] or o.name.startswith('BE_PAVING_'))]
supports=[]
for point in world[mask].mean(1):
    hits=[]
    for floor in ground:
        inverse=floor.matrix_world.inverted();hit,p,_,_=floor.ray_cast(inverse@Vector((point[0],point[1],10)),inverse.to_3x3()@Vector((0,0,-1)))
        if hit:
            z=(floor.matrix_world@p).z
            if 0<point[2]-z<.65:hits.append((point[2]-z,floor.name))
    assert hits,('Photographic removal lacks actual rebuilt ground',point.tolist())
    supports.append(min(hits))
cut=json.loads((R/s['photo_cut_file']).read_text());record=next(x for x in cut['overrides'] if str(x['node'])=='33492')
source_v=np.asarray(record['vertices']).reshape(-1,3,3);source_uv=np.asarray(record['uv_source_v_unflipped']).reshape(-1,3,2)
assert source_v.shape==tri.shape and np.max(np.abs(source_v-tri))<.0001
record['vertices']=source_v[~mask].reshape(-1,3).tolist();record['uv_source_v_unflipped']=source_uv[~mask].reshape(-1,2).tolist()
cut['mask_basis']+='; G1_016r1 removes only71 ray-identified floating faces of33492 above verified authored paving (0.8773m2).'
cut_file='derived/bellevue/west_context/east_facilities_surface_cut.json';path=R/cut_file;path.write_text(json.dumps(cut,separators=(',',':')))
me=bpy.data.meshes.new('BSE_SURFACE_CONTEXT_33492');v=np.asarray(record['vertices']);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
for mat in mesh.materials:me.materials.append(mat)
uv=me.uv_layers.new(name='source_photo_uv');data=np.asarray(record['uv_source_v_unflipped']);data[:,1]=1-data[:,1];uv.data.foreach_set('uv',data.astype(np.float32).ravel())
ob.data=me;ob['construction_mask']=cut['mask_basis']
tree_records=[]
for tree in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
    if tree.type!='MESH' or not tree.name.endswith('_WOOD'):continue
    indices=[i for i,m in enumerate(tree.data.materials) if m and m.name=='HB | continuous plane trunk atlas']
    if not indices:continue
    uv=tree.data.uv_layers.active;loops=[li for p in tree.data.polygons if p.material_index in indices for li in p.loop_indices]
    vmax=max(uv.data[li].uv.y for li in loops)
    if vmax<=.999:continue
    before=np.array([v.co[:] for v in tree.data.vertices]);changed=0
    # The atlas represents coarse root bark transitioning to upper flaking bark.
    # Keep the lower2.925m untouched; fit only the upper inferred pattern before
    # the V seam. This prevents a new coarse-root band at every4.5m height.
    for li in loops:
        v=uv.data[li].uv.y
        if v>.65:uv.data[li].uv.y=.65+(v-.65)*(.998-.65)/(vmax-.65);changed+=1
    assert max(uv.data[li].uv.y for li in loops)<=.999
    assert np.array_equal(before,np.array([v.co[:] for v in tree.data.vertices]))
    tree['bark_uv_basis']='Keep lower2.925m mapping; fit upper inferred flaking pattern below atlasV1 to avoid repeating coarse roots. Geometry/position/height untouched.'
    tree_records.append({'object':tree.name,'previous_vmax':vmax,'corrected_vmax':max(uv.data[li].uv.y for li in loops),'changed_loops':changed})
assert any(x['object']=='BS_TREE_114064_WOOD' for x in tree_records)
s['version']='G1_016r1';s['photo_cut_file']=cut_file;s.camera=bpy.data.objects['BE_QA_SOUTH_EAST_INFO_WIDE']
bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_016r1_east_surface_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=cut_file,source_cut_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True,next='Review east information frames, bin aperture, corrected bark and remnant removal; runtime export and natural use remain pending.')
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
report={'version':s['version'],'native':str(native),'removed_photo_node':'33492','removed_faces':int(mask.sum()),'removed_surface_area_m2':float(np.linalg.norm(np.cross(world[mask,1]-world[mask,0],world[mask,2]-world[mask,0]),axis=1).sum()/2),'support_objects':sorted(set(x[1] for x in supports)),'support_gap_range_m':[min(x[0] for x in supports),max(x[0] for x in supports)],'corrected_tree_uvs':tree_records,'original_photo_objects_preserved':len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects),'accepted':False}
(E/'surface_repair.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
