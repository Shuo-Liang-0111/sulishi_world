"""Use the actual whole-casting close-up to remove primitive-like finishing."""
import bpy,bmesh,json,ast,math
import numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/fountain59';scene=bpy.context.scene;assert scene['version']=='G1_018r2'
d=json.loads((D/'input.json').read_text());root=bpy.data.objects['F59_ROOT'];collection=bpy.data.collections['27_BELLEVUE_FOUNTAIN_59']
tree=ast.parse((R/'tools/blender_build_fountain59.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','unit','add_tube']],type_ignores=[]),'fountain_cast_helpers','exec'))
silver=bpy.data.materials['F59 | weathered chromium silver'];polished=bpy.data.materials['F59 | worn polished outlet'];changes=[]

def replace(name,verts,faces,mat):
    old=bpy.data.objects[name];temp=mesh('TEMP_'+name,verts,faces,mat,parent=old.parent)
    old.data=temp.data;bpy.data.objects.remove(temp,do_unlink=True)
    for mod in list(old.modifiers):old.modifiers.remove(mod)
    bm=bmesh.new();bm.from_mesh(old.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    zero=[f for f in bm.faces if f.calc_area()<1e-14]
    if zero:bmesh.ops.delete(bm,geom=zero,context='FACES_ONLY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(old.data);bm.free()
    for face in old.data.polygons:face.use_smooth=True
    old.data.update();return old

def patch(v,f,fun,nu=33,nv=11,thickness=.002):
    start=len(v);size=nu*nv
    for sign in [-1,1]:
        for j in range(nv):
            t=j/(nv-1)
            for i in range(nu):
                u=i/(nu-1);p=fun(u,t);du=fun(u+.0001,t)-fun(u-.0001,t);dt=fun(u,t+.0001)-fun(u,t-.0001)
                n=unit(np.cross(du,dt));v.append(p+sign*thickness*.5*n)
    for j in range(nv-1):
        for i in range(nu-1):
            a=start+j*nu+i;f.append((a,a+1,a+nu+1,a+nu));f.append((a+size,a+size+nu,a+size+nu+1,a+size+1))
    edge=list(range(nu))+[j*nu+nu-1 for j in range(1,nv)]+[(nv-1)*nu+i for i in reversed(range(nu-1))]+[j*nu for j in reversed(range(1,nv-1))]
    for a,b in zip(edge,edge[1:]+edge[:1]):f.append((start+a,start+a+size,start+b+size,start+b))

def tail(u,t):
    k=2*u-1;a=k*.80;length=.044+.066*abs(k)**.75
    return np.array([.251+t*length*math.cos(a),.003*math.sin(math.pi*t)*math.sin(k*2.7),.086+.008*k*(1-t)+t*length*math.sin(a)])
def pectoral(u,t,sign):
    arch=math.sin(math.pi*u)
    return np.array([-.160+.115*u+.010*arch*t,sign*(.047+.051*arch*t),.052-.043*arch*t+.004*math.sin(math.pi*t)])
def dorsal(u,t):
    arch=max(0.,math.sin(math.pi*u))**.65
    return np.array([.073+.105*u,.002*math.sin(math.pi*t)*arch,.118-.025*u+.053*arch*t])

for number in range(3):
    child=bpy.data.objects[f'F59_{number}_CHILD_CAST'];flat=sum(not p.use_smooth for p in child.data.polygons)
    for face in child.data.polygons:face.use_smooth=True
    child['finish_repair']='Checked smooth normals after voxel remesh; all were already smooth. Existing anatomy remains approximate; this is not a proven shading repair.'
    changes.append({'object':child.name,'flat_polygons_before':flat,'smooth_polygons_after':len(child.data.polygons)})
    v=[];f=[];patch(v,f,tail)
    for sign in [-1,1]:patch(v,f,lambda u,t:pectoral(u,t,sign))
    replace(f'F59_{number}_CAST_FINS',v,f,silver)
    v=[];f=[];patch(v,f,dorsal,thickness=.0025);replace(f'F59_{number}_DORSAL_FIN',v,f,silver)
    v=[];f=[]
    for u in np.linspace(.08,.92,11):
        for sign in [-1,1]:
            points=[]
            for t in np.linspace(.13,.96,17):p=tail(u,t);p[1]+=sign*.0015;points.append(p)
            add_tube(v,f,points,.00040,6)
    for sign in [-1,1]:
        for u in np.linspace(.1,.9,9):
            points=[]
            for t in np.linspace(.15,.94,15):p=pectoral(u,t,sign);p[2]+=.0015;points.append(p)
            add_tube(v,f,points,.00040,6)
    replace(f'F59_{number}_FIN_FLUTING',v,f,polished)
    v=[];f=[]
    for sign in [-1,1]:
        for u in np.linspace(.1,.9,9):
            points=[]
            for t in np.linspace(.1,.92,15):p=dorsal(u,t);p[1]+=sign*.0016;points.append(p)
            add_tube(v,f,points,.00040,6)
    replace(f'F59_{number}_DORSAL_FLUTING',v,f,polished)
    # Replace concentric ridges with shallow swept hair waves seen in reference.
    v=[];f=[]
    for row,y in enumerate(np.linspace(-.022,.022,10)):
        extent=.0305*math.sqrt(max(0,1-(y/.027)**2));points=[]
        for t in np.linspace(-.95,.94,49):
            x=-.063+extent*t;yy=y+.00085*math.sin(9*t+row*.3);val=max(.015,1-((x+.063)/.032)**2-(yy/.028)**2)
            z=.251+.0365*math.sqrt(val);points.append((x,yy,z))
        add_tube(v,f,points,.00070,7)
    replace(f'F59_{number}_HAIR_CROWN_RELIEF',v,f,silver)
    v=[];f=[]
    for sign in [-1,1]:
        points=[(-.089+.002*math.sin(t),sign*(.010+.004*math.cos(t)),.263+.0015*math.sin(t)) for t in np.linspace(0,math.pi,13)]
        add_tube(v,f,points,.0006,6)
    for k in range(4):
        add_tube(v,f,[(-.112,-.034+k*.003,.211),(-.114,-.034+k*.003,.221),(-.109,-.034+k*.003,.224)],.00125,8)
        add_tube(v,f,[(.003+k*.003,.035,.154),(.004+k*.003,.037,.147),(.010+k*.003,.034,.145)],.00125,8)
    replace(f'F59_{number}_CAST_FINE_RELIEF',v,f,silver)
for ob in collection.objects:
    if ob.type=='MESH' and silver in ob.data.materials[:]:
        uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='cast_surface_metre_coordinates')
        for loop in ob.data.loops:
            p=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x/.16,(p.y+p.z*.63)/.16)

