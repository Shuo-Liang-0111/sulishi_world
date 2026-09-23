import bpy,json,struct,math
from mathutils import Vector
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert str(scene['version']).startswith(('G1_005','G1_006','G1_007','G1_008','G1_009','G1_010','G1_011','G1_012','G1_013','G1_014','G1_015','G1_016','G1_017','G1_018','G1_019','G1_020','G1_021','G1_022','G1_023'))
camera=globals().get('REVIEW_CAMERA','BE_QA_ENTRY')
scene.camera=bpy.data.objects[camera]
scene.cycles.samples=globals().get('REVIEW_SAMPLES',32)
if globals().get('REVIEW_DEVICE'):
    scene.cycles.device=REVIEW_DEVICE
scene.render.resolution_x,scene.render.resolution_y=globals().get('REVIEW_RESOLUTION',(1600,1050))
out=ROOT/'evidence'/scene['version'];out.mkdir(exist_ok=True)
scene.render.filepath=str(out/(camera+'.png'))
# Keep all authored 4K surfaces and all source geometry. Only background source
# photography uses the already verified runtime mip cache for distant tiles.
# The original native links are always restored after rendering, including failure.
with (ROOT/'web/assets/G1_004r2_photo_stream.glb').open('rb') as file:
    file.seek(12);length,tag=struct.unpack('<II',file.read(8));manifest=json.loads(file.read(length))
records={m['name']:m['extras']['runtime_texture_lod'] for m in manifest['materials']}
candidates=[]
for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
    corners=[ob.matrix_world@Vector(p) for p in ob.bound_box];center=sum(corners,Vector())/8
    radius=max((p-center).length for p in corners);distance=max(1,(center-scene.camera.location).length-radius)
    # Resolve object-level overrides too: linked meshes retain library material
    # defaults, while the editable working scene uses local object materials.
    for slot in ob.material_slots:
        mat=slot.material
        if mat and mat.name in records:candidates.append((distance,mat,records[mat.name]))
candidates.sort(key=lambda x:x[0]);changed=[];counts={'full':0,'medium':0,'low':0};budget=0
try:
    for distance,mat,record in candidates:
        cost=record['width']*record['height']*4
        if distance<100 and counts['full']<180 and budget+cost<300*1024*1024:
            counts['full']+=1;budget+=cost;continue
        tier='medium' if distance<200 else 'low';counts[tier]+=1
        image=bpy.data.images.load(str(ROOT/'web/assets'/record[tier]),check_existing=True)
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE':changed.append((node,node.image));node.image=image
    result=bpy.ops.render.render(write_still=True,scene=scene.name)
    assert 'FINISHED' in result, f'Render operator did not finish: {result}'
finally:
    for node,image in changed:node.image=image
(out/(camera+'_render_settings.json')).write_text(json.dumps({'version':scene['version'],'camera':camera,'device':scene.cycles.device,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'resolution_percentage':scene.render.resolution_percentage,'samples':scene.cycles.samples,'denoising':scene.cycles.use_denoising,'background_texture_tiers':counts,'authored_textures_downscaled':False,'geometry_hidden_or_decimated':False,'original_links_restored':True},indent=2))
print(json.dumps({'version':scene['version'],'camera':camera,'image':scene.render.filepath,'quality':'construction review, not final acceptance'}))
