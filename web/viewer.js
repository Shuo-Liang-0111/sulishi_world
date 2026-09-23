import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {loadBellevue} from './bellevue.js';
import {createReviewAntialias} from './review-antialias.js';

const canvas=document.querySelector('#world');
const scene=new THREE.Scene();scene.background=new THREE.Color('#89969e');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.AgXToneMapping;
const camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.1,5000);
const antialias=new URLSearchParams(location.search).get('aa')!=='raw'?createReviewAntialias(renderer,scene,camera):null;
let imageRevision=0;
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.dampingFactor=.1;controls.maxDistance=2000;
controls.minDistance=.7;controls.maxPolarAngle=Math.PI-.01;
const hemisphere=new THREE.HemisphereLight(0xd7e3ee,0x8b8273,1.5);scene.add(hemisphere);
const sun=new THREE.DirectionalLight(0xfff6e7,2.5);sun.position.set(-220,380,200);scene.add(sun);
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
// Geometry and the sun are static while orbiting. Reuse the same shadow texture
// through the 32 stationary AA samples; door motion and layer changes invalidate
// it explicitly below. This retains all geometry, shadow resolution and surfaces.
renderer.shadowMap.autoUpdate=false;
renderer.shadowMap.needsUpdate=true;
sun.castShadow=true;sun.target.position.set(-200,10,-138);scene.add(sun.target);
sun.position.set(-270,115,-200);sun.shadow.mapSize.set(2048,2048);
Object.assign(sun.shadow.camera,{left:-36,right:36,top:36,bottom:-36,near:.5,far:240});
sun.shadow.bias=-.0001;sun.shadow.normalBias=.015;
const raycaster=new THREE.Raycaster();
let root,ground,buildings=[],currentView='overview',ready=false,loadedVersion=null;
let sourceManifest,photoRoot=null,activeLayer='survey',loadingPhoto=false,scopeOutline=null;
let bellevue=null,loadingBellevue=false,lastFrame=0;
let shadowRevision='';
// Explicit inspection mode only. Keep isolated lighting comparisons available
// without changing construction materials or the normal visitor's controls.
if(new URLSearchParams(location.search).has('lighting-probe')){
  const box=document.createElement('div');box.id='lighting-probe';
  for(const [part,label] of [['environment','环境光'],['fixtures','室内灯'],['sun','日光'],['occlusion','几何遮蔽'],['native-diffuse','原生漫反射'],['case-distance','玻璃近背板采样']]){
    const button=document.createElement('button');button.textContent=`诊断：关闭${label}`;
    let enabled=true;
    button.onclick=()=>{
      if(!bellevue)return;
      enabled=!enabled;
      if(part==='sun')sun.visible=enabled;else bellevue.setLightingProbe(part,enabled);
      imageRevision++;button.textContent=`诊断：${enabled?'关闭':'恢复'}${label}`;
    };
    box.appendChild(button);
  }
  document.querySelector('aside').appendChild(box);
}
let wideView=false;
const photoMaterials=[];
const textureLoader=new THREE.TextureLoader();
const frustum=new THREE.Frustum(),viewProjection=new THREE.Matrix4();
let inflightTextures=0,lastLod=0;
canvas.addEventListener('webglcontextlost',()=>{
  document.querySelector('#notice').textContent='渲染上下文丢失，当前画面不可用；请重新载入。';
  console.error('Zurich review: WebGL context lost; no visual acceptance.');
});
const views={
  overview:{position:[-590,590,650],target:[0,15,-35]},
  top:{position:[35,1100,5.1],target:[35,0,5]},
  plaza:{ground:[-131,15],look:[-31,14,60]},
  bellevue:{ground:[-213,-106],look:[-200,11,-137]},
  station:{ground:[9,-40],look:[52,13,-79]}
};
function surfaceY(x,z){
  if(!ground)return null;
  raycaster.set(new THREE.Vector3(x,300,z),new THREE.Vector3(0,-1,0));
  const hits=raycaster.intersectObject(ground,true);
  return hits.length?hits[0].point.y:null;
}
function go(name){
  camera.fov=48;camera.updateProjectionMatrix();
  currentView=name;const v=views[name];
  wideView=!v.ground;
  if(scopeOutline)scopeOutline.visible=!v.ground;
  if(v.ground){
    const [x,z]=v.ground;const y=surfaceY(x,z);
    if(y===null){document.querySelector('#notice').textContent='该视点未命中测绘地形，未移动相机。';return;}
    camera.position.set(x,y+1.65,z);controls.target.fromArray(v.look);
  }else{camera.position.fromArray(v.position);controls.target.fromArray(v.target);}
  controls.update();
  if(v.ground){
    const floor=surfaceY(camera.position.x,camera.position.z);
    document.querySelector('#inspect').textContent=`预设相机离测绘地面 ${(camera.position.y-floor).toFixed(2)} m。当前自由观察不代表已通过步行碰撞检查。`;
  }
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
}
function resize(){renderer.setSize(innerWidth,innerHeight);if(antialias)antialias.resize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();}
addEventListener('resize',resize);resize();go('overview');
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));
document.querySelector('#reset').addEventListener('click',()=>go('overview'));
document.querySelector('#panel-toggle').addEventListener('click',e=>{
  const panel=e.target.closest('aside'),collapsed=panel.dataset.collapsed!=='true';
  panel.dataset.collapsed=String(collapsed);
  for(const child of panel.children)if(child!==e.target)child.hidden=collapsed;
  panel.style.width=collapsed?'120px':'';
  e.target.textContent=collapsed?'展开面板':'收起面板';
});
document.querySelector('#toggle-buildings').addEventListener('click',e=>{
  const visible=!buildings[0]?.visible;buildings.forEach(b=>b.visible=visible);
  imageRevision++;
  e.target.textContent=visible?'隐藏建筑参考':'显示建筑参考';
});
async function toggleSource(){
  if(loadingPhoto||!sourceManifest?.photogrammetry_ready)return;
  const button=document.querySelector('#toggle-source');
  if(bellevue)bellevue.setActive(false);
  hemisphere.intensity=1.5;hemisphere.visible=true;
  document.querySelector('#door-toggle').disabled=true;
  if(activeLayer==='photo'){
    photoRoot.visible=false;root.visible=true;activeLayer='survey';
    button.textContent='查看摄影网格';document.querySelector('#toggle-buildings').disabled=false;
    document.querySelector('#stage').textContent='测绘基底检查版 · 近景和自然交互尚未完成';
    document.querySelector('#source-note').textContent='独立楼体和地形来自测绘；航拍地面只用于位置对照。';
    document.querySelector('#stats').textContent=`${sourceManifest.survey_version} · ${buildings.length} 个参考对象（含周边）`;
    return;
  }
  loadingPhoto=true;button.disabled=true;
  try{
    if(!photoRoot){
      button.textContent='加载摄影网格…';
      if(!sourceManifest.photo_stream_gltf)throw new Error('分块纹理缓存尚未就绪');
      const gltf=await new GLTFLoader().loadAsync('./assets/'+sourceManifest.photo_stream_gltf,e=>{
        button.textContent=`加载摄影网格 ${Math.round(e.loaded/1024/1024)} MB`;
      });
      photoRoot=gltf.scene;scene.add(photoRoot);photoRoot.updateMatrixWorld(true);
      photoRoot.traverse(o=>{if(o.isMesh){
        o.geometry.computeBoundingSphere();
        const sphere=o.geometry.boundingSphere.clone().applyMatrix4(o.matrixWorld);
        const mats=Array.isArray(o.material)?o.material:[o.material];
        for(const m of mats)if(m.map){
          m.map.anisotropy=4;
          const data=m.userData.runtime_texture_lod;
          if(data)photoMaterials.push({material:m,base:m.map,sphere,data,tier:'low',desired:'low',pending:false});
        }
      }});
      if(photoMaterials.length!==sourceManifest.photo_nodes){
        const loaded=photoMaterials.length;
        scene.remove(photoRoot);photoRoot=null;photoMaterials.length=0;
        throw new Error(`摄影纹理未齐：${loaded}/${sourceManifest.photo_nodes}，未接受显示`);
      }
    }
    root.visible=false;photoRoot.visible=true;activeLayer='photo';
    button.textContent='返回测绘体量';document.querySelector('#toggle-buildings').disabled=true;
    document.querySelector('#stage').textContent='原始摄影网格参考 · 近景重建和自然交互尚未完成';
    document.querySelector('#source-note').textContent='2025 年摄影时相。近处加载原始纹理，远处按视距加载；原始模糊、粘连与临时设施仍待精修。';
    document.querySelector('#stats').textContent=`${sourceManifest.version} · ${sourceManifest.photo_nodes} 个来源分块 · G1 约 0.31 km²`;
  }catch(error){button.textContent='摄影网格加载失败，可重试';document.querySelector('#notice').textContent=error.message;console.error(error);}
  finally{loadingPhoto=false;button.disabled=false;}
}

