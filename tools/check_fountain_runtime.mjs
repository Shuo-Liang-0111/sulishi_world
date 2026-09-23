// Exercise the real exported geometry/animation through the installed Three.js.
// CPU-only: placeholder materials avoid image decoding; no visual claim follows.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../web/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../web/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {createNativeFountainWater} from '../web/native-fountain-water.js';

const root='F:/MyWorld/ZurichWorld',version='G1_018r3';
const read=p=>JSON.parse(fs.readFileSync(`${root}/${p}`,'utf8'));
const metadata=read(`web/assets/${version}_bellevue.json`);
const reference=read(`evidence/${version}/runtime_preparation.json`);
const receipt=read(`evidence/${version}/runtime_externalization.json`);
assert(receipt.geometry_byte_identity_verified);
const base=read('runtime/review_server.json').url+'assets/';
globalThis.ProgressEvent??=class ProgressEvent extends Event{
  constructor(type,options={}){super(type);Object.assign(this,options);}
};
const loader=new GLTFLoader();
loader.register(()=>({name:'CPU_GEOMETRY_ONLY',loadMaterial(){return Promise.resolve(new THREE.MeshBasicMaterial());}}));
const text=fs.readFileSync(`${root}/web/assets/${metadata.authored_runtime.file}`,'utf8');
const gltf=await loader.parseAsync(text,base);
const identities=new Set();gltf.scene.traverse(o=>{if(o.userData.native_object)identities.add(o.userData.native_object);});
assert.equal(identities.size,metadata.exported_authored_objects);
const water=createNativeFountainWater(gltf.scene,metadata,gltf.animations);
assert(water);
const comparisons=[];let previous=0;
for(const sample of reference.weights){
  const t=(sample.frame-1)/reference.fps;water.update(t-previous);previous=t;
  const state=water.getState();
  for(const values of state.weights){assert.equal(values.length,1);assert(Math.abs(values[0]-sample.weight)<1e-6);}
  comparisons.push({frame:sample.frame,weight:state.weights[0][0],expected:sample.weight});
}
// One complete cycle returns to the same bounded water shape, without moving the rim.
water.update(.5);const beforePause=water.getState();
water.setEnabled(false);water.update(1.2);assert.equal(water.getState().phase,beforePause.phase);
water.setEnabled(true);water.update(.1);assert(water.getState().phase>beforePause.phase);
const view=metadata.cameras.BE_QA_FOUNTAIN_REVERSE;
const camera=new THREE.PerspectiveCamera(view.fov,1600/1050,.08,5000);
camera.position.fromArray(view.position);camera.lookAt(new THREE.Vector3().fromArray(view.target));camera.updateMatrixWorld();
assert(water.visibleFrom(camera));
const away=new THREE.Vector3().fromArray(view.position).multiplyScalar(2).sub(new THREE.Vector3().fromArray(view.target));
camera.lookAt(away);camera.updateMatrixWorld();assert(!water.visibleFrom(camera));
const report={version,threeRevision:THREE.REVISION,actualGeometryFile:metadata.authored_runtime.file,
  identities:identities.size,nativeAnimationSamples:comparisons,loopAndPauseVerified:true,
  frontAndAwayVisibilityVerified:true,geometryAndAnimationOnly:true,
  materialDecodingOrWebGLTested:false,runtimeVisualAccepted:false,naturalUseAccepted:false};
fs.writeFileSync(`${root}/evidence/${version}/water_runtime_cpu_check.json`,JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
