"""Independent geometric checks of the saved public facility, not task scoring."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version'].startswith('G1_018')
bpy.context.view_layer.update();root=bpy.data.objects['F59_ROOT'];basin=bpy.data.objects['F59_GRANITE_BASIN'];ground=bpy.data.objects['BS_ASPHALT'];report={'version':s['version'],'acceptance':False}
report['dimensions']={'x':max(v.co.x for v in basin.data.vertices)-min(v.co.x for v in basin.data.vertices),'y':max(v.co.y for v in basin.data.vertices)-min(v.co.y for v in basin.data.vertices),'rim_height':max(v.co.z for v in basin.data.vertices)}
assert all(abs(report['dimensions'][k]-4)<.001 for k in ['x','y']) and abs(report['dimensions']['rim_height']-.78)<.001
contacts=[]
for name,support in [('F59_GRANITE_PEDESTAL',ground)]+[(f'F59_{i}_CAST_FOOT',basin) for i in range(3)]:
    ob=bpy.data.objects[name];points=[ob.matrix_world@v.co for v in ob.data.vertices];low=min(p.z for p in points);bottom=[p for p in points if p.z<low+.0001];gaps=[]
    for p in bottom:
        inv=support.matrix_world.inverted();hit,q,n,f=support.ray_cast(inv@Vector((p.x,p.y,p.z+1)),inv.to_3x3()@Vector((0,0,-1)));assert hit,(name,'no physical support')
        gaps.append(p.z-(support.matrix_world@q).z)
    assert max(gaps)<.003,(name,'floating',max(gaps));contacts.append({'name':name,'support':support.name,'min_gap':min(gaps),'max_gap':max(gaps),'sample_points':len(bottom)})
report['contacts']=contacts
mesh=bpy.data.objects['F59_WATER_SURFACE'];bm=bmesh.new();bm.from_mesh(mesh.data);report['water']={'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_m3':bm.calc_volume(signed=True)};bm.free()
assert report['water']['nonmanifold_edges']==0 and report['water']['volume_m3']>0
casts=[]
for i in range(3):
    ob=bpy.data.objects[f'F59_{i}_FISH_CAST'];hit,p,n,f=ob.ray_cast(Vector((0,0,1)),Vector((0,0,-1)));assert hit and n.z>.7;casts.append({'name':ob.name,'top_z':p.z,'normal_z':n.z})
report['casts']=casts
strainer=bpy.data.objects['F59_OVERFLOW_PERFORATED_SHELL'];hole_rays=0;solid_rays=0
for j in range(3):
    for k in range(18):
        a=(k+.5)*2*math.pi/18;z=.704+(j+.5)*.054/3
        hit,_,_,_=strainer.ray_cast(Vector((.09*math.cos(a),.09*math.sin(a),z)),Vector((-math.cos(a),-math.sin(a),0)),distance=.18)
        assert not hit,('Blocked strainer hole',j,k);hole_rays+=1
        a=k*2*math.pi/18
        hit,_,_,_=strainer.ray_cast(Vector((.09*math.cos(a),.09*math.sin(a),z)),Vector((-math.cos(a),-math.sin(a),0)),distance=.04)
        assert hit,('Missing metal between holes',j,k);solid_rays+=1
report['strainer']={'open_hole_rays':hole_rays,'solid_web_rays':solid_rays}
if s['version']=='G1_018r3':
    cap=bpy.data.objects['F59_OVERFLOW_CAP'].evaluated_get(bpy.context.evaluated_depsgraph_get());opened=0
    for radius,count in [(.022,8),(.044,14)]:
        for i in range(count):
            a=2*math.pi*i/count;hit,_,_,_=cap.ray_cast(Vector((radius*math.cos(a),radius*math.sin(a),.8)),Vector((0,0,-1)),distance=.1)
            assert not hit,('Top drill hole blocked',radius,i);opened+=1
    hit,p,n,_=cap.ray_cast(Vector((0,0,.8)),Vector((0,0,-1)),distance=.1);assert hit and n.z>.99
    report['strainer']['top_open_holes']=opened;report['strainer']['top_centre_normal_z']=n.z
if 'F59_OVERFLOW_RISER' in bpy.data.objects:
    riser=bpy.data.objects['F59_OVERFLOW_RISER'];collar=bpy.data.objects['F59_OVERFLOW_PERFORATED_SHELL']
    top=max((riser.matrix_world@v.co).z for v in riser.data.vertices)
    bottom=min((collar.matrix_world@v.co).z for v in collar.data.vertices)
    foot=min((riser.matrix_world@v.co).z for v in riser.data.vertices)
    hole=(collar.matrix_world@Vector((.061,0,.713))).z
    level=root.location.z+.707
    assert top>bottom and foot<root.location.z+.3085 and hole<level
    report['overflow_connection']={'collar_riser_overlap_m':top-bottom,'riser_foot_below_basin_floor_m':root.location.z+.308-foot,'first_hole_below_water_m':level-hole}
report['original_photo_count']=len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects);assert report['original_photo_count']==2039
report['missing_unpacked_images']=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not Path(bpy.path.abspath(i.filepath)).exists()];assert not report['missing_unpacked_images']
out=R/'evidence'/s['version']/'facility_geometry_check.json';out.write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
