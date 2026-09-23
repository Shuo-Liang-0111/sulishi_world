"""G1_005: source-constrained Bellevue structure and first public interior pass.

Run via the Blender MCP client. Keeps the complete original source collection intact.
Exact geometry and inferred fine details are tagged separately; this is not final acceptance.
"""
import bpy,bmesh,json,math
from mathutils import Vector
from pathlib import Path
import numpy as np

ROOT=Path('F:/MyWorld/ZurichWorld'); VERSION='G1_005'
data=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
scene=bpy.context.scene
assert scene.get('version') in ['G1_004r2',VERSION], 'Open current source checkpoint first.'
assert bpy.data.materials.get('asphalt_03'), 'Preserve the downloaded CC0 material before continuing.'
C=np.array(data['center_lv95'])-np.array(data['origin'][:2]);FLOOR=data['ground_fit']['ground_plane_z_ln02'][2]-400
angle=math.radians(-102);front=np.array([math.cos(angle),math.sin(angle)]);right=np.array([-front[1],front[0]])

def col(name):
    c=bpy.data.collections.get(name)
    if c is None:c=bpy.data.collections.new(name);scene.collection.children.link(c)
    return c

building=col('10_BELLEVUE_RECONSTRUCTION')
for o in list(building.objects):bpy.data.objects.remove(o,do_unlink=True)
background=col('04_RETAINED_PHOTO_CONTEXT')
for o in list(background.objects):bpy.data.objects.remove(o,do_unlink=True)
building['status']='first structural reconstruction; details and natural use not yet accepted'
building['egid']=2376968

def P(u,v,z):
    xy=C+right*u+front*v;return (float(xy[0]),float(xy[1]),FLOOR+z)

def material(name,color,rough=.65,metal=0,trans=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    bs.inputs['Transmission Weight'].default_value=trans;bs.inputs['IOR'].default_value=1.47
    return m

plaster=material('BE | warm pale painted soffit',(.64,.63,.59),.84)
roofmat=material('BE | folded grey metal roof',(.32,.35,.35),.52,.65)
aluminium=material('BE | satin anodised aluminium',(.43,.46,.45),.29,.82)
darkmetal=material('BE | dark structural metal',(.048,.055,.054),.38,.75)
glass=material('BE | clear curved 12mm glass',(.93,.98,.965),.075,0,1)
wood=material('BE | warm wood',(.23,.11,.041),.46)
woodend=material('BE | wood edge',(.125,.065,.026),.55)
red=material('BE | red woven chair',(.31,.016,.028),.48)
countermetal=material('BE | stainless counter',(.39,.40,.385),.23,.91)
dark=material('BE | dark counter plinth',(.032,.034,.032),.72)
stone=material('BE | grey threshold stone',(.34,.35,.33),.77)
asphalt=bpy.data.materials['asphalt_03'];asphalt.use_fake_user=True
for node in asphalt.node_tree.nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.4
    if node.type=='OUTPUT_MATERIAL':
        for link in list(node.inputs['Displacement'].links):asphalt.node_tree.links.remove(link)
asphalt['world_texture_size_m']=2.05
asphalt['source_url']='https://polyhaven.com/a/asphalt_03';asphalt['license']='CC0'

def mesh(name,verts,faces,mat,smooth=False,basis='photo-informed reconstruction; dimensions inferred'):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);building.objects.link(ob);me.materials.append(mat)
    if smooth:
        for f in me.polygons:f.use_smooth=True
    ob['kind']='reconstructed_architecture';ob['place']='Bellevue_Rondell';ob['egid']=2376968
    ob['evidence_basis']=basis;ob['quality_status']='working_not_accepted'
    return ob

def triangles(name,tt,mat,basis):
    vv=np.asarray(tt).reshape(-1,3);return mesh(name,vv.tolist(),np.arange(len(vv)).reshape(-1,3).tolist(),mat,basis=basis)

