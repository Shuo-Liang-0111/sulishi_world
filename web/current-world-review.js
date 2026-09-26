import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RectAreaLightUniformsLib} from 'three/addons/lights/RectAreaLightUniformsLib.js';
import {loadNativeLeafPair} from './native-leaf-instances.js';
import {preparePhotoGeometryDelta} from './native-context-delta.js';
import {alignNativePanorama} from './native-panorama.js';
import {loadNativeHSVMaterials} from './native-hsv-materials.js';
import {loadNativeFBMMaterials} from './native-fbm-materials.js';

const version='G1_027r15',base=`./assets/${version}_current_r01/`;
const canvas=document.querySelector('#canvas'),status=document.querySelector('#status'),metrics=document.querySelector('#metrics'),cameraSelect=document.querySelector('#camera');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.AgXToneMapping;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
// The exported author scene is static except for the non-shadow-casting water.
// Re-render exact shadows on geometry/light changes, not on every idle frame.
renderer.shadowMap.autoUpdate=false;
const scene=new THREE.Scene();scene.background=new THREE.Color('#9babb5');
const camera=new THREE.PerspectiveCamera(48,1,.05,1600),controls=new OrbitControls(camera,canvas);controls.enableDamping=true;
const conversion=new THREE.Matrix4().makeRotationX(-Math.PI/2),manager=new THREE.LoadingManager(),errors=[];
manager.onError=url=>errors.push(url);
const texturePool=new Map(),plainTextures=new THREE.TextureLoader(manager);
const sharedTextures={load(url,onLoad,_progress,onError){
  const key=new URL(url,location.href).href;
  if(!texturePool.has(key))texturePool.set(key,plainTextures.loadAsync(key));
  texturePool.get(key).then(t=>onLoad(t.clone())).catch(onError);
}};
const loader=new GLTFLoader(manager);
loader.register(parser=>({name:'ZURICH_current_shared_images',loadTexture(index){return parser.loadTextureImage(index,parser.json.textures[index].source,sharedTextures);}}));
let manifest,photoRoot,sun,hsvMaterials,busy=false,lastFrame=performance.now(),frameTimes=[],manifestStamp='',activeNativeCamera,needsRender=true;
controls.addEventListener('change',()=>{needsRender=true;});
let translatedHSVMaterials=0,translatedFBMMaterials=0,renderFailure=null,anchors,fbmMaterials;
const chunks=new Map(),leaves=new Map(),leafMetadata=new Map(),identities=new Set(),mixers=[];
const photoDetail=new Map();let photoDetailStats=null;
const lightRoot=new THREE.Group();scene.add(lightRoot);RectAreaLightUniformsLib.init();
const nearRadius=95;
function matrix(values){return new THREE.Matrix4().set(...values.flat());}
function world(values){return conversion.clone().multiply(matrix(values));}
function refreshMetrics(){
  metrics.textContent=JSON.stringify({version,native_sha256:manifest?.native_sha256,export_status:manifest?.status,
    loaded_chunks:chunks.size,available_chunks:manifest?.chunks.length,loaded_tree_crowns:leaves.size,available_tree_crowns:manifest?.leaves.length,
    geometry_identities_loaded:identities.size,expected_geometry_identities:manifest?.expected_geometry_objects,
    native_cameras:manifest?.camera_inventory.length,photo_detail:photoDetailStats,draw_calls:renderer.info.render.calls,triangles_last_frame:renderer.info.render.triangles,
    translated_hsv_material_instances:translatedHSVMaterials,translated_fbm_material_instances:translatedFBMMaterials,render_failure:renderFailure,
    native_world_anchors_verified:Boolean(anchors),
    median_render_submission_ms:frameTimes.length?Number([...frameTimes].sort((a,b)=>a-b)[Math.floor(frameTimes.length/2)].toFixed(1)):null,
    idle_rendering:'on demand; animate only when an actual morph mesh intersects the camera frustum',
    shader_errors:renderer.info.programs.filter(p=>p.diagnostics?.runnable===false).length,load_errors:errors,
    source_procedural_materials_pending:manifest?.material_routes_summary,materials_fully_converted:false,full_runtime_published:false,natural_use_verified:false},null,2);
}
function updateProjection(){
  const c=activeNativeCamera;
  if(c){const vertical=c.sensor_fit==='VERTICAL'||(c.sensor_fit==='AUTO'&&camera.aspect<1);
    camera.fov=THREE.MathUtils.radToDeg(2*Math.atan((vertical?c.sensor_height:c.sensor_width/camera.aspect)/(2*c.lens_mm)));}
  camera.updateProjectionMatrix();
}
function resize(){renderer.setSize(canvas.clientWidth,canvas.clientHeight,false);camera.aspect=canvas.clientWidth/canvas.clientHeight;updateProjection();needsRender=true;}
addEventListener('resize',resize);resize();
function setCamera(name){
  const c=manifest.camera_inventory.find(x=>x.name===name);if(!c)throw new Error('Unknown native camera');
  if(c.camera_type!=='PERSP'||c.shift_x||c.shift_y)throw new Error('This camera requires a separate projection implementation');
  const m=world(anchors.cameras.find(x=>x.name===c.name).matrix_world);camera.position.setFromMatrixPosition(m);camera.quaternion.setFromRotationMatrix(m);
  camera.near=c.near;camera.far=c.far;activeNativeCamera=c;updateProjection();
  const direction=new THREE.Vector3(0,0,-1).applyQuaternion(camera.quaternion);
  controls.target.copy(camera.position).addScaledVector(direction,20);controls.update();cameraSelect.value=name;updateSun();
  const referenceAvailable=['UF_QA_FRONT','UF_QA_LANE','BST_QA_NORTH'].includes(name);
  document.querySelector('#native-reference').hidden=!referenceAvailable;
  if(referenceAvailable)document.querySelector('#native-reference-link').href=`./assets/${version}_native_review/${name}.png`;
}
function updateSun(){
  if(!sun)return;
  const center=controls.target;
  if(!sun.userData.shadowCenter||sun.userData.shadowCenter.distanceToSquared(center)>1e-12){
    sun.position.copy(center).addScaledVector(sun.userData.nativeTowardLight,180);sun.target.position.copy(center);
    sun.userData.shadowCenter=center.clone();renderer.shadowMap.needsUpdate=true;
  }
}
function addLights(){
  for(const item of manifest.lights){
    const m=world(anchors.lights.find(x=>x.name===item.name).matrix_world),color=new THREE.Color().fromArray(item.color);let light;
    if(item.type==='SUN'){
      light=new THREE.DirectionalLight(color,item.energy);sun=light;
      sun.userData.nativeTowardLight=new THREE.Vector3(0,0,1).transformDirection(m);
      sun.castShadow=true;sun.shadow.mapSize.set(4096,4096);Object.assign(sun.shadow.camera,{left:-55,right:55,top:55,bottom:-55,near:.1,far:400});
      sun.shadow.bias=-.00001;sun.shadow.normalBias=.006;sun.shadow.camera.updateProjectionMatrix();scene.add(sun.target);
    }else if(item.type==='AREA'){
      const disk=item.shape==='DISK',width=disk?item.size*Math.sqrt(Math.PI)/2:item.size;
      const height=item.shape==='RECTANGLE'?item.size_y:width;
      light=new THREE.RectAreaLight(color,1,width,height);light.power=item.energy;
      light.position.setFromMatrixPosition(m);light.quaternion.setFromRotationMatrix(m);
    }else throw new Error('Untranslated native light '+item.type);
    light.name=item.name;lightRoot.add(light);
  }
}
async function readManifest(){
  const response=await fetch(base+'runtime_native_matrix_manifest.json');if(!response.ok)throw new Error('Runtime package is not yet available');
  const next=await response.json();if(next.version!==version)throw new Error('Current-world version mismatch');
  if(manifest&&next.native_sha256!==manifest.native_sha256)throw new Error('Candidate native changed; reload for isolated review');
  manifest=next;manifestStamp=new Date().toISOString();
  if(!cameraSelect.options.length){
    const anchorResponse=await fetch(`./assets/${version}_runtime_anchors.json`);
    if(!anchorResponse.ok)throw new Error('Native world-matrix evidence is not yet available');
    anchors=await anchorResponse.json();
    if(anchors.native_sha256!==manifest.native_sha256||anchors.version!==version)throw new Error('Native anchor source differs');
    if(anchors.cameras.length!==manifest.camera_inventory.length||anchors.lights.length!==manifest.lights.length||
      manifest.camera_inventory.some(c=>!anchors.cameras.find(a=>a.name===c.name))||manifest.lights.some(c=>!anchors.lights.find(a=>a.name===c.name)))throw new Error('Camera/light world-matrix coverage differs');
    for(const c of manifest.camera_inventory.filter(c=>c.camera_type==='PERSP'&&!c.shift_x&&!c.shift_y).sort((a,b)=>a.name.localeCompare(b.name))){const option=document.createElement('option');option.value=c.name;option.textContent=c.name;cameraSelect.appendChild(option);}
    addLights();setCamera(new URLSearchParams(location.search).get('camera')||'BE_QA_ENTRY');
    renderer.toneMappingExposure=2**manifest.native_color.exposure;
  }
  for(const item of manifest.leaves)if(!leafMetadata.has(item.name)){
    const r=await fetch(base+item.metadata);if(!r.ok)throw new Error('Leaf metadata unavailable');const data=await r.json();
    if(data.native_sha256!==manifest.native_sha256||data.sha256!==item.sha256)throw new Error('Leaf source mismatch');
    const bounds=new THREE.Box3(new THREE.Vector3().fromArray(data.native_local_bounds[0]),new THREE.Vector3().fromArray(data.native_local_bounds[1])).applyMatrix4(world(data.object_matrix_world));
    leafMetadata.set(item.name,{...item,bounds});
  }
  refreshMetrics();
}
async function photo(){
  const [original,patch,response,hdr]=await Promise.all([
    loader.loadAsync('./assets/G1_004r2_photo_stream.glb'),loader.loadAsync(`./assets/${version}_context_delta.glb`),
    fetch(`./assets/${version}_context_delta.json`),new HDRLoader(manager).loadAsync(`./assets/${version}_sky.hdr`)]);
  const delta=await response.json();if(delta.native_sha256!==manifest.native_sha256)throw new Error('Photo/native version mismatch');
  photoRoot=original.scene;const binding=preparePhotoGeometryDelta({photoRoot,patchRoot:patch.scene,changedNodes:delta.changed_nodes,emptyNodes:delta.empty_nodes,version});binding.setActive(true);scene.add(photoRoot);
  const generator=new THREE.PMREMGenerator(renderer),environment=generator.fromEquirectangular(alignNativePanorama(hdr));scene.environment=environment.texture;hdr.dispose();generator.dispose();
}
async function upgradePhotoTextures(){
  camera.updateMatrixWorld();photoRoot.updateMatrixWorld(true);
  const frustum=new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse));
  const pixels=canvas.clientHeight/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))),candidates=new Map();
  photoRoot.traverse(o=>{
    if(!o.isMesh||!o.geometry.getAttribute('position')?.count)return;
    if(!o.geometry.boundingSphere)o.geometry.computeBoundingSphere();
    const sphere=o.geometry.boundingSphere.clone().applyMatrix4(o.matrixWorld);if(!frustum.intersectsSphere(sphere))return;
    const score=2*sphere.radius/Math.max(.2,camera.position.distanceTo(sphere.center)-sphere.radius)*pixels;
    for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.userData.runtime_texture_lod&&score>30){
      const previous=candidates.get(m);if(!previous||score>previous.score)candidates.set(m,{m,score,data:m.userData.runtime_texture_lod});
    }
  });
  const selected=new Map();let bytes=0,full=0,medium=0,unservedFull=0;
  for(const item of [...candidates.values()].sort((a,b)=>b.score-a.score)){
    const requestFull=item.score>128,nativeBytes=item.data.width*item.data.height*4*4/3;let tier;
    if(requestFull&&bytes+nativeBytes<=160*1024*1024){tier='full';bytes+=nativeBytes;full++;}
    else if(medium<128){tier='medium';medium++;if(requestFull)unservedFull++;}
    else{if(requestFull)unservedFull++;continue;}
    selected.set(item.m,{...item,tier});
  }
  for(const [material,item] of photoDetail)if(!selected.has(material)||selected.get(material).tier!==item.tier){material.map=item.original;item.texture.dispose();photoDetail.delete(material);}
  for(const [material,item] of selected){
    if(photoDetail.has(material))continue;
    const original=material.map,texture=await plainTextures.loadAsync('./assets/'+item.data[item.tier]);
    texture.flipY=false;texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=original.wrapS;texture.wrapT=original.wrapT;texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
    material.map=texture;photoDetail.set(material,{original,texture,tier:item.tier});
  }
  photoDetailStats={full,medium,full_requests_using_lower_tier:unservedFull,estimated_full_texture_mip_bytes:Math.round(bytes)};
}
async function loadGeometry(all=false){
  if(busy)return;busy=true;document.querySelectorAll('button,select').forEach(x=>x.disabled=true);
  try{
    const candidates=manifest.chunks.filter(c=>!chunks.has(c.file)&&(all||!c.bounds_yup||new THREE.Box3(new THREE.Vector3().fromArray(c.bounds_yup[0]),new THREE.Vector3().fromArray(c.bounds_yup[1])).distanceToPoint(camera.position)<nearRadius));
    for(const chunk of candidates){
      status.textContent='加载 '+chunk.collection;
      const asset=await loader.loadAsync(base+chunk.file),local=new Set();
      if(!chunk.native_matrix_restored)throw new Error('Native matrix restoration is missing');
      asset.scene.traverse(ob=>{
        const association=asset.parser.associations.get(ob),node=association?.nodes!==undefined?asset.parser.json.nodes[association.nodes]:null;
        if(node?.extras?.native_matrix_restored){
          if(!node.matrix||node.translation||node.rotation||node.scale)throw new Error('Native matrix representation differs');
          // Retain the matrix verbatim. Rebuilding it from decomposed TRS
          // reintroduces shear/round-off loss on these authored hierarchies.
          ob.matrix.fromArray(node.matrix);ob.matrixAutoUpdate=false;
        }
        if(ob.userData.native_object){if(identities.has(ob.userData.native_object))throw new Error('Duplicated author identity');local.add(ob.userData.native_object);}
        if(ob.isMesh){const materials=Array.isArray(ob.material)?ob.material:[ob.material];ob.castShadow=!materials.some(m=>m.transmission>.1);ob.receiveShadow=true;
          for(const m of materials)for(const name of ['map','normalMap','roughnessMap','metalnessMap'])if(m[name])m[name].anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());}
      });
      if(local.size!==chunk.native_objects.length||chunk.native_objects.some(n=>!local.has(n)))throw new Error('Author coverage differs from export');
      translatedHSVMaterials+=await hsvMaterials.apply(asset.scene);
      translatedFBMMaterials+=fbmMaterials.apply(asset.scene);
      asset.scene.updateMatrixWorld(true);
      local.forEach(n=>identities.add(n));scene.add(asset.scene);chunks.set(chunk.file,asset);
      renderer.shadowMap.needsUpdate=true;needsRender=true;
      if(asset.animations.length){const mixer=new THREE.AnimationMixer(asset.scene);asset.animations.forEach(clip=>mixer.clipAction(clip).play());
        const targets=[];asset.scene.traverse(o=>{if(o.isMesh&&o.morphTargetInfluences?.length)targets.push(o);});mixers.push({mixer,targets});}
      refreshMetrics();await new Promise(requestAnimationFrame);
    }
    for(const item of leafMetadata.values()){
      if(leaves.has(item.name)||(!all&&item.bounds.distanceToPoint(camera.position)>=nearRadius))continue;
      status.textContent='加载树冠 '+item.name;const pack=await loadNativeLeafPair(base+item.metadata);
      scene.add(pack.group);leaves.set(item.name,pack);identities.add(item.name);renderer.shadowMap.needsUpdate=true;needsRender=true;refreshMetrics();await new Promise(requestAnimationFrame);
    }
    status.textContent='加载机位中的原始摄影纹理';await upgradePhotoTextures();needsRender=true;
    status.textContent=`当前已载入 ${chunks.size}/${manifest.chunks.length} 组构件和 ${leaves.size}/50 组树冠；材质与自然使用仍待验收。`;
  }catch(error){errors.push(error.message);status.textContent='核验中止：'+error.message;console.error(error);}
  finally{busy=false;document.querySelectorAll('button,select').forEach(x=>x.disabled=false);refreshMetrics();}
}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
cameraSelect.onchange=()=>{setCamera(cameraSelect.value);status.textContent='机位已切换，可加载周边构件。';};
document.querySelector('#load-near').onclick=()=>loadGeometry(false);document.querySelector('#load-all').onclick=()=>loadGeometry(true);
document.querySelector('#refresh').onclick=async()=>{try{await readManifest();status.textContent='导出清单已更新。';}catch(e){status.textContent=e.message;}};
document.querySelector('#save-frame').onclick=()=>{renderer.render(scene,camera);canvas.toBlob(blob=>download(blob,`${version}_${cameraSelect.value}_runtime_candidate.png`),'image/png');};
document.querySelector('#save-report').onclick=()=>download(new Blob([JSON.stringify({manifest_read_utc:manifestStamp,camera:cameraSelect.value,...JSON.parse(metrics.textContent)},null,2)],{type:'application/json'}),`${version}_current_runtime_browser_report.json`);
let lastMetrics=0;const animationFrustum=new THREE.Frustum();
function draw(now){if(renderFailure)return;requestAnimationFrame(draw);const elapsed=now-lastFrame,dt=elapsed/1000;lastFrame=now;controls.update();updateSun();
  camera.updateMatrixWorld();animationFrustum.setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse));
  for(const item of mixers){item.mixer.update(dt);if(item.targets.some(mesh=>animationFrustum.intersectsObject(mesh)))needsRender=true;}
  if(needsRender){
    const started=performance.now();
    try{renderer.render(scene,camera);needsRender=false;}catch(error){renderFailure=error.message;errors.push(error.message);status.textContent='渲染核验中止：'+error.message;console.error(error);}
    if(!busy){frameTimes.push(performance.now()-started);if(frameTimes.length>90)frameTimes.shift();}
  }
  if(now-lastMetrics>1000){refreshMetrics();lastMetrics=now;}}
requestAnimationFrame(draw);
try{await readManifest();hsvMaterials=await loadNativeHSVMaterials(version,manifest.native_sha256);fbmMaterials=await loadNativeFBMMaterials(version,manifest.native_sha256);await photo();await loadGeometry(false);}catch(error){errors.push(error.message);status.textContent='核验未就绪：'+error.message;console.error(error);}
