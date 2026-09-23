"""Correct visibly unsupported window sills and add modest cafe display depth."""
import bpy,bmesh,json,ast,math,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_009r2'
building=bpy.data.collections['16_HAUS_BELLEVUE_STREET'];d=json.loads((R/'derived/haus_bellevue/build_input.json').read_text());f=d['frontage'];C=np.array(f['C']);right=np.array(f['right']);front=np.array(f['out']);FLOOR=f['floor_local']
def P(u,v,z):
 xy=C+u*right+v*front;return (*xy,FLOOR+z)
tree=ast.parse((R/'tools/blender_build_bellevue.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','box','lathe','tube']],type_ignores=[]),'helpers','exec'))
stone=bpy.data.materials['HB | grey sandstone plinth'];wood=bpy.data.materials['oak_veneer_01'];glass=bpy.data.materials['HB | clear shop glazing 8mm'];bronze=bpy.data.materials['HB | dark bronze storefront metal'];brass=bpy.data.materials['HB | brushed brass handle']
next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value=.035
def paper(name,c):
 m=bpy.data.materials.new('HB | '+name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(*c,1);n.inputs['Roughness'].default_value=.68;return m
papers=[paper('display sage paper',(.22,.32,.19)),paper('display cream paper',(.61,.54,.38)),paper('display rose paper',(.38,.155,.13))];ribbon=paper('display satin ribbon',(.65,.55,.30))
for i,(a,b) in enumerate(f['bays']):
 mid=(a+b)/2;w=b-a
 if i==f['entry_bay_index']:
  ob=box('HB_ENTRY_THRESHOLD_BASE',(mid,-.095,-.1925),(w,.82,.405),stone,.004)
 else:
  ob=box(f'HB_BAY_{i}_GROUND_PLINTH',(mid,-.15,-.1325),(w-.025,.71,.545),stone,.005)
 ob['evidence_basis']='Solid sill support extending into reconstructed ground; required by observed unsupported gap, inferred fabrication.'
 if i>=4:continue
 # The business is a cafe/confiserie. These few unbranded cartons are explicitly
 # designed display dressing; they do not reproduce a photographed product layout.
 for j in range(5):
  u=mid+(j-2)*.245;v=-.97-(j%2)*.075;z=.653
  for k in range(1+(j in [1,3])):
   width=.19-.025*k;height=.065;zz=z+k*.072
   for tag,center,dims,ma in [('BOX',(u,v,zz+height/2),(width,.145,height),papers[(i+j+k)%3]),('LID',(u,v,zz+height+.007),(width+.008,.153,.014),papers[(i+j+k)%3]),('RIBBON',(u,v,zz+height+.015),(.019,.154,.002),ribbon),('RIBBON_CROSS',(u,v,zz+height+.016),(width+.009,.014,.002),ribbon)]:
    q=box(f'HB_CAFE_GIFT_{i}_{j}_{k}_{tag}',center,dims,ma,.002);q['evidence_basis']='Designed unbranded cafe/confectionery display, not surveyed merchandise placement.'
for ob in building.objects:
 if not ob.get('egid'):ob['egid']=9011202
 if not ob.get('place'):ob['place']='Haus Bellevue south streetfront'
 if not ob.get('quality_status'):ob['quality_status']='construction candidate'
 if not ob.get('collision_role') and ob.type=='MESH':ob['collision_role']='solid_pending_runtime'
s['version']='G1_009r3';s.camera=bpy.data.objects['HB_QA_ALONG'];bpy.context.view_layer.update();native=R/'native/G1_009r3_haus_frontage_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
out=R/'evidence/G1_009r3';out.mkdir(exist_ok=True);(out/'refinement.json').write_text(json.dumps({'version':s['version'],'solid_sill_bases':9,'glazing_roughness':.035,'designed_cafe_dressing':'28 small unbranded gift cartons with lids and ribbon strips; placement inference','remaining':'Upper facade, corner tower, tree119962, neighboring fronts, street equipment, function and runtime visual checks incomplete.','accepted':False},indent=2));print(json.dumps({'version':s['version'],'native':str(native),'objects':len(building.objects),'accepted':False}))
