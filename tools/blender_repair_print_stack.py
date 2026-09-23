"""Place actual printed geometry between the artwork and the glazing surfaces."""
import bpy,json,hashlib,shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_015r2'
d=json.loads((R/'derived/bellevue/south_service/input.json').read_text())
front=Vector((*d['axis_v'],0))
parts=list(bpy.data.collections['24_BELLEVUE_SERVICE_PAVILION'].objects)
records=[]
bpy.context.view_layer.update()
for part in parts:
    if not (part.name.startswith('SV_AD_') and any(k in part.name for k in ['_TEXT_','_ART_LINE_','_FOOT'])):continue
    before=part.matrix_world.copy()
    if part.type=='CURVE':
        # Keep the editable line and its width in the poster plane, but make the
        # ink layer thin in depth: the old2.4mm tubes cannot fit a1mm glazing gap.
        points=[before@Vector(p.co[:3]) for sp in part.data.splines for p in sp.points]
        centre=sum(points,Vector())/len(points)
        right=Vector((*d['axis_u'],0))
        rotation=Matrix((right,front,Vector((0,0,1)))).transposed()
        assert abs(rotation.determinant()-1)<.00001
        inverse=rotation.transposed()
        for spline in part.data.splines:
            for point in spline.points:
                local=inverse@(before@Vector(point.co[:3])-centre)
                point.co=(*local,1)
        # Align the object's local axes first. An arbitrary world-space affine
        # scale would introduce shear which Blender's object TRS cannot retain.
        part.matrix_world=Matrix.Translation(centre+front*.0009)@rotation.to_4x4()@Matrix.Diagonal((1,.04,1,1))
    else:
        part.matrix_world=Matrix.Translation(front*.0009)@before
    part['print_depth_basis']='Ink plane between artwork and cover glass. Text plane0.4mm above substrate; line depth compressed to0.096mm with in-plane width retained.'
    records.append(part.name)
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();gaps=[]
for name in records:
    ob=bpy.data.objects[name];prefix='_'.join(name.split('_')[:3])
    art=bpy.data.objects[prefix+'_ART'];glass=bpy.data.objects[prefix+'_GLASS']
    def depth(obj):
        evaluated=obj.evaluated_get(deps);me=evaluated.to_mesh()
        values=[front.dot(obj.matrix_world@v.co) for v in me.vertices]
        evaluated.to_mesh_clear();return min(values),max(values)
    lo,hi=depth(ob);art_front=depth(art)[1];glass_back=depth(glass)[0]
    gaps.append({'name':name,'ink_above_art_m':lo-art_front,'glass_clearance_m':glass_back-hi})
    assert lo-art_front>.0001 and glass_back-hi>.0001,(name,lo-art_front,glass_back-hi)
assert len(records)==60
s['version']='G1_015r3';native=R/'native/G1_015r3_service_surface_working.blend'
old_cache=R/'derived/runtime_occlusion/G1_015r2';cache=R/'derived/runtime_occlusion'/s['version'];cache.mkdir(exist_ok=True)
shutil.copyfile(old_cache/'receiver_uv.npz',cache/'receiver_uv.npz')
manifest=json.loads((old_cache/'manifest.json').read_text());manifest.update(version=s['version'],native=str(native),uv_file=str((cache/'receiver_uv.npz').relative_to(R)))
(cache/'manifest.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),accepted=False,not_published=True,
 next='Verify corrected soffit and printed-layer stack at normal eye height; rebuild version-matched lighting/export. Then construct prepared east-side mast4211, info2717/2580 and bin1173. Whole G1 and natural use remain incomplete.')
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
report={'version':s['version'],'native':str(native),'printed_parts':len(records),'gaps':gaps,
 'min_ink_above_art_m':min(x['ink_above_art_m'] for x in gaps),
 'min_glass_clearance_m':min(x['glass_clearance_m'] for x in gaps),
 'artwork_and_glass_unchanged':True,'editable_curve_width_retained':True,'visual_acceptance':False}
e=R/'evidence'/s['version'];e.mkdir(exist_ok=True);(e/'print_stack.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='gaps'}))
