// Read the actual saved buffers and reconstruct every leaf with Three.js.
// Geometry agreement is distinct from the pending browser shader comparison.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const config=JSON.parse(await fs.readFile(path.join(root,'workspace.local.json'),'utf8'));
const threeURL=pathToFileURL(path.join(config.legacy_asset_root,'web/node_modules/three/build/three.module.js')).href;
const THREE=await import(threeURL);
const source=await fs.readFile(path.join(root,'web/native-leaf-instances.js'),'utf8');
const module=await import('data:text/javascript;base64,'+Buffer.from(source.replace("from 'three'",`from '${threeURL}'`)).toString('base64'));
const version=process.argv[2];assert.match(version,/^G1_\d{3}(?:r\d+)?$/);
const folder=path.join(root,'web/assets',version+'_leaf_diagnostic');
const exact=process.argv.includes('--exact');
const metadata=JSON.parse(await fs.readFile(path.join(folder,exact?'tree_exact.json':'tree.json'),'utf8'));
assert.equal(metadata.version,version);
const disk=await fs.readFile(path.join(folder,metadata.file));
assert.equal(crypto.createHash('sha256').update(disk).digest('hex'),metadata.sha256);
const buffer=disk.buffer.slice(disk.byteOffset,disk.byteOffset+disk.byteLength);
for(const [key,item] of Object.entries(metadata.arrays)){
  const array=module.leafArray(metadata,buffer,key);
  assert.equal(crypto.createHash('sha256').update(new Uint8Array(array.buffer,array.byteOffset,array.byteLength)).digest('hex'),item.sha256,key);
}
const pair=module.createNativeLeafPair(metadata,buffer);
const expected=pair.reference.geometry.getAttribute('position'),template=pair.instanced.geometry.getAttribute('position');
const expectedNormals=pair.reference.geometry.getAttribute('normal'),expectedColors=pair.reference.geometry.getAttribute('color');
const templateColors=pair.instanced.geometry.getAttribute('color'),encoded=pair.normalTexture.image.data;
const referenceIndex=pair.reference.geometry.index.array,templateIndex=pair.instanced.geometry.index.array;
const matrix=new THREE.Matrix4(),point=new THREE.Vector3(),referencePoint=new THREE.Vector3();
let maxPosition=0,maxNormal=0,maxColor=0;
for(let leaf=0;leaf<metadata.leaves;leaf++){
  if(!exact)pair.instanced.getMatrixAt(leaf,matrix);
  for(let v=0;v<metadata.vertices_per_leaf;v++){
    const index=leaf*metadata.vertices_per_leaf+v;
    if(exact)point.fromArray(pair.positionTexture.image.data,index*4);
    else point.fromBufferAttribute(template,v).applyMatrix4(matrix);
    referencePoint.fromBufferAttribute(expected,index);
    maxPosition=Math.max(maxPosition,point.distanceTo(referencePoint));
    const normal=module.decodeOctNormal(encoded[index*2],encoded[index*2+1]);
    const nx=expectedNormals.getX(index),ny=expectedNormals.getY(index),nz=expectedNormals.getZ(index),length=Math.hypot(nx,ny,nz);
    const cosine=(normal[0]*nx+normal[1]*ny+normal[2]*nz)/length;
    maxNormal=Math.max(maxNormal,Math.acos(Math.max(-1,Math.min(1,cosine)))*180/Math.PI);
    const instanceColors=exact?pair.instanced.geometry.getAttribute('nativeLeafColor'):pair.instanced.instanceColor;
    for(let c=0;c<3;c++)maxColor=Math.max(maxColor,Math.abs(templateColors.array[v*3+c]*instanceColors.array[leaf*3+c]-expectedColors.array[index*3+c]));
  }
  for(let corner=0;corner<templateIndex.length;corner++)assert.equal(referenceIndex[leaf*templateIndex.length+corner],leaf*metadata.vertices_per_leaf+templateIndex[corner]);
}
assert(maxPosition<.0001);assert(maxNormal<.0001);assert(maxColor<1e-6);
assert.deepEqual(pair.reference.matrix.elements,pair.instanced.matrix.elements);
if(exact)assert.equal(maxPosition,0);
const report={version,native_sha256:metadata.native_sha256,binary_sha256:metadata.sha256,position_policy:exact?'exact_native_texture':'affine',
  vertices_checked:expected.count,triangle_corners_checked:referenceIndex.length,
  maximum_position_error_m:maxPosition,maximum_normal_error_degrees:maxNormal,maximum_color_error:maxColor,
  reference_attribute_bytes:metadata.reference_attribute_bytes,packed_attribute_bytes:metadata.packed_attribute_bytes,
  numeric_roundtrip_passed:true,browser_shader_verified:false,native_material_equivalence:false,full_runtime_published:false};
await fs.writeFile(path.join(root,'evidence',version,exact?'leaf_exact_numeric_roundtrip.json':'leaf_numeric_roundtrip.json'),JSON.stringify(report,null,2));
pair.dispose();console.log(JSON.stringify(report));
