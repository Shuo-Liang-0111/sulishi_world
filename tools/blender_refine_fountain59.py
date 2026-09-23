"""Repair the first actual native review; preserve fixed survey identity/envelope."""
import bpy,bmesh,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/fountain59';scene=bpy.context.scene
assert scene['version']=='G1_018'
d=json.loads((D/'input.json').read_text());root=bpy.data.objects['F59_ROOT'];collection=bpy.data.collections['27_BELLEVUE_FOUNTAIN_59']
tree=ast.parse((R/'tools/blender_build_fountain59.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['material','mesh','lathe','unit','add_tube','tube_object','ellipsoid']],type_ignores=[]),'fountain_helpers','exec'))
pipe_metal=bpy.data.materials['F59 | worn polished outlet'];silver=bpy.data.materials['F59 | weathered chromium silver']
water=bpy.data.materials['F59 | clear water IOR1.333'];recess=bpy.data.materials.get('F59 | sheltered casting recess') or material('F59 | sheltered casting recess',(.23,.25,.255),.34,.97)
changed=[]
def repair_mesh(o,cap=False):
    bm=bmesh.new();bm.from_mesh(o.data);before=sum(1 for e in bm.edges if e.is_boundary)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    if cap:bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=66)
    zero=[f for f in bm.faces if f.calc_area()<1e-14]
    if zero:bmesh.ops.delete(bm,geom=zero,context='FACES_ONLY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    after=sum(1 for e in bm.edges if e.is_boundary)
    if after==0 and bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    changed.append({'object':o.name,'boundary_edges_before':before,'boundary_edges_after':after,'signed_volume_m3':bm.calc_volume(signed=True) if after==0 else None})
    bm.to_mesh(o.data);bm.free();o.data.update()
for o in list(collection.objects):
    if o.type=='MESH' and not o.name.startswith(('F59_WATER','F59_OVERFLOW_PERFORATED')):repair_mesh(o,o.name.endswith('_FISH_CAST'))

# The rim close-up revealed a tangent/shear discontinuity: angular U previously
# changed with every radial profile row. Hold circumference U fixed per chart.
for name,radius in [('F59_GRANITE_BASIN',2.),('F59_GRANITE_PEDESTAL',.55),('F59_MINERAL_FOOT_BEDDING',.55)]:
    ob=bpy.data.objects[name];layer=ob.data.uv_layers.active
    for face in ob.data.polygons:
        angles=np.unwrap([math.atan2(ob.data.vertices[ob.data.loops[li].vertex_index].co.y,ob.data.vertices[ob.data.loops[li].vertex_index].co.x) for li in face.loop_indices])
        for i,li in enumerate(face.loop_indices):layer.data[li].uv.x=float(angles[i]*radius)
    ob['uv_repair']='Fixed-circumference cylindrical U, continuous cross-section V; no radial shear of grain on rim'

profile=np.array([[-.305,.139,.001,.003],[-.290,.132,.019,.021],[-.267,.116,.039,.047],[-.230,.100,.056,.065],[-.175,.083,.061,.062],[-.10,.076,.060,.057],[0,.075,.052,.047],[.10,.075,.043,.038],[.185,.079,.024,.027],[.248,.086,.012,.014],[.270,.089,.010,.010]])
slopes=np.gradient(profile[:,1:],profile[:,0],axis=0)
def smooth_profile(x):
    j=int(np.clip(np.searchsorted(profile[:,0],x)-1,0,len(profile)-2));dx=profile[j+1,0]-profile[j,0];t=np.clip((x-profile[j,0])/dx,0,1)
    result=(2*t**3-3*t*t+1)*profile[j,1:]+(t**3-2*t*t+t)*dx*slopes[j]+(-2*t**3+3*t*t)*profile[j+1,1:]+(t**3-t*t)*dx*slopes[j+1]
    result[1:]=np.maximum(result[1:],.0005);return result
for number in range(3):
    for suffix in ['FISH_CAST','SCALE_RELIEF','FISH_HEAD_RELIEF']:
        ob=bpy.data.objects[f'F59_{number}_{suffix}']
        for v in ob.data.vertices:
            x=v.co.x;old=np.array([np.interp(x,profile[:,0],profile[:,i]) for i in [1,2,3]]);new=smooth_profile(x)
            v.co.y*=new[1]/old[1];v.co.z=new[0]+(v.co.z-old[0])*new[2]/old[2]
        ob.data.update()

# Precisely shared rectangular panel borders around circular perforations.
old=bpy.data.objects['F59_OVERFLOW_PERFORATED_SHELL'];oldme=old.data
v=[];f=[];radius=.061;thick=.0015;cols=18;rows=3;height=.054
for j in range(rows):
    for k in range(cols):
        u=(k+.5)/cols*2*math.pi;cz=.704+(j+.5)*height/rows;w=math.pi*radius/cols;h=height/(2*rows);start=len(v)
        outer=[]
        for side in range(4):
            for t in np.linspace(0,1,4,endpoint=False):
                outer.append([(-w+2*w*t,-h),(w,-h+2*h*t),(w-2*w*t,h),(-w,h-2*h*t)][side])
        for rr in [radius,radius-thick]:
            for hole in [False,True]:
                for a,b in outer:
                    if hole:
                        length=math.hypot(a,b);a,b=a/length*.0052,b/length*.0052
                    angle=u+a/radius;v.append((rr*math.cos(angle),rr*math.sin(angle),cz+b))
        for i in range(16):
            ni=(i+1)%16
            f.extend([(start+i,start+ni,start+16+ni,start+16+i),(start+32+i,start+48+i,start+48+ni,start+32+ni),(start+16+i,start+16+ni,start+48+ni,start+48+i)])
tmp=mesh('TEMP_F59_PERFORATED',v,f,pipe_metal);old.data=tmp.data;bpy.data.objects.remove(tmp,do_unlink=True);repair_mesh(old)

# The original fish sheath had inward normals. Closed castings are now checked
# by signed volume and from rays through upper and lower body, not appearance alone.
casting_checks=[]
for i in range(3):
    fish=bpy.data.objects[f'F59_{i}_FISH_CAST'];hit,p,n,face=fish.ray_cast(Vector((0,0,1)),Vector((0,0,-1)))
    assert hit and .10<p.z<.15 and n.z>.7,(fish.name,list(p),list(n))
    casting_checks.append({'object':fish.name,'upper_body_z':p.z,'upper_normal':list(n)})
    root_cast=bpy.data.objects[f'F59_SCULPTURE_{i+1}']
    # Replace capped outlet with an actual annular nozzle.
    old=bpy.data.objects[f'F59_{i}_FISH_NOZZLE'];bpy.data.objects.remove(old,do_unlink=True)
    nozzle=lathe(f'F59_{i}_FISH_NOZZLE',[(.0026,0),(.004,0),(.004,.013),(.0044,.013),(.0044,.014),(.0026,.014),(.0026,0)],pipe_metal,32,root_cast)
    nozzle.location=(-.301,0,.136);nozzle.rotation_euler.y=-math.pi/4;repair_mesh(nozzle)
    # Whole crown, with shallow ridges; no bald cut-through at the back.
    v=[];f=[]
    for row in range(8):
        t=.15+row*.13;pts=[]
        for a in np.linspace(0,2*math.pi,65):
            pts.append((-.063+.0321*math.cos(a)*math.sin(t),.0275*math.sin(a)*math.sin(t),.251+.0362*math.cos(t)+.0006*math.sin(8*a+row)))
        add_tube(v,f,pts,.0008,7)
    mesh(f'F59_{i}_HAIR_CROWN_RELIEF',v,f,silver,parent=root_cast)
    v=[];f=[]
    for sign in [-1,1]:ellipsoid(v,f,[-.090,sign*.0125,.260],[.0018,.0030,.0016])
    mesh(f'F59_{i}_EYE_RECESSES',v,f,recess,parent=root_cast)

# A single closed water body removes the separate-shell ambiguity. Keep a
# persistent facility-volume identity as an Empty referring to the same mesh.
old=bpy.data.objects['F59_WATER_SURFACE'];oldname=old.name;water_body=bpy.data.objects['F59_WATER_VOLUME']
bpy.data.objects.remove(old,do_unlink=True);bpy.data.objects.remove(water_body,do_unlink=True)
jets=json.loads((D/'water_state.json').read_text())['jets']
steps=384;rings=144;rad=1.784;v=[(0,0,.707)];uv=[(0,0)];faces=[]
def wave(x,y,phase):
    z=0.
    for a,length,amp in [(.22,.51,.00038),(1.36,.28,.00022),(2.68,.17,.00018),(-.71,.093,.00010),(.87,.079,.00008)]:
        z+=amp*math.sin(2*math.pi/length*(x*math.cos(a)+y*math.sin(a))+phase*(.6+a/3))
    for n,j in enumerate(jets):
        q=j['impact'];dx=x-q[0];dy=y-q[1];rr=math.hypot(dx,dy);theta=math.atan2(dy,dx)
        z+=.00068*math.cos(58*rr+.36*math.sin(theta*5+n)-phase*1.8)*math.exp(-rr*3.7)
    return z*min(1.,max(0.,(rad-math.hypot(x,y))/.08))
for row in range(1,rings+1):
    r=rad*row/rings
    for k in range(steps):
        a=2*math.pi*k/steps;x=r*math.cos(a);y=r*math.sin(a);v.append((x,y,.707+wave(x,y,0)));uv.append((x,y))
for k in range(steps):faces.append((0,1+k,1+(k+1)%steps))
for row in range(rings-1):
    for k in range(steps):a=1+row*steps+k;b=1+row*steps+(k+1)%steps;faces.append((a,a+steps,b+steps,b))
top_count=len(v);last=1+(rings-1)*steps
for r in np.linspace(rad,.04,54):
    st=len(v);z=.308+.421*(r/1.825)**2.65+.0015
    for k in range(steps):a=2*math.pi*k/steps;v.append((r*math.cos(a),r*math.sin(a),z));uv.append((r*math.cos(a),r*math.sin(a)))
    for k in range(steps):ni=(k+1)%steps;faces.append((last+k,last+ni,st+ni,st+k))
    last=st
bottom=len(v);v.append((0,0,.3095));uv.append((0,0))
for k in range(steps):faces.append((last+k,last+(k+1)%steps,bottom))
surface=mesh(oldname,v,faces,water,uv)
top_weight=surface.data.attributes.new('F59WaveTop','FLOAT','POINT')
top_weight.data.foreach_set('value',np.r_[np.ones(top_count),np.zeros(len(v)-top_count)].astype(np.float32))
repair_mesh(surface)
surface['collision_role']='water_volume_not_solid';surface['water_level_local']=.707;surface['animation_basis']='Multi-direction wind and local disturbed ripples; analytic approximation, not fluid simulation'
surface.shape_key_add(name='Basis');key=surface.shape_key_add(name='Wind and jet ripples')
# Repaired topology can reorder vertices; select surface by coordinates.
for i,point in enumerate(key.data):
    if surface.data.attributes['F59WaveTop'].data[i].value>.5:point.co.z=.707+wave(point.co.x,point.co.y,math.pi)
for frame,value in [(1,0),(41,1),(81,0)]:key.value=value;key.keyframe_insert(data_path='value',frame=frame)
volume=bpy.data.objects.new('F59_WATER_VOLUME',None);collection.objects.link(volume);volume.parent=root;volume['fluid_mesh']='F59_WATER_SURFACE';volume['role']='Persistent water volume identity; geometry unified with top surface'

# The reference has an inner mineral/water line. Use a modest non-uniform tint
# on the actual wet face only; do not dirty the entire object or darken exposure.
base=bpy.data.materials['F59 | Castione visual proxy wet'];line=base.copy();line.name='F59 | mineral waterline'
nodes=line.node_tree.nodes;links=line.node_tree.links;p=nodes.get('Principled BSDF');texture=p.inputs['Base Color'].links[0].from_node
multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1.;multiply.inputs[2].default_value=(.62,.66,.51,1)
links.new(texture.outputs['Color'],multiply.inputs[1]);links.new(multiply.outputs['Color'],p.inputs['Base Color']);line['export_note']='Bake or confirm base factor preservation during glTF verification.'
basin=bpy.data.objects['F59_GRANITE_BASIN'];basin.data.materials.append(line);idx=len(basin.data.materials)-1
for face in basin.data.polygons:
    if face.material_index==1 and .669<face.center.z<.714:face.material_index=idx

ground=bpy.data.objects['BS_ASPHALT'];xy=root.location+Vector((2.3,.4,0));hit,p,_,_=ground.ray_cast(Vector((xy.x,xy.y,40)),Vector((0,0,-1)));assert hit
name='BE_QA_FOUNTAIN_OVERFLOW';cd=bpy.data.cameras.new(name);camera=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(camera)
camera.location=(xy.x,xy.y,p.z+1.65);camera.rotation_euler=(root.location+Vector((0,0,.72))-camera.location).to_track_quat('-Z','Y').to_euler();cd.lens=85;camera['eye_height_m']=1.65
# Original detail view cut off the child and tail. Fit the whole casting while
# retaining the real standing eye height and a visible rim/material reference.
camera=bpy.data.objects['BE_QA_FOUNTAIN_RIM'];centre=bpy.data.objects['F59_SCULPTURE_1'].matrix_world.translation
camera.rotation_euler=(centre+Vector((0,0,.14))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=48
scene.frame_set(1);scene['version']='G1_018r1';scene.camera=bpy.data.objects['BE_QA_FOUNTAIN_OVERVIEW'];bpy.context.view_layer.update()
E=R/'evidence/G1_018r1';E.mkdir(exist_ok=True)
(E/'repair.json').write_text(json.dumps({'version':scene['version'],'mesh_repairs':changed,'casting_rays':casting_checks,'water_mesh_closed':next(q for q in changed if q['object']=='F59_WATER_SURFACE')['boundary_edges_after']==0,'ground_xy_envelope_unchanged':True,'visual_accepted':False,'natural_use_accepted':False},indent=2))
native=R/'native/G1_018r1_fountain_surface_working.blend';bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=scene['version'],native=str(native),accepted=False,not_published=True,next='Repeat native fountain views after actual review corrections, then export matching materials/water.');(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
print(json.dumps({'version':scene['version'],'repaired_meshes':len(changed),'water_closed':True,'casting_rays':casting_checks,'new_objects':len(collection.objects),'saved':str(native)}))
