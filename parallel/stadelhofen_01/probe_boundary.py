"""Read actual saved author/retained meshes on opposite sides of the paving boundary.

No grade function is used as the opposing surface. This also runs on v01 with
its archived specification, independently of the v02 preparation files.
"""
import bpy, json, math, os, hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent

def mesh_bvh(objects, ground_filter=False):
    verts=[];faces=[];labels=[];deps=bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
        for tri in me.loop_triangles:
            pp=[ev.matrix_world@me.vertices[i].co for i in tri.vertices]
            n=(pp[1]-pp[0]).cross(pp[2]-pp[0]);n.normalize()
            if ground_filter and (abs(n.z)<.82 or min(p.z for p in pp)>11.3 or max(p.z for p in pp)<9.8):continue
            start=len(verts);verts.extend(pp);faces.append([start,start+1,start+2]);labels.append(ob.name)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts,faces,all_triangles=True),labels

def run():
    s=bpy.context.scene;version=s['sf1_version'];tag=version.split('_')[-1]
    spec=OUT/('archive/v01/build_input.json' if version=='SF1_v01' else 'derived/build_input.json')
    d=json.loads(spec.read_text());A=np.array(d['A']);U=np.array(d['U']);N=np.array(d['N'])
    def P(u,v,z):return Vector((*list(A+U*u+N*v),z))
    def expected(uv):c=d['ground_plane_coefficients'];return c[0]+c[1]*uv[0]+c[2]*uv[1]
    roles={'walk_surface','walk_support','step_support','step_surface','plinth'}
    author=[o for o in bpy.data.collections[d['import_collection']].objects if o.get('sf1_role') in roles]
    context=[o for o in bpy.data.objects if o.name.startswith('SF1_REF_CTX_')]
    abvh,alabels=mesh_bvh(author);cbvh,clabels=mesh_bvh(context,True)
    outline=np.array(d.get('apron_outline',[[-1.3,-.82],[13.25,-.82],[13.25,8],[-1.3,8]]))
    def inside(pt):
        x,y=pt;yes=False
        for a,b in zip(outline,np.roll(outline,-1,axis=0)):
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:yes=not yes
        return yes
    edges=d.get('ground_edge_profiles') or [dict(edge='front',a=[-1.3,8],b=[13.25,8]),dict(edge='left',a=[-1.3,1.54],b=[-1.3,8]),dict(edge='right',a=[13.25,1.54],b=[13.25,8])]
    rows=[]
    def cast(tree,labels,uv,top=12.0,bottom=9.75):
        p,n,idx,dist=tree.ray_cast(P(*uv,top),Vector((0,0,-1)),top-bottom)
        return None if p is None else dict(z=float(p.z),normal=list(n),object=labels[idx],triangle=int(idx))
    def edge_height(hit,uv,mid):
        n=np.array(hit['normal']);xy=U*(mid[0]-uv[0])+N*(mid[1]-uv[1])
        return hit['z']-float(np.dot(n[:2],xy)/n[2])
    for edge in edges:
        a=np.array(edge['a']);b=np.array(edge['b']);ab=b-a;length=np.linalg.norm(ab);perp=np.array([-ab[1],ab[0]])/length
        if not inside((a+b)/2+perp*.01):perp=-perp
        for t in np.linspace(.06/length,1-.06/length,max(2,int(math.ceil(length/.18)))):
            mid=a+ab*t;inu=mid+perp*.04;outu=mid-perp*.04
            ih=cast(abvh,alabels,inu);raw=[];top=11.3
            for k in range(12):
                hit=cast(cbvh,clabels,outu,top)
                if hit is None:break
                raw.append(hit);top=hit['z']-.002
            eligible=[h for h in raw if abs(h['z']-expected(outu))<.35 and abs(h['normal'][2])>=edge.get('minimum_normal_abs_z',.82)]
            oh=min(eligible,key=lambda h:abs(h['z']-expected(outu))) if eligible else None
            gap=edge_height(ih,inu,mid)-edge_height(oh,outu,mid) if ih and oh else None
            ambiguous=bool(oh and any(abs(h['z']-oh['z'])>.03 for h in eligible))
            okay=bool(ih and oh and not ambiguous and abs(gap)<=.020)
            rows.append(dict(edge=edge['edge'],boundary_uv=mid.tolist(),inside_uv=inu.tolist(),outside_uv=outu.tolist(),author_hit=ih,retained_context_hit=oh,retained_context_all_hits=raw,ambiguous=ambiguous,paired_raw_height_difference_m=(ih['z']-oh['z']) if ih and oh else None,triangle_plane_edge_gap_m=gap,pass_20mm=okay))
    result=dict(version=version,process_id=os.getpid(),native=bpy.data.filepath,purpose='Actual paired surfaces: author 40mm inside and retained context 40mm outside; each actual triangle plane projected to the same boundary point',horizontal_normal_filter=.82,ground_z_window_m=[9.8,11.3],selection='Closest retained ground hit to original apron plane within 0.35m; alternate layers differing by >30mm are unreliable',scope='Front and exposed left/right paving edges; rear masonry interfaces excluded',samples=rows,summary=dict(total=len(rows),missing_author=sum(r['author_hit'] is None for r in rows),missing_retained_context=sum(r['retained_context_hit'] is None for r in rows),ambiguous=sum(r['ambiguous'] for r in rows),over_20mm=sum(r['triangle_plane_edge_gap_m'] is not None and abs(r['triangle_plane_edge_gap_m'])>.020 for r in rows),max_absolute_edge_gap_m=max([abs(r['triangle_plane_edge_gap_m']) for r in rows if r['triangle_plane_edge_gap_m'] is not None],default=None),passed=all(r['pass_20mm'] for r in rows)),limits=['Photo geometry agreement is not surveyed elevation accuracy','No walkability or accessibility claim','Probe samples do not by themselves establish visual continuity'])
    path=OUT/f'evidence/{tag}/actual_boundary_probe.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('SF1_ACTUAL_BOUNDARY',json.dumps(result['summary']),flush=True)
    return result

if __name__=='__main__':run()