async function showBellevue(cameraName='BE_QA_ENTRY'){
  if(loadingBellevue||loadingPhoto)return;
  loadingBellevue=true;const button=document.querySelector('#show-bellevue');button.disabled=true;
  try{
    if(!photoRoot)await toggleSource();
    if(!photoRoot)throw new Error('原始摄影背景尚未载入');
    if(!bellevue)bellevue=await loadBellevue({scene,renderer,photoRoot,version:sourceManifest.construction_version});
    root.visible=false;photoRoot.visible=true;bellevue.setActive(true);activeLayer='construction';
    const nativeSun=bellevue.metadata.sun_lights?.[0];
    if(nativeSun){
      sun.color.fromArray(nativeSun.color);sun.intensity=nativeSun.energy;
      sun.position.copy(sun.target.position).addScaledVector(new THREE.Vector3().fromArray(nativeSun.direction_to_sun),150);
      renderer.shadowMap.needsUpdate=true;
    }
    // Remove the unused survey light from the active light list. On the current
    // Intel/ANGLE + r180 renderer, an otherwise identical zero-intensity hemi
    // light reproducibly creates black transmission rectangles. Visibility=false
    // preserves its intended zero contribution without retaining that shader path.
    hemisphere.visible=false;
    const view=bellevue.metadata.cameras[cameraName];camera.position.fromArray(view.position);controls.target.fromArray(view.target);
    wideView=['BE_QA_STRUCTURE','BE_QA_STATION_STREETS'].includes(cameraName);
    camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(view.fov/2))*Math.max(1,(1600/1050)/camera.aspect)));
    camera.updateProjectionMatrix();controls.update();currentView=cameraName;scopeOutline.visible=false;
    document.querySelector('#stage').textContent='Bellevue 实体施工版 · 全街区仍在复原';
    document.querySelector('#source-note').textContent='亭体按测绘与实拍重建；周边仍保留待精修的摄影资料。室内设备、细部与照明尚在核验。';
    document.querySelector('#inspect').textContent=`${bellevue.metadata.exported_authored_objects} 个原生对象已载入，包含可开合入口；当前仍为自由观察。`;
    document.querySelector('#toggle-source').textContent='查看原始摄影对照';
    document.querySelector('#toggle-buildings').disabled=true;
    document.querySelector('#door-toggle').disabled=false;
    document.querySelector('#crossing-views').hidden=!bellevue.metadata.cameras.BE_QA_CROSSING_WEST;
    document.querySelector('#station-views').hidden=!bellevue.metadata.cameras.BE_QA_STATION_STREETS;
    document.querySelector('#west-views').hidden=!bellevue.metadata.cameras.BE_QA_WEST_PLATFORM;
    document.querySelector('#haus-views').hidden=!bellevue.metadata.cameras.HB_QA_ALONG;
    document.querySelector('#fountain-views').hidden=!bellevue.metadata.cameras.BE_QA_FOUNTAIN_RIM;
    document.querySelectorAll('[data-be-view]').forEach(b=>b.disabled=!bellevue.metadata.cameras[b.dataset.beView]);
  }catch(error){document.querySelector('#notice').textContent=error.message;console.error(error);}
  finally{loadingBellevue=false;button.disabled=false;}
}
document.querySelector('#show-bellevue').addEventListener('click',()=>showBellevue());
document.querySelectorAll('[data-be-view]').forEach(button=>button.addEventListener('click',()=>showBellevue(button.dataset.beView)));
document.querySelector('#door-toggle').addEventListener('click',e=>{
  if(!bellevue||activeLayer!=='construction')return;
  const opening=bellevue.toggleDoor();e.target.textContent=opening?'关闭亭体入口':'打开亭体入口';
  document.querySelector('#inspect').textContent=opening?'入口门向两侧收起。门机构为照片约束的重建，尚未验收行人防夹。':'入口门正在关闭。当前为机构检查，步行碰撞尚未开放。';
});
document.querySelector('#toggle-source').addEventListener('click',toggleSource);
let down;
canvas.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);
canvas.addEventListener('pointerup',e=>{
  if(!ready||!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;
  raycaster.setFromCamera(new THREE.Vector2(e.clientX/innerWidth*2-1,1-e.clientY/innerHeight*2),camera);
  const hit=activeLayer==='construction'?raycaster.intersectObject(bellevue.root,true)[0]:activeLayer==='photo'?raycaster.intersectObject(photoRoot,true)[0]:
    raycaster.intersectObjects(buildings.filter(b=>b.visible),true)[0];
  if(!hit)return;
  if(activeLayer==='construction'){
    let obj=hit.object;while(obj.parent&&!obj.userData.native_object)obj=obj.parent;
    document.querySelector('#inspect').textContent=`${obj.userData.native_object||obj.name} · ${obj.userData.evidence_basis||'本地重建构件'}。`;return;
  }
  if(activeLayer==='photo'){
    document.querySelector('#inspect').textContent=`${hit.object.name} · 原始摄影分块；暂未接受为独立可交互建筑。`;
    return;
  }
  let obj=hit.object;while(obj.parent&&obj.userData.kind!=='survey_building')obj=obj.parent;
  let p={};try{p=JSON.parse(obj.userData.source_properties||'{}');}catch{}
  const text=`${obj.name} · ${p.art_txt||'建筑参考'}\n来源：官方 Dachmodell。首层、门窗与内部尚未精修；模型底面不是入口楼板。`;
  document.querySelector('#inspect').textContent=text;
});
try{
  const preview=new URLSearchParams(location.search).get('preview');
  const manifests={bellevue:'./assets/bellevue_preview.json',station:'./assets/station_preview.json'};
  const response=await fetch(manifests[preview]||'./assets/current.json');if(!response.ok)throw new Error('版本清单无法读取');
  const version=await response.json();
  document.querySelector('#station-views').hidden=!String(version.construction_version||'').startsWith('G1_007');
  sourceManifest=version;
  loadedVersion=version.version;
  const gltf=await new GLTFLoader().loadAsync('./assets/'+version.survey_glb);
  root=gltf.scene;scene.add(root);root.updateMatrixWorld(true);
  root.traverse(o=>{
    if(o.userData.kind==='terrain_reference')ground=o;
    if(o.userData.kind==='survey_building')buildings.push(o);
    if(o.isMesh){o.frustumCulled=true;const mats=Array.isArray(o.material)?o.material:[o.material];
      for(const m of mats)if(m.map)m.map.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());}
  });
  if(!ground||!buildings.length)throw new Error('导出缺少地形或建筑身份，停止检查');
  const scopeResponse=await fetch('./assets/g1_scope.geojson');
  if(!scopeResponse.ok)throw new Error('G1施工范围无法读取');
  const scope=await scopeResponse.json();
  scopeOutline=new THREE.Group();scopeOutline.name='G1_construction_boundary_review_only';
  const boundaryMaterial=new THREE.LineBasicMaterial({color:0xf6d586,transparent:true,opacity:.8,depthTest:false});
  for(const feature of scope.features){
    const polygons=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
    for(const polygon of polygons)for(const ring of polygon){
      const points=ring.map(([e,n])=>{const x=e-2683775,z=1246700-n;return new THREE.Vector3(x,(surfaceY(x,z)??0)+.4,z);});
      const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),boundaryMaterial);
      line.renderOrder=20;scopeOutline.add(line);
    }
  }
  scene.add(scopeOutline);scopeOutline.visible=!views[currentView].ground;
  ready=true;document.querySelectorAll('button').forEach(b=>b.disabled=false);
  document.querySelector('#toggle-source').disabled=!version.photogrammetry_ready;
  document.querySelector('#show-bellevue').disabled=!version.construction_version;
  document.querySelector('#door-toggle').disabled=true;
  if(version.photogrammetry_ready)document.querySelector('#toggle-source').textContent='查看摄影网格';
  document.querySelector('#stats').textContent=`${version.survey_version||version.version} · ${buildings.length} 个参考对象（含周边） · G1 约 0.31 km²`;
  document.querySelector('#loading').classList.add('hidden');
  const requestedView=new URLSearchParams(location.search).get('view');
  if(requestedView&&[...document.querySelectorAll('[data-be-view]')].some(b=>b.dataset.beView===requestedView)){
    await showBellevue(requestedView);
  }
}catch(error){document.querySelector('#loading').textContent=`加载未完成：${error.message}`;console.error(error);}
function requestTier(rec,tier){
  if(rec.pending||inflightTextures>=4)return;
  rec.pending=true;inflightTextures++;
  textureLoader.load('./assets/'+rec.data[tier],texture=>{
    rec.pending=false;inflightTextures--;
    if(rec.desired!==tier||activeLayer==='survey'){texture.dispose();return;}
    texture.flipY=false;texture.colorSpace=THREE.SRGBColorSpace;
    texture.wrapS=rec.base.wrapS;texture.wrapT=rec.base.wrapT;
    texture.anisotropy=4;
    const old=rec.material.map;rec.material.map=texture;rec.tier=tier;
    imageRevision++;
    if(old!==rec.base)old.dispose();
  },undefined,error=>{rec.pending=false;inflightTextures--;console.error('Reference texture load failed',error);});
}
function updateTextureLod(now){
  if(activeLayer==='survey'||now-lastLod<500)return;
  lastLod=now;camera.updateMatrixWorld();
  viewProjection.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);
  frustum.setFromProjectionMatrix(viewProjection);
  const pixels=innerHeight/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov*.5)));
  const candidates=[];
  for(const rec of photoMaterials){
    rec.desired='low';
    if(!frustum.intersectsSphere(rec.sphere))continue;
    const distance=Math.max(1,camera.position.distanceTo(rec.sphere.center)-rec.sphere.radius);
    const score=rec.sphere.radius*2/distance*pixels;
    if(score>80)candidates.push({rec,score});
  }
  candidates.sort((a,b)=>b.score-a.score);
  let fullCount=0,fullBytes=0,mediumCount=0;
  for(const {rec,score} of candidates){
    const bytes=rec.data.width*rec.data.height*4;
    if(score>200&&fullCount<72&&fullBytes+bytes<96*1024*1024){
      rec.desired='full';fullCount++;fullBytes+=bytes;
    }else if(mediumCount<96){rec.desired='medium';mediumCount++;}
  }
  for(const rec of photoMaterials){
    if(rec.desired==='low'&&rec.tier!=='low'){
      const old=rec.material.map;rec.material.map=rec.base;rec.tier='low';if(old!==rec.base)old.dispose();
      imageRevision++;
    }
  }
  for(const {rec} of candidates)if(rec.desired!==rec.tier&&rec.desired!=='low')requestTier(rec,rec.desired);
  document.querySelector('#stats').textContent=`${activeLayer==='construction'?sourceManifest.construction_version:'G1_004r2'} · ${sourceManifest.photo_nodes} 来源分块 · 近景原始纹理 ${photoMaterials.filter(r=>r.tier==='full').length} 块`;
}
function animate(now=0){requestAnimationFrame(animate);if(bellevue)bellevue.update(Math.min((now-lastFrame)/1000,.05),Math.max(0,(now-lastFrame)/1000));lastFrame=now;controls.update();
  const nextShadowRevision=[activeLayer,!!bellevue,bellevue?.getDoorState().current].join(':');
  if(nextShadowRevision!==shadowRevision){renderer.shadowMap.needsUpdate=true;shadowRevision=nextShadowRevision;}
  // Keep millimetre-scale coatings separable in wide views. This alone did not
  // resolve subpixel roof aliasing; stationary multisampling handles that.
  const near=wideView?Math.min(.8,Math.max(.08,camera.position.distanceTo(controls.target)*.1)):.08;
  if(Math.abs(camera.near-near)>.001){camera.near=near;camera.updateProjectionMatrix();}
  updateTextureLod(now);
  if(antialias)antialias.render(now,[imageRevision,ready,activeLayer,!!bellevue,bellevue?.getDoorState().current].join(':'),activeLayer==='construction'&&bellevue?.fountainWater?.visibleFrom(camera));
  else renderer.render(scene,camera);}
animate();
// Diagnostic state is deliberately separate from the public UI and contains no agent controls.
window.zurichReview={getState:()=>({ready,version:loadedVersion,view:currentView,activeLayer,
  camera:camera.position.toArray(),target:controls.target.toArray(),buildings:buildings.length,
  calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,
  accumulatedSamples:antialias?.getSamples()||0,
  fountainWater:bellevue?.fountainWater?.getState()||null,
  status:'source_reference_not_accepted',walking:false}),go};
