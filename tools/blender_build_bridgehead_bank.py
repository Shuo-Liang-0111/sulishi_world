"""Author full AV36232 upper-bank paving, guarding and twelve source trees.

TREE_IDS can limit tree batches; receipts guard resumptions. The final photo
replacement and version change happen only after every tree is complete.
"""
from pathlib import Path
import ast,hashlib,json,math
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridgehead_bank'
s=bpy.context.scene;assert s['version']=='G1_024'
assert Path(bpy.data.filepath).name=='G1_024_bridge_water_context_working.blend'
P=json.loads((D/'build_input.json').read_text(encoding='utf-8'));O=np.array(P['origin'])
E=R/'evidence/G1_025';E.mkdir(exist_ok=True)
root=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
def collection_named(name):
    c=bpy.data.collections.get(name)
    if c is None:c=bpy.data.collections.new(name);root.children.link(c)
    return c
C=collection_named('40_BRIDGEHEAD_BANK');treecol=collection_named('41_BRIDGEHEAD_TREES')
mats={'paving':bpy.data.materials['asphalt_03'],
      'soil':bpy.data.objects['LM_SOIL'].material_slots[0].material,
      'concrete':bpy.data.materials['QB | aged mineral structure'],
      'coping':bpy.data.materials['QB | dark dressed coping'],
      'steel':bpy.data.materials['RL | weathered zinc steel']}
src=ast.parse((R/'tools/blender_build_quaibruecke.py').read_text(encoding='utf-8'))
helper=ast.unparse(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','beam','sweep'}],type_ignores=[])).replace("'QB_'","'UB_'")
exec(compile(helper,'bank_geometry_helpers','exec'))

if globals().get('REBUILD_GROUND',False):
    # Only this unsaved batch's ground/rail collection may be rebuilt after
    # an observed support defect; all tree receipts and predecessor stay intact.
    assert s['version']=='G1_024' and all(o.name.startswith('UB_') for o in C.objects)
    for ob in list(C.objects):
        me=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
        if me.users==0:bpy.data.meshes.remove(me)
    C['geometry_complete']=False
if not C.get('geometry_complete',False):
    assert not len(C.objects),'Inspect incomplete ground before retry'
    for part in P['parts']:
        ob=mesh(part['name'],part['vertices'],part['faces'],part['role'],part['source'],.003 if part['role']=='coping' else 0)
        ob['source_plan_area_m2']=part['area_m2']
        if part['role']=='soil':
            ident=int(part['name'].split('_')[-1]);uv=ob.data.uv_layers.active
            phase=(ident%997)/997*2*np.pi;rotation=np.array([[np.cos(phase),-np.sin(phase)],[np.sin(phase),np.cos(phase)]])
            values=np.array([v.uv[:] for v in uv.data])@rotation.T/2
            uv.data.foreach_set('uv',values.astype(np.float32).ravel())
            for f in ob.data.polygons:f.use_smooth=True
    for rail in P['rails']:
        pts=np.array(rail['points']);dist=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(pts[:,:2],axis=0),axis=1))]
        def at(st):return np.array([np.interp(st,dist,pts[:,j]) for j in range(3)])
        n=max(1,int(math.ceil(dist[-1]/1.5)));posts=np.linspace(0,dist[-1],n+1)
        for j,sta in enumerate(posts):
            p=at(sta);beam(f'GUARD_{rail["index"]}_POST_{j}',p-[0,0,.022],p+[0,0,1.03],.045,.045,'steel',rail['source'],.001)
            beam(f'GUARD_{rail["index"]}_FOOT_{j}',p-[0,0,.025],p+[0,0,.012],.10,.10,'steel','inferred embedded rail base',.001)
        for z in [.14,.98]:
            sweep(f'GUARD_{rail["index"]}_CONTINUOUS_{z}',pts+[0,0,z],.023,'steel',rail['source'])
        for j,sta in enumerate(np.linspace(0,dist[-1],max(2,int(math.ceil(dist[-1]/.12))+1))):
            if min(abs(posts-sta))<.045:continue
            p=at(sta);beam(f'GUARD_{rail["index"]}_PICKET_{j}',p+[0,0,.125],p+[0,0,.993],.015,.015,'steel','inferred vertical-picket guarding',.0006)
    for ob in C.objects:ob['construction_batch']='G1_025'
    C['geometry_complete']=True;C['input_sha256']=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
    print('UPPER_BANK_GROUND_COMPLETE',len(C.objects),flush=True)

