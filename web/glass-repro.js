import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.toneMapping=THREE.AgXToneMapping;document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(.4,.45,.5);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,.01,20),controls=new OrbitControls(camera,renderer.domElement);
const pmrem=new THREE.PMREMGenerator(renderer),env=new RoomEnvironment();scene.environment=pmrem.fromScene(env,.04).texture;env.dispose();pmrem.dispose();
const gltf=await new GLTFLoader().loadAsync('./assets/diagnostics/glass_case.glb');const root=gltf.scene;const box=new THREE.Box3().setFromObject(root);const center=box.getCenter(new THREE.Vector3());root.position.sub(center);scene.add(root);
const material=new THREE.MeshStandardMaterial({color:0x7b6b59,roughness:.6});const back=new THREE.Mesh(new THREE.BoxGeometry(5,3,.04),material);back.position.set(0,0,-.7);scene.add(back);
for(let y=-1;y<1;y+=.07){const slat=new THREE.Mesh(new THREE.BoxGeometry(5,.026,.06),new THREE.MeshStandardMaterial({color:0xa28f73,roughness:.5}));slat.position.set(0,y,-.66);scene.add(slat);}
const floor=new THREE.Mesh(new THREE.BoxGeometry(5,.08,5),new THREE.MeshStandardMaterial({color:0x909799,metalness:.7,roughness:.3}));floor.position.y=-.32;scene.add(floor);
camera.position.set(.1,.28,1.5);controls.target.set(0,0,0);controls.update();
const mats=new Set();root.traverse(o=>{if(o.isMesh)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>mats.add(m));});
let disableSamples=false,found=null;
// Isolated diagnostic has no other mipmapped, multisampled HDR render target.
// No production renderer or source asset is changed by this local interception.
const setTarget=renderer.setRenderTarget.bind(renderer);
renderer.setRenderTarget=(target,...args)=>{
  if(target?.texture?.type===THREE.HalfFloatType&&target.texture.generateMipmaps&&target.samples===4){
    found=target;
    if(disableSamples){target.dispose();target.samples=0;}
  }
  return setTarget(target,...args);
};
document.querySelector('#samples').onclick=()=>{disableSamples=true;};
document.querySelector('#front').onclick=()=>{mats.forEach(m=>{if(m.transmission>0){m.side=THREE.FrontSide;m.needsUpdate=true;}});};
document.querySelector('#lod').onclick=()=>{mats.forEach(m=>{if(m.transmission>0){m.onBeforeCompile=shader=>{shader.fragmentShader=shader.fragmentShader.replace('#include <transmission_pars_fragment>',THREE.ShaderChunk.transmission_pars_fragment.replace('return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );','return textureLod( transmissionSamplerMap, fragCoord.xy, 0.0 );'));};m.customProgramCacheKey=()=>'mip-zero-diagnostic';m.needsUpdate=true;}});};
document.querySelector('#reset').onclick=()=>location.reload();
document.querySelector('#actual').onclick=async()=>{const data=await(await fetch('./assets/G1_006r2_bellevue.json')).json();const v=data.cameras.BE_QA_INTERIOR;camera.position.fromArray(v.position).sub(center);controls.target.fromArray(v.target).sub(center);camera.fov=v.fov;camera.updateProjectionMatrix();controls.update();};
document.querySelector('#coords').onclick=e=>{scene.children.forEach(o=>o.position.add(center));camera.position.add(center);controls.target.add(center);controls.update();e.target.disabled=true;};
document.querySelector('#sky').onclick=async()=>{const hdr=await new HDRLoader().loadAsync('./assets/G1_006r2_sky.hdr');const gen=new THREE.PMREMGenerator(renderer);scene.environment=gen.fromEquirectangular(hdr).texture;hdr.dispose();gen.dispose();document.querySelector('#sky').textContent='已用原生天空';};
function frame(){requestAnimationFrame(frame);controls.update();renderer.render(scene,camera);document.querySelector('#status').textContent=`原生 G1_007r2 / Three ${THREE.REVISION}\n内部目标 samples: ${found?.samples??'尚未捕获'}\n${found?`${found.width} × ${found.height}`:''}`;}frame();
addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();});
