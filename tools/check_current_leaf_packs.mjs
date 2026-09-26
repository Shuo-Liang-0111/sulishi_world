// Validate every saved production leaf pack through the actual Three.js module.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const version=process.argv[2],attempt=process.argv[3]||'r01';
assert.match(version,/^G1_\d{3}r\d+$/);assert.match(attempt,/^r\d+$/);
const config=JSON.parse(await fs.readFile(path.join(root,'workspace.local.json'),'utf8'));
const threeURL=pathToFileURL(path.join(config.legacy_asset_root,'web/node_modules/three/build/three.module.js')).href;
const source=await fs.readFile(path.join(root,'web/native-leaf-instances.js'),'utf8');
const module=await import('data:text/javascript;base64,'+Buffer.from(source.replace("from 'three'",`from '${threeURL}'`)).toString('base64'));
const folder=path.join(root,'web/assets',version+'_current_'+attempt);
const manifest=JSON.parse(await fs.readFile(path.join(folder,'manifest.json'),'utf8'));
assert.equal(manifest.leaves.length,50,'All current tree crowns must be exported before this check');
const hash=data=>crypto.createHash('sha256').update(data).digest('hex');
const checks=[];
for(const entry of manifest.leaves){
  const metadata=JSON.parse(await fs.readFile(path.join(folder,entry.metadata),'utf8'));
  assert.equal(metadata.version,version);assert.equal(metadata.native_sha256,manifest.native_sha256);
  assert.equal(metadata.format,'exact_native_leaf_runtime_v1');assert.equal(metadata.native_object,entry.name);
  const disk=await fs.readFile(path.resolve(folder,path.dirname(entry.metadata),metadata.file));
  assert.equal(hash(disk),metadata.sha256);assert.equal(metadata.sha256,entry.sha256);
  const buffer=disk.buffer.slice(disk.byteOffset,disk.byteOffset+disk.byteLength);
  for(const [key,item] of Object.entries(metadata.arrays)){
    const a=module.leafArray(metadata,buffer,key);
    assert.equal(hash(new Uint8Array(a.buffer,a.byteOffset,a.byteLength)),item.sha256,key);
  }
  const pair=module.createNativeLeafPair(metadata,buffer);
  assert.equal(pair.reference,null);assert.equal(pair.instanced.visible,true);assert(pair.exact);
  assert(pair.instanced.customDepthMaterial&&pair.instanced.customDistanceMaterial);
  assert.throws(()=>pair.setMode('reference'));
  const texture=pair.positionTexture.image.data,positions=new Float32Array(metadata.source_vertex_count*3);
  for(let i=0;i<metadata.source_vertex_count;i++)positions.set(texture.subarray(i*4,i*4+3),i*3);
  assert.equal(hash(new Uint8Array(positions.buffer)),metadata.source_position_sha256);
  const template=pair.instanced.geometry.index.array,triangles=new Uint32Array(metadata.source_triangle_count*3);
  assert.equal(template.length*metadata.leaves,triangles.length);
  for(let leaf=0;leaf<metadata.leaves;leaf++)for(let corner=0;corner<template.length;corner++)triangles[leaf*template.length+corner]=template[corner]+leaf*metadata.vertices_per_leaf;
  assert.equal(hash(new Uint8Array(triangles.buffer)),metadata.source_triangle_sha256);
  assert(!pair.worldBounds.isEmpty());assert(pair.worldBounds.min.toArray().every(Number.isFinite));
  checks.push({name:entry.name,bytes:entry.bytes,vertices:metadata.source_vertex_count,triangles:metadata.source_triangle_count,
    exact_position_hash_verified:true,complete_triangle_topology_hash_verified:true,
    native_normal_encoding_error_degrees:metadata.maximum_normal_angle_error_degrees,
    native_color_encoding_error:metadata.maximum_color_error});
  pair.dispose();console.log('LEAF_PACK_VERIFIED',checks.length,entry.name);
}
const report={version,attempt,native_sha256:manifest.native_sha256,objects_checked:checks.length,
  vertices_checked:checks.reduce((a,b)=>a+b.vertices,0),triangles_checked:checks.reduce((a,b)=>a+b.triangles,0),
  numeric_roundtrip_passed:true,browser_all_trees_verified:false,native_material_equivalence:false,full_runtime_published:false,checks};
await fs.writeFile(path.join(root,'evidence',version,`current_leaves_${attempt}_roundtrip.json`),JSON.stringify(report,null,2));
console.log(JSON.stringify({...report,checks:undefined}));
