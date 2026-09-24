"""Audit saved native025 materials before enabling a matching realtime export.

No scene mutation, export or acceptance. The report separates actual object
materials from linked mesh defaults and records nontrivial shader inputs.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,runpy
import bpy

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version'].startswith('G1_025')
collection=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
overrides=[];materials={};groups={};copy_samples=[]
deps=bpy.context.evaluated_depsgraph_get()
# Temporary mesh creation/removal invalidates Blender's live all_objects
# iterator. Snapshot object references before probing the export primitive.
for ob in list(collection.all_objects):
    if ob.type!='MESH':continue
    group=ob.get('construction_batch','older')
    record=groups.setdefault(group,dict(objects=0,vertices=0,faces=0))
    record['objects']+=1;record['vertices']+=len(ob.data.vertices);record['faces']+=len(ob.data.polygons)
    if any(slot.material!=(ob.data.materials[i] if i<len(ob.data.materials) else None)
           for i,slot in enumerate(ob.material_slots)):
        overrides.append(ob.name)
        if len(copy_samples)<3 and len(ob.data.vertices)<500000:
            # Probe the actual exporter copy primitive; an override existing
            # alone does not prove that new_from_object loses it.
            evaluated=ob.evaluated_get(deps)
            copy=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
            actual=[slot.material.name if slot.material else None for slot in ob.material_slots]
            copied=[mat.name if mat else None for mat in copy.materials]
            copy_samples.append(dict(object=ob.name,actual_slots=actual,copied_slots=copied,match=actual==copied))
            bpy.data.meshes.remove(copy)
    for slot in ob.material_slots:
        mat=slot.material
        if mat is None or mat.name in materials:continue
        entry=dict(users=mat.users,node_types={},principled_inputs={},procedural_nodes=[])
        if mat.use_nodes:
            entry['node_types']=dict(Counter(n.type for n in mat.node_tree.nodes))
            shader=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
            if shader:
                for name in ['Base Color','Roughness','Metallic','Normal','Transmission Weight','Alpha']:
                    sock=shader.inputs[name]
                    value=sock.default_value
                    entry['principled_inputs'][name]=dict(
                        default=value if isinstance(value,(float,int)) else list(value),
                        sources=[dict(type=l.from_node.type,socket=l.from_socket.name) for l in sock.links])
            entry['procedural_nodes']=[dict(type=n.type,name=n.name) for n in mat.node_tree.nodes
                if n.type in ['TEX_NOISE','TEX_VORONOI','TEX_WAVE','ATTRIBUTE','VOLUME_ABSORPTION','VOLUME_SCATTER']]
        materials[mat.name]=entry
native=Path(bpy.data.filepath)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
report=dict(version=s['version'],native=str(native),native_sha256=digest,
    construction_groups=groups,object_material_override_objects=overrides,material_copy_samples=copy_samples,materials=materials,
    exported=False,visual_equivalence_verified=False,natural_use_verified=False)
(R/'evidence'/s['version']/'runtime_material_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
runpy.run_path(str(R/'tools/blender_probe_bridgehead_bank_terrain.py'))
print('RUNTIME_MATERIAL_AUDIT',json.dumps(dict(materials=len(materials),object_material_overrides=len(overrides),
    procedural_materials=[k for k,v in materials.items() if v['procedural_nodes']],copy_samples=copy_samples,groups=groups)),flush=True)
