"""Photo-constrained public interior refinement, preserving the surveyed envelope."""
import bpy,bmesh,json,math,ast
from pathlib import Path
from mathutils import Vector
import numpy as np
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_005r4'
data=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
C=np.array(data['center_lv95'])-np.array(data['origin'][:2]);FLOOR=data['ground_fit']['ground_plane_z_ln02'][2]-400
angle=math.radians(-102);front=np.array([math.cos(angle),math.sin(angle)]);right=np.array([-front[1],front[0]])
building=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
tree=ast.parse((ROOT/'tools/blender_build_bellevue.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['P','mesh','triangles','box','lathe','arc','tube','material']]
exec(compile(ast.Module(body=functions,type_ignores=[]),'bellevue_geometry_helpers','exec'))
steel=bpy.data.materials['BE | stainless counter'];aluminium=bpy.data.materials['BE | satin anodised aluminium']
dark=bpy.data.materials['BE | dark structural metal'];wood=bpy.data.materials['oak_veneer_01'];wood.use_fake_user=True
wood['license']='CC0';wood['source_url']='https://polyhaven.com/a/oak_veneer_01';wood['size_m']=1.83
for n in wood.node_tree.nodes:
    if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.16
    if n.type=='OUTPUT_MATERIAL':
        for link in list(n.inputs['Displacement'].links):wood.node_tree.links.remove(link)
paint=material('BE | pale rear wall',(.67,.645,.56),.82)
rubber=material('BE | equipment black rubber',(.018,.02,.019),.68)
porcelain=material('BE | warm porcelain',(.77,.765,.71),.24)
coffee=material('BE | espresso liquid',(.041,.016,.007),.19)
bottle=material('BE | dark green beverage glass',(.035,.09,.026),.16,0,.72)
label=material('BE | paper bottle band',(.61,.60,.53),.8)
etch=material('BE | translucent etching',(.62,.64,.60),.40,0,.25)
counter_bs=steel.node_tree.nodes.get('Principled BSDF');counter_bs.inputs['Roughness'].default_value=.32
counter_bs.inputs['Anisotropic'].default_value=.35

def remove_prefixes(prefixes):
    for ob in list(building.objects):
        if ob.name.startswith(tuple(prefixes)):bpy.data.objects.remove(ob,do_unlink=True)
def wood_uv(ob,mode='slat',seed=0):
    ob.data.materials.clear();ob.data.materials.append(wood)
    layer=ob.data.uv_layers.get('real_joinery_scale') or ob.data.uv_layers.new(name='real_joinery_scale')
    for loop in ob.data.loops:
        p=ob.data.vertices[loop.vertex_index].co;xy=np.array(p[:2])-C
        u,v=float(np.dot(xy,right)),float(np.dot(xy,front));z=p.z-FLOOR
        # Asset grain runs V. Keep it along each horizontal slat, not vertically across the wall.
        uv=(z/1.83+seed*.127,u/1.83+seed*.361) if mode=='slat' else (u/1.83,v/1.83)
        layer.data[loop.index].uv=uv
    ob['texture_orientation']='Wood grain follows actual joinery; 1.83m source texture scale'

# Low wooden service screen and its pale upper wall are separate, as photographed.
remove_prefixes(['BE_SERVICE_PARTITION','BE_WOOD_SLAT_','BE_SERVICE_CABINET','BE_SERVICE_WORKTOP','BE_SERVICE_PLINTH','BE_ESPRESSO_'])
box('BE_SERVICE_PARTITION',(0,-2.10,1.15),(12.6,.17,2.30),dark)
box('BE_REAR_UPPER_WALL',(0,-2.10,2.61),(12.6,.17,.60),paint)
for i in range(53):
    ob=box('BE_WOOD_SLAT_%02d'%i,(0,-1.998,.16+i*.040),(12.5,.055,.031),wood,.002)
    wood_uv(ob,'slat',i)
shelf=box('BE_REAR_BOTTLE_LEDGE',(0,-1.965,2.315),(12.55,.23,.035),wood,.004);wood_uv(shelf,'slat')
for i in range(27):
    u=-5.72+i*.44
    ob=lathe('BE_REAR_BOTTLE_%02d'%i,[(0,2.34),(.026,2.34),(.030,2.36),(.030,2.51),(.020,2.54),(.011,2.56),(.011,2.625),(0,2.625)],bottle,(u,-1.91),32)
    ob['evidence_basis']='Row of bottles observed in operator photo; count and exact positions inferred'
    lathe('BE_REAR_BOTTLE_LABEL_%02d'%i,[(.0305,2.41),(.0305,2.458)],label,(u,-1.91),32)
    lathe('BE_REAR_BOTTLE_CAP_%02d'%i,[(.012,2.621),(.012,2.631),(0,2.631)],dark,(u,-1.91),24)

# Real supported rear work station; generic two-group equipment, no invented brand.
u,v=-2.3,-1.35
box('BE_SERVICE_PLINTH',(u,v,.045),(1.57,.91,.09),rubber)
box('BE_SERVICE_CABINET',(u,v,.54),(1.65,.95,.99),steel)
box('BE_SERVICE_WORKTOP',(u,v,1.055),(1.74,1.06,.07),steel)
for du in [-.42,.42]:
    box('BE_CABINET_DOOR_'+str(du),(u+du,v+.483,.57),(.80,.026,.84),steel,.008)
    tube('BE_CABINET_PULL_'+str(du),[P(u+du-.13,v+.525,.88),P(u+du+.13,v+.525,.88)],.008,dark)
for du in [-.42,.42]:
    for dv in [-.22,.22]:lathe('BE_ESPRESSO_FOOT_%s_%s'%(du,dv),[(.027,1.09),(.027,1.18)],rubber,(u+du,v+dv),24)
body=box('BE_ESPRESSO_BODY',(u,v,1.47),(1.08,.62,.58),steel,.055)
body['evidence_basis']='Operating photo locates equipment behind the bar; precise appliance design and position inferred'
box('BE_ESPRESSO_FRONT_RECESS',(u,v+.313,1.39),(.89,.022,.31),rubber,.018)
box('BE_ESPRESSO_CONTROL_BAND',(u,v+.33,1.66),(1.0,.035,.13),steel,.012)
box('BE_ESPRESSO_DRIP_FRAME',(u,v+.41,1.13),(1.04,.33,.055),steel,.016)
box('BE_ESPRESSO_DRIP_WELL',(u,v+.415,1.16),(.96,.265,.012),rubber,.007)
for i in range(29):
    x=u-.46+i*.0325;tube('BE_ESPRESSO_DRAIN_GRILLE_%02d'%i,[P(x,v+.30,1.17),P(x,v+.53,1.17)],.0025,aluminium)
for k,du in enumerate([-.24,.24]):
    lathe('BE_ESPRESSO_GROUP_COLLAR_%d'%k,[(.066,1.47),(.073,1.50),(.066,1.55)],steel,(u+du,v+.36),40)
    tube('BE_ESPRESSO_PORTAFILTER_%d'%k,[P(u+du,v+.39,1.46),P(u+du,v+.61,1.45)],.018,rubber)
    tube('BE_ESPRESSO_TWIN_SPOUT_%d'%k,[P(u+du-.025,v+.40,1.425),P(u+du-.025,v+.40,1.44),P(u+du+.025,v+.40,1.44),P(u+du+.025,v+.40,1.425)],.007,steel)
    for j in range(4):box('BE_ESPRESSO_BUTTON_%d_%d'%(k,j),(u+du-.075+j*.05,v+.35,1.66),(.028,.016,.027),rubber,.004)
for sign in [-1,1]:
    tube('BE_ESPRESSO_STEAM_WAND_'+str(sign),[P(u+sign*.46,v+.30,1.53),P(u+sign*.55,v+.40,1.40),P(u+sign*.55,v+.40,1.23)],.008,steel)
    tube('BE_ESPRESSO_VALVE_'+str(sign),[P(u+sign*.48,v+.30,1.65),P(u+sign*.48,v+.40,1.65)],.027,rubber)
tube('BE_ESPRESSO_CUP_RAIL',[P(u-.50,v-.23,1.81),P(u-.50,v+.22,1.81),P(u+.50,v+.22,1.81),P(u+.50,v-.23,1.81)],.006,aluminium)
def cup(name,u,v,z):
    lathe(name,[(0,z),(.027,z),(.033,z+.01),(.045,z+.084),(.041,z+.09),(.037,z+.081),(.028,z+.014),(0,z+.014)],porcelain,(u,v),48)
    tube(name+'_HANDLE',[P(u+.042+.022*math.cos(t),v,z+.048+.029*math.sin(t)) for t in np.linspace(-math.pi/2,math.pi/2,20)],.006,porcelain)
for i in range(5):cup('BE_CUP_WARMER_%02d'%i,u-.37+i*.18,v-.04,1.765)
for i in range(2):cup('BE_SERVICE_CUP_%d'%i,u+(-.24 if i==0 else .24),v+.41,1.175)

# Counter construction, ordinary hand-contact edges and foot rail.
for k in range(4):
    a=math.radians(-78+k*52);p=(3.67*math.sin(a),3.67*math.cos(a))
    tube('BE_BAR_FOOTRAIL_BRACKET_%d'%k,[P(p[0]*.957,p[1]*.957,.20),P(*p,.20)],.011,steel)
tube('BE_BAR_FOOTRAIL',[P(3.72*math.sin(a),3.72*math.cos(a),.20) for a in np.linspace(math.radians(-100),math.radians(100),150)],.021,steel)
for i,ob in enumerate([o for o in building.objects if o.name.startswith('BE_HIGH_TABLE_')]):wood_uv(ob,'table',i)

# Centre skylight structural glazing bars and restrained windrose markings.
for i in range(32):
    a=2*math.pi*i/32
    points=[(C[0]+r*math.cos(a),C[1]+r*math.sin(a),z-400+.012) for r,z in [(.13,414.595),(3.24,413.615)]]
    ob=tube('BE_SKYLIGHT_GLAZING_BAR_%02d'%i,points,.016,aluminium)
    ob['evidence_basis']='Fine radial glazing bars observed in original aerial; count/profile inferred within surveyed cone'
for i in range(24):
    a=2*math.pi*i/24+.04
    points=[P(r*math.sin(a),r*math.cos(a),2.917) for r in [1.15,3.02]]
    ob=tube('BE_WINDROSE_ETCH_BAR_%02d'%i,points,.009,etch)
    ob['evidence_basis']='Etched direction strips photographed; unreadable city inscriptions not invented'
for title,degrees in [('O',0),('NO',45),('N',90),('NW',135),('W',180),('SW',225),('S',270),('SO',315)]:
    a=math.radians(degrees);font=bpy.data.curves.new('Windrose '+title,'FONT');font.body=title;font.size=.11;font.align_x='CENTER';font.align_y='CENTER';font.extrude=.0005
    ob=bpy.data.objects.new('BE_WINDROSE_DIRECTION_'+title,font);building.objects.link(ob);font.materials.append(aluminium)
    ob.location=(C[0]+3.4*math.cos(a),C[1]+3.4*math.sin(a),FLOOR+2.902);ob.rotation_euler=(math.pi,0,a+math.pi/2)
    ob['evidence_basis']='German compass directions photographed; orientation follows true scene north'

# Thin architectural glass shadow approximation, matching the realtime no-opaque-shadow policy.
# Full shadow-caustic experiment cost 293s without useful visual gain; retain its old file.
for ob in building.objects:
    if hasattr(ob.cycles,'is_caustics_caster'):ob.cycles.is_caustics_caster=False;ob.cycles.is_caustics_receiver=False
    if ob.type=='MESH' and any(m and ('glass' in m.name or 'etching' in m.name) for m in ob.data.materials):
        ob.visible_shadow=False;ob['shadow_transport']='thin translucent surface; opaque shadow disabled as documented render approximation'
for ld in bpy.data.lights:
    if hasattr(ld.cycles,'is_caustics_light'):ld.cycles.is_caustics_light=False
scene.world.cycles.is_caustics_light=False;scene.cycles.caustics_refractive=False
scene.cycles.diffuse_bounces=6;scene.cycles.transmission_bounces=8;scene.cycles.samples=32
scene['version']='G1_006';scene['quality_status']='public interior detail revision, not G1 completion'
scene.camera=bpy.data.objects['BE_QA_ENTRY']
bpy.ops.file.make_paths_relative();native=ROOT/'native/G1_006_bellevue_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/bellevue_working.json').read_text());record.update(version='G1_006',native=str(native),new_objects=len(building.objects))
(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(record,indent=2))
print(json.dumps({'version':'G1_006','objects':len(building.objects),'native':str(native),'surveys_moved':False,'assumptions':'Equipment details and exact interior positions inferred from photographed use; roof/building envelope unchanged'}))