# Actual overflow close-up exposed radial shading artifacts on the Boolean cap.
# An explicitly triangulated flat perforated sheet has stable planar normals.
cap_data=json.loads((D/'overflow_cap_mesh.json').read_text())
cap=replace('F59_OVERFLOW_CAP',cap_data['vertices'],cap_data['faces'],polished)
for p in cap.data.polygons:p.use_smooth=False
bevel=cap.modifiers.new('Rounded drilled hole lips','BEVEL');bevel.width=.00025;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.4
satin=polished.copy();satin.name='F59 | satin overflow stainless proxy';satin.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.34
satin['basis']='Satin sheet finish inferred from actual overflow photo; alloy not identified.'
for name in ['F59_OVERFLOW_CAP','F59_OVERFLOW_ROLLED_TOP','F59_OVERFLOW_PERFORATED_SHELL','F59_OVERFLOW_RISER','F59_DRAIN_FLANGE']:
    bpy.data.objects[name].data.materials[0]=satin

scene['version']='G1_018r3';scene.camera=bpy.data.objects['BE_QA_FOUNTAIN_RIM'];bpy.context.view_layer.update()
E=R/'evidence/G1_018r3';E.mkdir(exist_ok=True);(E/'casting_finish.json').write_text(json.dumps({'version':scene['version'],'normal_changes':changes,'changes':['Curved thick fins with connected rims replace flat polygons','Swept hair ridges replace concentric rings','Whole actual rendering required; sculpture remains inferred approximation'],'visual_accepted':False},indent=2))
native=R/'native/G1_018r3_fountain_cast_finish_working.blend';bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=scene['version'],native=str(native),accepted=False,not_published=True,next='Inspect casting closeup and reverse full view, retain fountain base and water checks, then matching runtime export.');(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
print(json.dumps({'version':scene['version'],'normal_changes':changes,'saved':str(native)}))
