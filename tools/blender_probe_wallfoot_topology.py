"""Read-only diagnosis of the actual subbase's nonmanifold edges."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,bmesh,numpy as np
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path

cp=json.loads(read_path('evidence/G1_027r16/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()==cp['native_sha256']
r=json.loads(read_path('evidence/G1_027r16/wallfoot_build_report.json').read_text())
d=json.loads(read_path(r['specification_file']).read_text());A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]
def Q(p):
    p=np.asarray(p);return [float((p[:2]-A)@U),float((p[:2]-A)@N),float(p[2])]
ob=bpy.data.objects['SF1_APRON_CONTINUOUS_SUBBASE'];bm=bmesh.new();bm.from_mesh(ob.data)
bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();bm.faces.ensure_lookup_table()
kd=KDTree(len(bm.verts))
for v in bm.verts:kd.insert(v.co,v.index)
kd.balance();rows=[]
for e in bm.edges:
    if e.is_manifold:continue
    verts=[]
    for v in e.verts:
        verts.append({'index':v.index,'xyz':list(v.co),'uvz':Q(ob.matrix_world@v.co),
                      'near_vertices':[{'index':idx,'distance':dist} for p,idx,dist in kd.find_range(v.co,.00005) if idx!=v.index]})
    rows.append({'edge':e.index,'length':e.calc_length(),'face_count':len(e.link_faces),'vertices':verts,
                 'faces':[{'index':f.index,'area':f.calc_area(),'vertices':[v.index for v in f.verts]} for f in e.link_faces]})
bm.free()
out={'process_id':os.getpid(),'native_sha256':cp['native_sha256'],'object':ob.name,'edges':rows,'native_saved':False}
write_path('evidence/G1_027r16/base_topology_probe.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('BASE_TOPOLOGY',json.dumps(rows),flush=True)
