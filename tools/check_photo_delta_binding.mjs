// Actual Three.js geometry swaps and rollback guards; no browser rendering claim.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const config=JSON.parse(await fs.readFile(path.join(root,'workspace.local.json'),'utf8'));
const threeURL=pathToFileURL(path.join(config.legacy_asset_root,'web/node_modules/three/build/three.module.js')).href;
const THREE=await import(threeURL);
const source=await fs.readFile(path.join(root,'web/native-context-delta.js'),'utf8');
// Same installed dependency as the browser import map, without writing H/node_modules.
const {preparePhotoGeometryDelta}=await import('data:text/javascript;base64,'+
  Buffer.from(source.replace("from 'three'",`from '${threeURL}'`)).toString('base64'));
const geometry=()=>{
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute([0,0,0,1,0,0,0,1,0],3));
  g.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,0,1],2));return g;
};
const mesh=(id,g=geometry())=>{
  const m=new THREE.Mesh(g,new THREE.MeshBasicMaterial());m.userData.source_node=id;return m;
};
const photoRoot=new THREE.Group(),patchRoot=new THREE.Group();
const first=mesh('100'),cleared=mesh('101'),unchanged=mesh('102'),patch=mesh('100');
photoRoot.add(first,cleared,unchanged);patchRoot.add(patch);
const base=[first.geometry,cleared.geometry,unchanged.geometry],material=first.material;
const options={photoRoot,patchRoot,changedNodes:['100','101'],emptyNodes:['101'],version:'G1_027r7'};
let checks=0;
const rejected=action=>{assert.throws(action);assert.equal(first.geometry,base[0]);assert.equal(cleared.geometry,base[1]);checks++;};
rejected(()=>preparePhotoGeometryDelta({...options,changedNodes:['100','103'],emptyNodes:['103']}));
rejected(()=>preparePhotoGeometryDelta({...options,changedNodes:['100','100','101']}));
patch.position.x=.02;rejected(()=>preparePhotoGeometryDelta(options));patch.position.x=0;
const uv=patch.geometry.getAttribute('uv');patch.geometry.deleteAttribute('uv');
rejected(()=>preparePhotoGeometryDelta(options));patch.geometry.setAttribute('uv',uv);
patch.userData.construction_version='G1_018r3';rejected(()=>preparePhotoGeometryDelta(options));
patch.userData.construction_version='G1_027r7';
const delta=preparePhotoGeometryDelta(options);assert.equal(first.geometry,base[0]);
delta.setActive(true);assert.equal(first.geometry,patch.geometry);assert.equal(first.material,material);
assert.equal(cleared.geometry.getAttribute('position').count,0);assert.equal(unchanged.geometry,base[2]);
delta.setActive(false);assert.equal(first.geometry,base[0]);assert.equal(cleared.geometry,base[1]);checks++;
cleared.geometry=geometry();assert.throws(()=>delta.setActive(true));assert.equal(first.geometry,base[0]);checks++;
cleared.geometry=base[1];

// Optionally verify the real exported patch against the real base geometry and
// transforms. Removing image/material references affects loading cost only;
// identity, matrices, geometry and UV buffers remain the exact exported bytes.
const version=process.argv[2];let real=null;
if(version){
  const {GLTFLoader}=await import(pathToFileURL(path.join(config.legacy_asset_root,'web/node_modules/three/examples/jsm/loaders/GLTFLoader.js')).href);
  const manifest=JSON.parse(await fs.readFile(path.join(root,'web/assets',version+'_context_delta.json'),'utf8'));
  const basePath=path.join(config.legacy_asset_root,'web/assets/G1_004r2_photo_stream.glb');
  const baseRaw=await fs.readFile(basePath),length=baseRaw.readUInt32LE(12);
  const document=JSON.parse(baseRaw.subarray(20,20+length).toString());
  const bin=baseRaw.subarray(28+length);
  delete document.images;delete document.textures;delete document.samplers;delete document.materials;
  for(const m of document.meshes)for(const p of m.primitives)delete p.material;
  let json=Buffer.from(JSON.stringify(document));json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
  const header=Buffer.alloc(20);header.write('glTF');header.writeUInt32LE(2,4);header.writeUInt32LE(28+json.length+bin.length,8);
  header.writeUInt32LE(json.length,12);header.writeUInt32LE(0x4e4f534a,16);
  const binHeader=Buffer.alloc(8);binHeader.writeUInt32LE(bin.length);binHeader.writeUInt32LE(0x004e4942,4);
  const plain=Buffer.concat([header,json,binHeader,bin]);const arrayBuffer=b=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);
  const loader=new GLTFLoader();
  const baseScene=(await loader.parseAsync(arrayBuffer(plain),'')).scene;
  const patchBytes=await fs.readFile(path.join(root,'web/assets',manifest.file));
  const patchScene=(await loader.parseAsync(arrayBuffer(patchBytes),'')).scene;
  const realDelta=preparePhotoGeometryDelta({photoRoot:baseScene,patchRoot:patchScene,
    changedNodes:manifest.changed_nodes,emptyNodes:manifest.empty_nodes,version});
  const originalMaterials=realDelta.replacements.map(r=>r.original.material);
  realDelta.setActive(true);
  for(const [i,r] of realDelta.replacements.entries()){
    assert.equal(r.original.geometry,r.refined);assert.equal(r.original.material,originalMaterials[i]);
  }
  realDelta.setActive(false);for(const r of realDelta.replacements)assert.equal(r.original.geometry,r.base);
  real={version,changed_nodes:realDelta.replacements.length,empty_nodes:manifest.empty_nodes.length,
    actual_glb_loaded_by_three:true,geometry_swap_and_restore:true,
    source_material_objects_preserved:true,photo_textures_decoded:false,browser_rendered:false};
}
const report={verified_utc:new Date().toISOString(),synthetic_guard_checks:checks,real_export:real};
const output=path.join(root,version?`evidence/${version}/context_delta_binding.json`:'runtime/migration/photo_delta_guard_checks.json');
await fs.writeFile(output,JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
