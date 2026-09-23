import bpy,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path('F:/MyWorld/ZurichWorld')
VERSION='G1_003r2'
scene=bpy.context.scene
base=json.loads((ROOT/'derived/G1_geo_base.json').read_text())
terrain=next(o for o in base['objects'] if o['kind']=='terrain_reference')
obj=bpy.data.objects['SURVEY_TERRAIN'];old=obj.data
mesh=bpy.data.meshes.new('SURVEY_TERRAIN_clipped_context')
mesh.from_pydata(terrain['vertices'],[],terrain['faces']);mesh.update()
mesh.materials.append(old.materials[0])
layer=mesh.uv_layers.new(name='LV95_SWISSIMAGE_reference')
coords=np.asarray(terrain['vertices'],dtype=float)
xy=(coords[:,:2]+np.array([2683775,1246700])-np.array([2683420,1246300]))/np.array([780,810])
uv=np.array([xy[l.vertex_index] for l in mesh.loops],dtype=np.float32)
layer.data.foreach_set('uv',uv.ravel())
obj.data=mesh
if old.users==0:bpy.data.meshes.remove(old)
# Reconcile surveyed structures by the actual official gid when EGID is absent.
col=bpy.data.collections['02_SURVEY_LOD2_REFERENCE']
for oldobj in list(col.objects):
    oldmesh=oldobj.data
    bpy.data.objects.remove(oldobj,do_unlink=True)
    if oldmesh.users==0:bpy.data.meshes.remove(oldmesh)
materials=[bpy.data.materials[n] for n in ['SURVEY roof | no finish inference',
           'SURVEY wall | no facade detail yet','SURVEY sunk bottom | not floor']]
for item in base['objects']:
    if item['kind']!='survey_building':continue
    m=bpy.data.meshes.new(item['id']);m.from_pydata(item['vertices'],[],item['faces']);m.update()
    o=bpy.data.objects.new(item['id'],m);col.objects.link(o)
    for key in ['kind','source','role','in_scope','floor_warning']:
        if key in item:o[key]=item[key]
    o['source_properties']=json.dumps(item['source_properties'])
    o['source_feature_ids']=json.dumps(item['source_feature_ids'])
    o['collision_status']='not_accepted_survey_bottoms_are_sunk'
    for material in materials:m.materials.append(material)
    m.polygons.foreach_set('material_index',item['materials'])
scene['quality_status']=VERSION+'_source_reference_not_accepted'
scene['version']=VERSION
scene.camera=bpy.data.objects['QA_Whole_context_SW']
native=ROOT/f'native/{VERSION}_source_reference.blend'
for o in scene.objects:o.select_set(o.type=='MESH')
out=ROOT/'web/assets';out.mkdir(parents=True,exist_ok=True)
glb=out/f'{VERSION}_survey.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
                         export_extras=True,export_yup=True,export_cameras=False,
                         export_lights=False,export_materials='EXPORT')
bpy.ops.wm.save_as_mainfile(filepath=str(native))
report={'native':str(native),'version':VERSION,'stage':'source_reference',
        'accepted':False,'survey_glb':str(glb),'glb_bytes':glb.stat().st_size,
        'glb_sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),'objects':len(scene.objects),
        'terrain_coverage_m2_missing':json.loads((ROOT/'derived/G1_geo_base_receipt.json').read_text())['scope_without_terrain_m2']}
(ROOT/'runtime/current_scene.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(out/'current.json').write_text(json.dumps({'version':VERSION,'survey_glb':glb.name,
    'quality':'source-reference','accepted':False,'photogrammetry_ready':False},indent=2),encoding='utf-8')
print(json.dumps(report))
