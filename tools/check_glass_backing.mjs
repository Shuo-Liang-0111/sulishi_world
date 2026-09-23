// Check the actual exported geometry used by the backing-distance shaders.
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from '../web/node_modules/three/build/three.module.js';
import {applyNearBackingTransmission} from '../web/native-case-transmission.js';
const version=process.argv[2]||'G1_016r1';if(!/^G1_\d{3}(r\d+)?$/.test(version))throw Error('Invalid version');
const measureOnly=process.argv.includes('--measure-only');
const base=path.resolve('web/assets'),metadata=JSON.parse(fs.readFileSync(path.join(base,version+'_bellevue.json')));
const gltf=JSON.parse(fs.readFileSync(path.join(base,metadata.authored_runtime.file)));
const sizes={5126:4,5125:4,5123:2,5121:1},readers={5126:'readFloatLE',5125:'readUInt32LE',5123:'readUInt16LE',5121:'readUInt8'},components={VEC3:3,SCALAR:1};
function attribute(index){
  const a=gltf.accessors[index],v=gltf.bufferViews[a.bufferView],size=sizes[a.componentType],n=components[a.type];
  if(!size||!n||a.sparse)throw Error('Unsupported calibration accessor');
  const data=Buffer.alloc(v.byteLength),file=fs.openSync(path.join(base,gltf.buffers[v.buffer].uri),'r');
  fs.readSync(file,data,0,data.length,v.byteOffset||0);fs.closeSync(file);
  const values=[];for(let i=0;i<a.count;i++)for(let j=0;j<n;j++)values.push(data[readers[a.componentType]]((a.byteOffset||0)+i*(v.byteStride||size*n)+j*size));
  return new THREE.BufferAttribute(new (a.componentType===5126?Float32Array:Uint32Array)(values),n);
}
const parents=new Map();gltf.nodes.forEach((n,i)=>n.children?.forEach(c=>parents.set(c,i)));
function transform(i){const n=gltf.nodes[i],m=new THREE.Matrix4();
  if(n.matrix)m.fromArray(n.matrix);else m.compose(new THREE.Vector3().fromArray(n.translation||[0,0,0]),new THREE.Quaternion().fromArray(n.rotation||[0,0,0,1]),new THREE.Vector3().fromArray(n.scale||[1,1,1]));
  return parents.has(i)?transform(parents.get(i)).multiply(m):m;
}
const root=new THREE.Group();
for(let i=0;i<gltf.nodes.length;i++){
  const n=gltf.nodes[i],name=n.extras?.native_object;if(!/^SV_AD_\d+_(GLASS|ART)$/.test(name)&&! /^(CF|CF2|BSF|BSE)_INFO_(MAIN|RETURN)_NOTICE_(GLASS|PRINT)(?:_REVERSE)?$/.test(name))continue;
  const owner=new THREE.Group();owner.userData.native_object=name;owner.matrixAutoUpdate=false;owner.matrix.copy(transform(i));root.add(owner);
  function addNode(node){if(node.mesh!==undefined)for(const primitive of gltf.meshes[node.mesh].primitives){
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',attribute(primitive.attributes.POSITION));if(primitive.indices!==undefined)geometry.setIndex(attribute(primitive.indices));
    const source=gltf.materials[primitive.material];
    const material=new THREE.MeshPhysicalMaterial({transmission:source.extensions?.KHR_materials_transmission?.transmissionFactor||0,roughness:source.pbrMetallicRoughness?.roughnessFactor??1});owner.add(new THREE.Mesh(geometry,material));
  }for(const child of node.children||[])addNode(gltf.nodes[child]);}
  addNode(n);
}
const result=applyNearBackingTransmission(root,{measureOnly});if(!result.records.length)throw Error('No actual paired cases');
fs.writeFileSync('evidence/'+version+'/glass_backing_geometry.json',JSON.stringify({version:metadata.version,records:result.records,geometry_untouched:true,measure_only:measureOnly,shader_visual_acceptance:false},null,2));
console.log(JSON.stringify(result.records));
