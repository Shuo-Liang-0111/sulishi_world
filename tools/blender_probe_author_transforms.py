"""Read evaluated native author matrices without temporary parent/TRS rebuilding."""
from pathlib import Path
import hashlib,json,os,sys
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path,validate_native
version=bpy.context.scene['version'];assert version=='G1_027r15'
native=validate_native(bpy.data.filepath)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
manifest=json.loads(read_path(f'web/assets/{version}_current_r01/manifest.json').read_text());assert manifest['native_sha256']==digest
target=write_path(f'evidence/{version}/current_author_native_matrices.json');assert not target.exists()
deps=bpy.context.evaluated_depsgraph_get();rows=[]
for name in manifest['expected_geometry_names']:
    ob=bpy.data.objects[name];ev=ob.evaluated_get(deps)
    rows.append({'name':name,'parent':ob.parent.name if ob.parent else None,'matrix_world':[list(row) for row in ev.matrix_world]})
with native.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
target.write_text(json.dumps({'version':version,'native_sha256':digest,'process_id':os.getpid(),'objects':rows,'native_modified':False},indent=2),encoding='utf-8')
print('NATIVE_AUTHOR_MATRICES_READ',len(rows),os.getpid(),flush=True)