# Use existing individually seeded branch/leaf authoring, while removing the
# old regular seven-lobe collar and preserving the reviewed flaking-bark atlas.
path=R/'tools/blender_build_south_public_space.py';module=ast.parse(path.read_text(encoding='utf-8'))
start=next(i for i,n in enumerate(module.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='old' for t in n.targets))
end=next(i for i,n in enumerate(module.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cutpath' for t in n.targets))
code=ast.unparse(ast.Module(body=module.body[start:end],type_ignores=[])).replace('BS_TREE_','UB_TREE_')
code=code.replace("bpy.data.materials['HB | continuous plane trunk atlas']","bpy.data.materials['ZW | plane trunk exfoliation patches']")
replacements={
 'phase = rng.uniform(0, 6.28)': 'phase = rng.uniform(0, 6.28)\n    root_axes = rng.uniform(0, 2*np.pi, 6)\n    root_weights = rng.uniform(.30, 1., 6)\n    root_widths = rng.uniform(.17, .34, 6)',
 'lobes = (0.5 + 0.5 * math.cos(7 * a + phase + 0.15 * math.sin(3 * a))) ** 3': 'lobes = sum(w*np.exp(-(np.arctan2(np.sin(a-aa),np.cos(a-aa))/width)**2) for aa,w,width in zip(root_axes,root_weights,root_widths))',
 'flare = (0.025 + girth * 0.45 * lobes) * math.exp(-max(z, 0) / 0.25)': 'flare = (.012 + girth*.23*lobes)*math.exp(-max(z,0)/.25)',
 'scaffolds = 5 if ident == 68441 else 6':'scaffolds = 5 + ident % 3'
}
for before,after in replacements.items():
    assert code.count(before)==1,before;code=code.replace(before,after)
growth=compile(code,'bridgehead_plane_growth','exec')
targets=set(globals().get('TREE_IDS',[p['source']['properties']['objectid'] for p in P['trees']]))
for entry in P['trees']:
    ident=entry['source']['properties']['objectid']
    if ident not in targets:continue
    names=[f'UB_TREE_{ident}_{key}' for key in ['WOOD','TWIGS','LEAVES']]
    if treecol.get(f'complete_{ident}',False):
        assert all(name in bpy.data.objects for name in names);continue
    assert not any(name in bpy.data.objects for name in names),'Inspect incomplete tree before retry'
    ns={'R':R,'bpy':bpy,'ast':ast,'json':json,'math':math,'np':np,'td':{'trees':[entry]},'collection':treecol}
    exec(growth,ns)
    ob=bpy.data.objects[names[0]];uv=ob.data.uv_layers.active
    atlas=bpy.data.materials['ZW | plane trunk exfoliation patches']
    material_ids=[i for i,slot in enumerate(ob.material_slots) if slot.material==atlas]
    loops=[li for face in ob.data.polygons if face.material_index in material_ids for li in face.loop_indices]
    vmax=max(uv.data[li].uv.y for li in loops)
    if vmax>.998:
        for li in loops:
            z=uv.data[li].uv.y
            if z>.65:uv.data[li].uv.y=.65+(z-.65)*(.998-.65)/(vmax-.65)
    for name in names:bpy.data.objects[name]['construction_batch']='G1_025'
    rec=ns['reports'][0];treecol[f'complete_{ident}']=True;treecol[f'report_{ident}']=json.dumps(rec)
    (E/'tree_progress.json').write_text(json.dumps({'completed':[json.loads(treecol[k]) for k in treecol.keys() if k.startswith('report_')],'native_saved':False},indent=2),encoding='utf-8')
    del ns
    print('UPPER_BANK_TREE_COMPLETE',ident,flush=True)

complete=all(treecol.get(f'complete_{p["source"]["properties"]["objectid"]}',False) for p in P['trees'])
if complete:
    cutpath=R/'derived/bellevue/west_context/bridgehead_bank_cut.json';cut=json.loads(cutpath.read_text(encoding='utf-8'))
    prior=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(prior.read_bytes()).hexdigest()
    previous={str(q['node']):q for q in json.loads(prior.read_text(encoding='utf-8'))['overrides']}
    working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};changed=[]
    for rec in cut['overrides']:
        key=str(rec['node'])
        if rec==previous.get(key):continue
        ob=working[key];materials=[slot.material for slot in ob.material_slots]
        v=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
        me=bpy.data.meshes.new('UB_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
        for mat in materials:me.materials.append(mat)
        layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel());ob.data=me
        for slot,mat in zip(ob.material_slots,materials):slot.material=mat
        ob['construction_mask']=cut['mask_basis'];changed.append(key)
    assert set(changed)==set(cut['bank_changed_nodes'])
    bpy.context.view_layer.update()
    for name,xy,target,lens in [
        ('UB_QA_NORTH',[2683519.,1246810.],[2683534.,1246778.,410.5],30),
        ('UB_QA_SOUTH',[2683548.,1246757.],[2683518.,1246807.,411.],30),
        ('UB_QA_STAIR_TOP',[2683516.,1246802.],[2683510.4,1246805.,407.8],30),
        ('UB_QA_ROOT',[2683517.8,1246805.],[2683514.687,1246807.685,409.5],36)]:
        local=np.array(xy)-O[:2];levels=[]
        for ob in C.objects:
            if ob.get('surface_role') not in ['paving','soil']:continue
            hit,q,_,_=ob.ray_cast(Vector((*local,30)),Vector((0,0,-1)))
            if hit:levels.append(q.z)
        assert levels,(name,'No constructed ground')
        z=max(levels);cam=bpy.data.objects.new(name,bpy.data.cameras.new(name));bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(cam)
        cam.location=(*local,z+1.65);cam.rotation_euler=(Vector(np.array(target)-O)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
        cam['eye_height_m']=1.65;cam['floor_height_local']=z
    s['version']='G1_025';s['photo_cut_file']=cutpath.relative_to(R).as_posix();s.camera=bpy.data.objects['QB_QA_SOUTH'];bpy.context.view_layer.update()
    (E/'construction.json').write_text(json.dumps(dict(version=s['version'],ground_objects=len(C.objects),tree_objects=len(treecol.objects),
        photo_nodes=changed,input_sha256=C['input_sha256'],original_photo_nodes_retained=2039,
        native_saved=False,visual_acceptance=False,natural_use_verified=False,cameras_exposure_sky_sun_unchanged=True),indent=2),encoding='utf-8')
print('UPPER_BANK_BATCH',json.dumps({'trees_complete':sum(treecol.get(f'complete_{p["source"]["properties"]["objectid"]}',False) for p in P['trees']),'all_complete':complete,'scene_version':s['version']}),flush=True)
