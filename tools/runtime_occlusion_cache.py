"""Attach independently baked indirect occlusion to evaluated export copies."""
import hashlib
import json
from pathlib import Path
import bpy
import numpy as np

class RuntimeOcclusion:
    def __init__(self,root,version):
        p=root/'derived/runtime_occlusion'/version/'manifest.json'
        self.report=None;self.applied=[];self.materials={}
        if not p.exists():return
        self.report=json.loads(p.read_text());assert self.report['version']==version
        self.by_name={r['name']:r for r in self.report['receivers']}
        self.uvs=np.load(root/self.report['uv_file'])
        image_path=root/self.report['image']
        assert hashlib.sha256(image_path.read_bytes()).hexdigest()==self.report['image_sha256']
        self.image=bpy.data.images.load(str(image_path),check_existing=True)
        self.image.colorspace_settings.name='Non-Color'
        from io_scene_gltf2.blender.com.material_helpers import create_settings_group,get_gltf_node_name
        self.group=bpy.data.node_groups.get(get_gltf_node_name()) or create_settings_group(get_gltf_node_name())

    def apply(self,name,mesh):
        if not self.report or name not in self.by_name:return
        record=self.by_name[name]
        v=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',v)
        ids=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',ids)
        assert hashlib.sha256(v.tobytes()+ids.tobytes()).hexdigest()==record['topology_sha256'],name
        values=self.uvs[record['uv_key']]
        assert values.shape==(len(mesh.loops),2)
        if not mesh.uv_layers:
            mesh.uv_layers.new(name='native_primary_uv')
        layer=mesh.uv_layers.new(name='runtime_indirect_occlusion')
        layer.data.foreach_set('uv',values.ravel())
        # The original UV channel remains the default for existing PBR maps.
        mesh.uv_layers.active_index=0;mesh.uv_layers[0].active_render=True
        for i,source in enumerate(list(mesh.materials)):
            if source is None:continue
            if source.name not in self.materials:
                mat=source.copy();mat.name='RTAO_'+source.name
                nodes=mat.node_tree.nodes;links=mat.node_tree.links
                image=nodes.new('ShaderNodeTexImage');image.image=self.image
                uv=nodes.new('ShaderNodeUVMap');uv.uv_map=layer.name
                output=nodes.new('ShaderNodeGroup');output.node_tree=self.group
                links.new(uv.outputs['UV'],image.inputs['Vector'])
                links.new(image.outputs['Color'],output.inputs['Occlusion'])
                self.materials[source.name]=mat
            mesh.materials[i]=self.materials[source.name]
        self.applied.append(name)

    def evidence(self):
        if not self.report:return None
        assert set(self.applied)==set(self.by_name),'Occlusion receivers missing from export'
        return {'receivers_verified':len(self.applied),'source_version':self.report['version'],
                'image_sha256':self.report['image_sha256'],'uv_topology_verified':True,
                'inherited_scalar_ao_from':self.report.get('inherited_scalar_ao_from'),
                'invalid_scalar_ao_receivers':self.report.get('invalid_scalar_ao_receivers',[]),
                'distance_m':self.report['distance_m'],'approximation':self.report['limitation']}
