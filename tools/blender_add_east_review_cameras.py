"""Add full-extent and deposit-opening review cameras, without moving objects."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_016'
d=json.loads((R/'derived/bellevue/south_context/east_facilities/input.json').read_text())
ground=bpy.data.objects['BS_ASPHALT'];collection=bpy.data.collections['90_REVIEW_CAMERAS']
records=[]
for suffix in ['INFO','REVERSE']:
    name='BE_QA_SOUTH_EAST_'+suffix+'_WIDE'
    assert name not in bpy.data.objects
    source=bpy.data.objects['BE_QA_SOUTH_EAST_'+suffix]
    camera=source.copy();camera.data=source.data.copy();camera.name=name
    collection.objects.link(camera);camera.data.lens=26
    camera['review_purpose']='Show entire information frame, foot contact and approach; original detail view retained.'
    records.append(camera)
base=bpy.data.objects['BE_QA_SOUTH_EAST_BIN']
# Geometry is centered on the source bin XY in local LV95 coordinates.
parts=[o for o in bpy.data.collections['26_BELLEVUE_SOUTH_EAST_FACILITIES'].objects if o.name.startswith('BSE_BIN1173_')]
assert len(parts)==9
origin=d['origin']
source=d['bin']['source'];assert source['geometry']['type']=='MultiPoint'
xy=source['geometry']['coordinates'][0]
centre=Vector((xy[0]-origin[0],xy[1]-origin[1],d['bin']['ground_local']))
bearing=math.radians(float(source['properties']['orientierung']))
front=Vector((math.sin(bearing),math.cos(bearing),0));right=Vector((-front.y,front.x,0))
position=centre+front*3+right*.65
hit,p,_,_=ground.ray_cast(Vector((position.x,position.y,40)),Vector((0,0,-1)))
assert hit,'Bin-opening review camera must stand on actual constructed ground'
name='BE_QA_SOUTH_EAST_BIN_OPENING';assert name not in bpy.data.objects
camera=base.copy();camera.data=base.data.copy();camera.name=name;collection.objects.link(camera)
camera.location=(position.x,position.y,p.z+1.65)
camera.rotation_euler=(centre+Vector((0,0,.75))-camera.location).to_track_quat('-Z','Y').to_euler()
camera['eye_height_m']=1.65;camera['review_purpose']='Deposit aperture, liner, folded rim and front approach from source bearing.'
records.append(camera)
bpy.context.view_layer.update()
report=[]
for camera in records:
    hit,p,_,_=ground.ray_cast(Vector((camera.location.x,camera.location.y,40)),Vector((0,0,-1)))
    assert hit and abs(camera.location.z-p.z-1.65)<.003
    report.append({'name':camera.name,'lens_mm':camera.data.lens,'position_local':list(camera.location),'eye_above_actual_ground_m':camera.location.z-p.z})
(R/'evidence/G1_016/additional_review_cameras.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