def box(name,center,dims,mat,bevel=.008):
    u,v,z=center;du,dv,dz=np.array(dims)/2
    vv=[P(u+x*du,v+y*dv,z+k*dz) for x,y,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    ob=mesh(name,vv,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    if bevel:
        m=ob.modifiers.new('Physical edge radius','BEVEL');m.width=bevel;m.segments=2
        n=ob.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return ob

def lathe(name,profile,mat,center=(0,0),steps=80,world_center=None):
    vv=[]
    for r,z in profile:
        for i in range(steps):
            t=2*math.pi*i/steps
            if world_center:vv.append((world_center[0]+r*math.cos(t),world_center[1]+r*math.sin(t),z))
            else:vv.append(P(center[0]+r*math.cos(t),center[1]+r*math.sin(t),z))
    ff=[]
    for j in range(len(profile)-1):
        for i in range(steps):
            ni=(i+1)%steps;ff.append((j*steps+i,j*steps+ni,(j+1)*steps+ni,(j+1)*steps+i))
    return mesh(name,vv,ff,mat,True)

def arc(name,r0,r1,z0,z1,a0,a1,mat,center=(0,0),step=2):
    steps=max(2,math.ceil(abs(a1-a0)/step));vv=[]
    for z,r in [(z0,r0),(z0,r1),(z1,r1),(z1,r0)]:
        for a in np.linspace(math.radians(a0),math.radians(a1),steps+1):vv.append(P(center[0]+r*math.sin(a),center[1]+r*math.cos(a),z))
    n=steps+1;ff=[]
    for row in range(4):
        nxt=(row+1)%4
        for i in range(steps):ff.append((row*n+i,row*n+i+1,nxt*n+i+1,nxt*n+i))
    ff.extend([(0,n,2*n,3*n),(n-1,4*n-1,3*n-1,2*n-1)])
    return mesh(name,vv,ff,mat)

def tube(name,points,r,mat,closed=False):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=2
    curve.bevel_depth=r;curve.bevel_resolution=2
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for a,p in zip(spline.points,points):a.co=(*p,1)
    spline.use_cyclic_u=closed
    ob=bpy.data.objects.new(name,curve);building.objects.link(ob);curve.materials.append(mat)
    ob['place']='Bellevue_Rondell';ob['evidence_basis']='photo-informed fixture reconstruction';return ob

# Surveyed canopy and central roof are preserved at their source coordinates.
for part in data['source_parts']:
    mat=roofmat if part['type']=='RoofSurface' else plaster
    ob=triangles('BE_SOURCE_'+part['id'],part['triangles'],mat,'unchanged source coordinates: '+part['id'])
    if part['type']=='GroundSurface':
        for p in ob.data.polygons:p.use_smooth=True

ground=triangles('BE_PUBLIC_PLATFORM',data['ground_surface_triangles'],asphalt,data['ground_surface_basis'])
ground['collision_role']='walkable_surface';ground['source_id']=data['ground_fit']['island_id']
uv=ground.data.uv_layers.new(name='real_scale_2.05m')
for loop in ground.data.loops:
    v=ground.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=((v.x-C[0])/2.05,(v.y-C[1])/2.05)

# Three column heads come from distinct circular patches in the surveyed underside.
for i,support in enumerate(data['supports']):
    xy=np.array(support['center_lv95'])-np.array(data['origin'][:2]);top=support['cap_z_ln02']-400
    gf=data['ground_fit']['ground_plane_z_ln02'];delta=np.array(support['center_lv95'])-np.array(data['center_lv95'])
    floor=gf[0]*delta[0]+gf[1]*delta[1]+gf[2]-400
    cap_r=math.sqrt(support['cap_area_m2']/math.pi)
    shaft=lathe('BE_COLUMN_%02d_STEEL'%i,[(.19,floor),(.19,top-1.1),(.24,top-.97)],aluminium,world_center=xy.tolist())
    shaft['source_position']=json.dumps(support);shaft['collision_role']='solid'
    profile=[(.19,top-1.12),(.22,top-.91),(.32,top-.66),(.50,top-.42),(.78,top-.22),(1.08,top-.08),(cap_r,top)]
    lathe('BE_COLUMN_%02d_FLARE'%i,profile,plaster,world_center=xy.tolist())
    lathe('BE_COLUMN_%02d_FOOT'%i,[(.23,floor),(.23,floor+.07),(.19,floor+.09)],aluminium,world_center=xy.tolist())

# Photographs resolve the low glazed ring below the higher surveyed roof.
lathe('BE_SCULPTED_SOFFIT_COLLAR',[(7.015,2.88),(7.06,3.10),(7.18,3.38),(7.38,3.64),(7.76,3.84),(8.30,3.99),(9.05,4.02)],plaster)
arc('BE_UPPER_FRAME',6.955,7.065,2.73,2.88,0,360,aluminium)
arc('BE_PUBLIC_THRESHOLD',6.86,7.20,-.005,.012,-20,20,stone)
arc('BE_BOTTOM_FRAME',6.965,7.025,.02,.12,20,340,aluminium)
for start in range(20,340,10):
    arc('BE_FIXED_GLASS_%03d'%start,6.985,6.997,.115,2.755,start+.18,start+9.82,glass)
for a in range(20,341,10):
    t=math.radians(a);u,v=7*math.sin(t),7*math.cos(t)
    lathe('BE_MULLION_%03d'%a,[(.031,.03),(.031,2.79)],aluminium,(u,v),steps=16)

# Curved sliding entrance: door hardware is an explicit reconstruction inference.
for side,a0,a1 in [('L',-20,0),('R',0,20)]:
    pivot=bpy.data.objects.new('BE_ENTRANCE_'+side,None);building.objects.link(pivot);pivot.location=(C[0],C[1],FLOOR)
    pivot['interaction_role']='curved_sliding_door_leaf';pivot['closed_rotation_z']=0.0
    pivot['open_rotation_z']=math.radians(20 if side=='L' else -20)
    pivot['state']='open';pivot['mechanism_basis']='inferred curved sliding entrance; sales windows elsewhere are separately documented vertical sliding'
    parts=[arc('BE_DOOR_GLASS_'+side,7.035,7.047,.09,2.75,a0+.18,a1-.18,glass),
           arc('BE_DOOR_TOP_'+side,7.005,7.075,2.72,2.79,a0,a1,aluminium),
           arc('BE_DOOR_BASE_'+side,7.005,7.075,.045,.13,a0,a1,aluminium)]
    for a in [a0,a1]:
        t=math.radians(a);parts.append(lathe('BE_DOOR_EDGE_'+side+'_'+str(a),[(.035,.06),(.035,2.77)],aluminium,(7.04*math.sin(t),7.04*math.cos(t)),20))
    for part in parts:
        part.parent=pivot;part.matrix_parent_inverse=pivot.matrix_world.inverted()
    pivot.rotation_euler.z=pivot['open_rotation_z']

# Interior: curved stainless bar, visible wood partition and windrose ceiling.
lathe('BE_CENTRAL_COLUMN',[(.20,0),(.20,2.96)],darkmetal)
for z0,z1,r0,r1,mat,name in [(.08,.94,3.02,3.43,dark,'PLINTH'),(.21,1.05,3.16,3.51,countermetal,'FACE'),(1.035,1.09,2.95,3.69,countermetal,'TOP')]:
    arc('BE_BAR_'+name,r0,r1,z0,z1,-105,105,mat,step=2)
box('BE_SERVICE_PARTITION',(0,-2.10,1.43),(12.6,.17,2.86),woodend)
for i in range(59):box('BE_WOOD_SLAT_%02d'%i,(0,-1.998,.18+i*.042),(12.5,.055,.033),wood,.003)

ceilingmats=[]
for i,color in enumerate([(.62,.71,.70),(.72,.76,.69),(.61,.69,.73),(.73,.73,.67)]):
    mat=material('BE | luminous glass %d'%i,color,.5)
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=.4
    ceilingmats.append(mat)
for ring,(r0,r1) in enumerate([(.33,1.05),(1.05,2.05),(2.05,3.20)]):
    for sector in range(8):arc('BE_WINDROSE_%d_%d'%(ring,sector),r0,r1,2.925,2.952,sector*45+.25,(sector+1)*45-.25,ceilingmats[(ring+sector)%4],step=2)
for r in [.34,1.05,2.05,3.20]:arc('BE_WINDROSE_RING_%.2f'%r,r-.027,r+.027,2.902,2.928,0,360,darkmetal)
for a in range(0,360,45):
    t=math.radians(a);tube('BE_WINDROSE_RADIAL_%d'%a,[P(.34*math.sin(t),.34*math.cos(t),2.913),P(3.20*math.sin(t),3.20*math.cos(t),2.913)],.023,darkmetal)
arc('BE_INTERIOR_CEILING',3.23,6.95,2.96,3.025,0,360,woodend)

# A few referenced daily-use fixtures; detailed equipment pass follows geometry review.
box('BE_ESPRESSO_BODY',(-1.15,.4,1.40),(.78,.56,.60),countermetal,.035)
box('BE_ESPRESSO_DRIP_TRAY',(-1.15,.75,1.17),(.85,.26,.045),darkmetal)
for u in [-1.39,-.91]:
    tube('BE_ESPRESSO_GROUP_'+str(u),[P(u,.65,1.48),P(u,.78,1.48),P(u,.81,1.37)],.045,aluminium)
box('BE_DISPLAY_CASE_BASE',(1.0,2.7,1.12),(1.20,.55,.075),darkmetal)
for name,c,d in [('front',(1,3.0,1.36),(1.2,.012,.44)),('top',(1,2.73,1.59),(1.2,.56,.012)),('left',(.394,2.73,1.36),(.012,.56,.44)),('right',(1.606,2.73,1.36),(.012,.56,.44))]:box('BE_DISPLAY_GLASS_'+name,c,d,glass,0)

def table(u,v,index):
    profile=[(.105,0),(.105,.08)]
    for z in np.arange(.08,1.035,.035):
        r=.09+.28*(z/1.035)**2.5;profile.extend([(r,z),(r,z+.029),(r-.006,z+.034)])
    profile.extend([(.40,1.04),(.44,1.065),(.44,1.09),(.015,1.09)])
    lathe('BE_HIGH_TABLE_%02d'%index,profile,wood,(u,v),64)
    lathe('BE_TABLE_FOOT_%02d'%index,[(.14,.005),(.14,.05),(.105,.065)],aluminium,(u,v),48)

def chair(u,v,index):
    for x,y in [(-.23,-.23),(.23,-.23),(-.23,.23),(.23,.23)]:
        tube('BE_CHAIR_%02d_LEG_%s_%s'%(index,x,y),[P(u+x*1.18,v+y*1.18,.015),P(u+x*.83,v+y*.83,.77)],.012,darkmetal)
    tube('BE_CHAIR_%02d_FOOTREST'%index,[P(u-.24,v-.24,.34),P(u+.24,v-.24,.34),P(u+.24,v+.24,.34),P(u-.24,v+.24,.34)],.011,darkmetal,True)
    for axis in range(2):
        for j in range(13):
            s=-.245+j*.0408
            points=[P(u+s,v-.27,.78),P(u+s,v+.27,.78)] if axis==0 else [P(u-.27,v+s,.787),P(u+.27,v+s,.787)]
            tube('BE_CHAIR_%02d_WEAVE_%d_%d'%(index,axis,j),points,.006,red)
    outline=[P(u-.28,v+.22,.77),P(u-.30,v+.31,1.11),P(u-.23,v+.35,1.19),P(u+.23,v+.35,1.19),P(u+.30,v+.31,1.11),P(u+.28,v+.22,.77)]
    tube('BE_CHAIR_%02d_BACK_FRAME'%index,outline,.009,red)
    for j in range(9):
        z=.82+j*.04;tube('BE_CHAIR_%02d_BACK_WEAVE_%d'%(index,j),[P(u-.28,v+.26+(z-.82)*.2,z),P(u+.28,v+.26+(z-.82)*.2,z)],.006,red)

locations=[(-5.0,7.0),(5.0,7.0),(-8.2,3.8),(8.2,3.8),(-8.7,.7),(8.7,.7)]
for i,(u,v) in enumerate(locations):
    table(u,v,i);chair(u-.7,v+.1,i*2);chair(u+.7,v+.1,i*2+1)

# Retained source context: duplicate only edited meshes, preserve all original objects.
cut=json.loads((ROOT/'derived/bellevue/photo_cut.json').read_text());overrides={x['node']:x for x in cut['overrides']}
source=bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
for original in source.objects:
    item=overrides.get(str(original['source_node']))
    if item and not item['vertices']:continue
    ob=original.copy();ob.name='CTX_'+original.name;background.objects.link(ob)
    if item:
        vv=item['vertices'];me=bpy.data.meshes.new(ob.name);me.from_pydata(vv,[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
        layer=me.uv_layers.new(name='I3S_source_V_flipped_for_Blender');uv=np.asarray(item['uv_source_v_unflipped']);uv[:,1]=1-uv[:,1]
        layer.data.foreach_set('uv',uv.ravel());me.materials.append(original.data.materials[0]);ob.data=me
        ob['source_edit']='Exact plan-mask removal inside reconstructed Bellevue island; source original retained.'
    ob['kind']='retained_source_context';ob.hide_render=False;ob.hide_set(False)
source.hide_render=True;source.hide_viewport=True
for name in ['01_SURVEY_TERRAIN_REFERENCE','02_SURVEY_LOD2_REFERENCE']:
    bpy.data.collections[name].hide_render=True;bpy.data.collections[name].hide_viewport=True

def camera(name,eye,target,lens=36):
    ob=bpy.data.objects.get(name)
    if ob is None:
        d=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,d);col('90_REVIEW_CAMERAS').objects.link(ob)
    ob.location=P(*eye);ob.rotation_euler=(Vector(P(*target))-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens
    ob.data.clip_start=.08;ob.data.clip_end=5000;return ob

camera('BE_QA_FRONT',(0,32,1.65),(0,0,2.0),34)
camera('BE_QA_ENTRY',(0,12,1.65),(0,0,1.6),30)
camera('BE_QA_SIDE',(-25,13,1.65),(0,0,2.2),34)
camera('BE_QA_REAR',(0,-27,1.65),(0,0,2.2),34)
camera('BE_QA_INTERIOR',(0,5.65,1.65),(0,0,1.85),23)
camera('BE_QA_STRUCTURE',(28,34,24),(0,0,1.5),44)
scene.camera=bpy.data.objects['BE_QA_ENTRY']
scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.8
scene['version']=VERSION;scene['quality_status']='Bellevue first structural reconstruction; G1 incomplete'
scene['bellevue_datum_note']='Road and platform differ. Local platform fit 408.631m LN02; door threshold inferred, not measured.'
scene.blendermcp_use_polyhaven=True
bpy.ops.file.make_paths_relative()
native=ROOT/f'native/{VERSION}_bellevue_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
receipt={'version':VERSION,'native':str(native),'new_objects':len(building.objects),
         'source_context_objects':len(background.objects),'source_originals':len(source.objects),
         'source_cut_nodes':len(overrides),'platform_z_ln02':FLOOR+400,
         'status':'working_not_accepted','next':'multi-angle rendering, source comparison, join and export checks'}
(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
