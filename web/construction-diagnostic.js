import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RectAreaLightUniformsLib} from 'three/addons/lights/RectAreaLightUniformsLib.js';
const pref=new URLSearchParams(location.search).get('gpu')==='high'?'high-performance':'default';
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:pref});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=THREE.AgXToneMapping;document.body.appendChild(renderer.domElement);
const gl=renderer.getContext(),gpuInfo=gl.getExtension('WEBGL_debug_renderer_info'),gpuName=gpuInfo?gl.getParameter(gpuInfo.UNMASKED_RENDERER_WEBGL):'GPU info unavailable';
const scene=new THREE.Scene();scene.background=new THREE.Color('#89969e');
const camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.1,5000),controls=new OrbitControls(camera,renderer.domElement);
const meta=await(await fetch('./assets/G1_006r2_bellevue.json')).json(),manager=new THREE.LoadingManager(),loader=new GLTFLoader(manager);
loader.register(parser=>({name:'ZURICH_diagnostic_loader',loadTexture(index){return parser.loadTextureImage(index,parser.json.textures[index].source,new THREE.TextureLoader(manager));}}));
const [gltf,hdr]=await Promise.all([loader.loadAsync('./assets/'+meta.authored_runtime.file),new HDRLoader().loadAsync('./assets/G1_006r2_sky.hdr')]);
const root=gltf.scene;scene.add(root);const pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromEquirectangular(hdr).texture;hdr.dispose();pmrem.dispose();
root.traverse(o=>{if(o.isMesh){const mats=Array.isArray(o.material)?o.material:[o.material];o.castShadow=!mats.some(m=>m.transmission>.1);o.receiveShadow=true;if(String(o.userData.native_object||o.name).includes('BE_ROOF_STANDING_SEAM')){o.castShadow=false;o.receiveShadow=false;}for(const m of mats){if(m.map)m.map.anisotropy=8;if(m.normalMap)m.normalMap.anisotropy=8;}}});
const area=new THREE.Group();RectAreaLightUniformsLib.init();for(const item of meta.lights){const side=item.diameter_m*Math.sqrt(Math.PI)/2;const l=new THREE.RectAreaLight(new THREE.Color().fromArray(item.color),1,side,side);l.power=item.power_W;l.position.fromArray(item.position);l.lookAt(l.position.clone().add(new THREE.Vector3(0,-1,0)));area.add(l);}scene.add(area);
const sun=new THREE.DirectionalLight(0xfff6e7,2.5);sun.position.set(-270,115,-200);sun.target.position.set(-200,10,-138);scene.add(sun,sun.target);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-36,right:36,top:36,bottom:-36,near:.5,far:240});sun.shadow.bias=-.0001;sun.shadow.normalBias=.015;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
function view(key){const v=meta.cameras[key];camera.position.fromArray(v.position);controls.target.fromArray(v.target);camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(v.fov/2))*Math.max(1,(1600/1050)/camera.aspect)));camera.updateProjectionMatrix();controls.update();}
view('BE_QA_INTERIOR');document.querySelector('#interior').onclick=()=>view('BE_QA_INTERIOR');document.querySelector('#entry').onclick=()=>view('BE_QA_ENTRY');
document.querySelector('#area').onclick=e=>{area.visible=!area.visible;e.target.textContent=area.visible?'关闭区域灯':'开启区域灯';};document.querySelector('#sun').onclick=e=>{sun.visible=!sun.visible;e.target.textContent=sun.visible?'关闭日光':'开启日光';};
document.querySelector('#shadows').onclick=e=>{renderer.shadowMap.enabled=!renderer.shadowMap.enabled;root.traverse(o=>{if(o.isMesh)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.needsUpdate=true);});e.target.textContent=renderer.shadowMap.enabled?'关闭阴影':'开启阴影';};
let subset=false;document.querySelector('#subset').onclick=e=>{subset=!subset;root.traverse(o=>{if(o.isMesh)o.visible=!subset||/DISPLAY|COUNTER|BACK_WALL|SLAT|BOTTLE|COFFEE/i.test(o.userData.native_object||o.name);});e.target.textContent=subset?'恢复全亭体':'隔离柜台与后墙';};
// Display the exact opaque pass sampled by transmission. No material changes.
let captured=null,showBuffer=false;const setTarget=renderer.setRenderTarget.bind(renderer);renderer.setRenderTarget=(target,...args)=>{if(target?.texture?.type===THREE.HalfFloatType&&target.texture.generateMipmaps)captured=target;return setTarget(target,...args);};
const debugScene=new THREE.Scene(),debugCamera=new THREE.OrthographicCamera(-1,1,1,-1,0,1),debugMaterial=new THREE.MeshBasicMaterial({toneMapped:true});debugScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),debugMaterial));
document.querySelector('#mip').onclick=e=>{showBuffer=!showBuffer;e.target.textContent=showBuffer?'恢复正常画面':'显示透射缓冲';};document.querySelector('#reset').onclick=()=>location.reload();
let photoRoot=null,photoNote='未载入摄影背景';
const photoButton=document.createElement('button');photoButton.textContent='载入摄影低清底图';document.querySelector('aside').insertBefore(photoButton,document.querySelector('#status'));
photoButton.onclick=async()=>{
 if(photoRoot){photoRoot.visible=!photoRoot.visible;photoButton.textContent=photoRoot.visible?'隐藏摄影底图':'显示摄影底图';return;}
 photoButton.disabled=true;photoButton.textContent='加载中';
 const [source,patch]=await Promise.all([new GLTFLoader().loadAsync('./assets/G1_004r2_photo_stream.glb'),new GLTFLoader().loadAsync('./assets/'+meta.context_patch.file)]);
 photoRoot=source.scene;const byId=new Map();photoRoot.traverse(o=>{if(o.isMesh)byId.set(String(o.userData.source_node),o);});let count=0;
 patch.scene.traverse(o=>{if(o.isMesh){const dst=byId.get(String(o.userData.source_node));if(!dst)throw Error('Missing photo patch identity');dst.geometry=o.geometry;count++;}});
 if(count!==meta.changed_nodes.length)throw Error('Photo patch count mismatch');scene.add(photoRoot);photoButton.disabled=false;photoButton.textContent='隐藏摄影底图';photoNote=`摄影低清 ${byId.size} 分块 / ${count} 替换`;
};
const tierButton=document.createElement('button');tierButton.textContent='加载视野原始纹理';document.querySelector('aside').insertBefore(tierButton,document.querySelector('#status'));
tierButton.onclick=async()=>{
 if(!photoRoot)return;tierButton.disabled=true;camera.updateMatrixWorld();photoRoot.updateMatrixWorld(true);
 const frustum=new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse)),candidates=[];
 const pixels=innerHeight/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov*.5)));
 photoRoot.traverse(o=>{if(!o.isMesh)return;o.geometry.computeBoundingSphere();const sphere=o.geometry.boundingSphere.clone().applyMatrix4(o.matrixWorld);if(!frustum.intersectsSphere(sphere))return;const score=sphere.radius*2/Math.max(1,camera.position.distanceTo(sphere.center)-sphere.radius)*pixels;
  for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.userData.runtime_texture_lod&&score>80)candidates.push({m,score,data:m.userData.runtime_texture_lod});});
 candidates.sort((a,b)=>b.score-a.score);let full=0,bytes=0,medium=0,loaded=0;
 for(const c of candidates){let tier;const size=c.data.width*c.data.height*4;if(c.score>200&&full<72&&bytes+size<96*1024*1024){tier='full';full++;bytes+=size;}else if(medium<96){tier='medium';medium++;}else continue;
  const tex=await new THREE.TextureLoader().loadAsync('./assets/'+c.data[tier]);tex.flipY=false;tex.colorSpace=THREE.SRGBColorSpace;tex.wrapS=c.m.map.wrapS;tex.wrapT=c.m.map.wrapT;tex.anisotropy=4;c.m.map=tex;tierButton.textContent=`已替换 ${++loaded}`;
 }photoNote=`摄影 2039 / 13 替换 / full ${full} / medium ${medium}`;tierButton.textContent='视野原始纹理已就绪';
};
const doorButton=document.createElement('button');doorButton.textContent='应用入口动画姿态';document.querySelector('aside').insertBefore(doorButton,document.querySelector('#status'));
doorButton.onclick=e=>{let n=0;root.traverse(o=>{if(o.userData.interaction_role==='curved_sliding_door_leaf'){o.quaternion.setFromAxisAngle(new THREE.Vector3(0,1,0),Number(o.userData.open_rotation_z));n++;}});e.target.textContent=`已更新 ${n} 门扇`;};
const hemiButton=document.createElement('button');hemiButton.textContent='加入零强度半球光';document.querySelector('aside').insertBefore(hemiButton,document.querySelector('#status'));
let diagnosticHemi=null;hemiButton.onclick=e=>{if(!diagnosticHemi){diagnosticHemi=new THREE.HemisphereLight(0xd7e3ee,0x8b8273,0);scene.add(diagnosticHemi);}else diagnosticHemi.visible=!diagnosticHemi.visible;e.target.textContent=diagnosticHemi.visible?'隐藏零强度半球光':'恢复零强度半球光';};
function frame(){requestAnimationFrame(frame);controls.update();renderer.render(scene,camera);if(showBuffer&&captured){debugMaterial.map=captured.texture;debugMaterial.needsUpdate=!debugMaterial.userData.ready;debugMaterial.userData.ready=true;renderer.render(debugScene,debugCamera);}document.querySelector('#status').textContent=`Three ${THREE.REVISION} / G1_006r2 亭体\n区域灯 ${area.visible} / 日光 ${sun.visible} / 阴影 ${renderer.shadowMap.enabled}\n缓冲 ${captured?.width} × ${captured?.height} / samples ${captured?.samples}\n${photoNote}\n${pref}: ${gpuName}`;}frame();
addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();});
