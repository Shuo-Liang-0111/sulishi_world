import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {loadNativeLeafPair} from './native-leaf-instances.js';
const canvas=document.querySelector('#canvas'),status=document.querySelector('#status'),metrics=document.querySelector('#metrics');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.AgXToneMapping;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
const scene=new THREE.Scene();scene.background=new THREE.Color('#8e9da5');
const camera=new THREE.PerspectiveCamera(48,1,.02,2000),controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;
const sun=new THREE.DirectionalLight(0xfff1de,3),point=new THREE.PointLight(0xfff1de,1),hemi=new THREE.HemisphereLight(0xd2e8ff,0x494438,.65);
scene.add(sun,sun.target,point,hemi);sun.castShadow=point.castShadow=true;
for(const light of [sun,point]){light.shadow.mapSize.set(1024,1024);light.shadow.bias=-.00001;light.shadow.normalBias=0;}
let pair,center,radius,ground,busy=false,lastReport=null,lightMode='sun';
function resize(){renderer.setSize(canvas.clientWidth,canvas.clientHeight,false);camera.aspect=canvas.clientWidth/canvas.clientHeight;camera.updateProjectionMatrix();}
addEventListener('resize',resize);resize();
function draw(){requestAnimationFrame(draw);if(!busy){controls.update();renderer.render(scene,camera);}}draw();
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function lighting(mode){lightMode=mode;sun.visible=mode==='sun';point.visible=mode==='point';renderer.shadowMap.needsUpdate=true;}
function overview(){
  camera.position.copy(center).add(new THREE.Vector3(1.25,.95,1.25).normalize().multiplyScalar(radius*3.6));
  controls.target.copy(center).add(new THREE.Vector3(0,-radius*.4,0));controls.update();
}
function difference(a,b){
  let squared=0,max=0,over2=0,over4=0;
  for(let p=0;p<a.length/4;p++){
    let pixelMax=0;
    for(let c=0;c<3;c++){const d=Math.abs(a[p*4+c]-b[p*4+c]);squared+=d*d;max=Math.max(max,d);pixelMax=Math.max(pixelMax,d);}
    if(pixelMax>2)over2++;if(pixelMax>4)over4++;
  }
  return {rms_8bit:Math.sqrt(squared/(a.length/4*3)),max_8bit:max,pixels_over_2:over2,pixels_over_4:over4};
}
async function compare(){
  busy=true;document.querySelector('#compare').disabled=true;lastReport=null;
  const saved={position:camera.position.clone(),quaternion:camera.quaternion.clone(),aspect:camera.aspect,lightMode};
  const width=640,height=480,target=new THREE.WebGLRenderTarget(width,height,{depthBuffer:true}),results=[];
  try{
    camera.aspect=width/height;camera.updateProjectionMatrix();
    for(const [name,mode,position,selfShadow] of [
      ['sun_overview','sun',[1.25,.95,1.25],false],['sun_reverse','sun',[-1,.85,.9],false],
      ['point_overview','point',[1.25,.95,1.25],false],['sun_self','sun',[1.25,.95,1.25],true],
      ['point_self','point',[1.25,.95,1.25],true]]){
      pair.reference.receiveShadow=pair.instanced.receiveShadow=selfShadow;
      lighting(mode);camera.position.copy(center).addScaledVector(new THREE.Vector3(...position).normalize(),radius*3.6);
      camera.lookAt(center.clone().add(new THREE.Vector3(0,-radius*.4,0)));camera.updateMatrixWorld(true);
      const images=[],unshadowed=[];
      for(const representation of ['reference','instanced']){
        pair.setMode(representation);const mesh=pair[representation];
        for(const casts of [true,false]){
          mesh.castShadow=casts;renderer.shadowMap.needsUpdate=true;renderer.setRenderTarget(target);renderer.render(scene,camera);
          const pixels=new Uint8Array(width*height*4);renderer.readRenderTargetPixels(target,0,0,width,height,pixels);
          (casts?images:unshadowed).push(pixels);
        }
        mesh.castShadow=true;
      }
      const d=difference(images[0],images[1]);
      results.push({view:name,light:mode,self_shadow:selfShadow,...d,total_pixels:width*height,
        reference_shadow_pixels:difference(images[0],unshadowed[0]).pixels_over_4,
        compact_shadow_pixels:difference(images[1],unshadowed[1]).pixels_over_4});
    }
    lastReport={version:pair.metadata.version,native_sha256:pair.metadata.native_sha256,binary_sha256:pair.metadata.sha256,
      object:pair.metadata.native_object,position_policy:pair.metadata.position_policy,views:results,
      shader_errors:renderer.info.programs.filter(p=>p.diagnostics?.runnable===false).length,
      depth_material:pair.instanced.customDepthMaterial?.type,distance_material:pair.instanced.customDistanceMaterial?.type,
      shadow_type:'PCFShadowMap',map_resolution:1024,self_shadow_tested:true,native_material_equivalence:false,full_runtime_published:false};
    lastReport.comparison_passed=lastReport.shader_errors===0&&results.every(r=>r.reference_shadow_pixels>100&&r.compact_shadow_pixels>100&&r.rms_8bit<.2&&r.pixels_over_2/r.total_pixels<.002);
    metrics.textContent=JSON.stringify(lastReport,null,2);metrics.dataset.complete='true';document.querySelector('#save-report').disabled=false;
    status.textContent=lastReport.comparison_passed?'五组地面及自身阴影对比通过；请查看实际画面。':'投影核验未通过，保留原始表示。';
  }finally{
    renderer.setRenderTarget(null);target.dispose();camera.position.copy(saved.position);camera.quaternion.copy(saved.quaternion);camera.aspect=saved.aspect;camera.updateProjectionMatrix();
    lighting(saved.lightMode);pair.reference.castShadow=pair.instanced.castShadow=true;
    pair.reference.receiveShadow=pair.instanced.receiveShadow=true;
    pair.setMode(lastReport?.comparison_passed?'instanced':'reference');busy=false;document.querySelector('#compare').disabled=false;
  }
}
try{
  pair=await loadNativeLeafPair('./assets/G1_027r15_leaf_diagnostic/tree_exact.json');scene.add(pair.group);
  center=pair.worldBounds.getCenter(new THREE.Vector3());radius=pair.worldBounds.getSize(new THREE.Vector3()).length()/2;
  pair.reference.receiveShadow=pair.instanced.receiveShadow=false;
  ground=new THREE.Mesh(new THREE.PlaneGeometry(radius*12,radius*12),new THREE.MeshStandardMaterial({color:'#b9b5a9',roughness:1}));
  ground.rotation.x=-Math.PI/2;ground.position.set(center.x,pair.worldBounds.min.y-radius*.5,center.z);ground.receiveShadow=true;scene.add(ground);
  sun.position.copy(center).addScaledVector(new THREE.Vector3(8,18,7).normalize(),radius*4);sun.target.position.copy(center);
  Object.assign(sun.shadow.camera,{left:-radius*4,right:radius*4,top:radius*4,bottom:-radius*4,near:.1,far:radius*12});sun.shadow.camera.updateProjectionMatrix();
  point.position.copy(center).add(new THREE.Vector3(radius*.9,radius*1.7,radius*.8));point.intensity=radius*radius*30;point.shadow.camera.near=.1;point.shadow.camera.far=radius*15;
  lighting('sun');overview();
  for(const mode of ['reference','instanced']){const button=document.querySelector('#'+mode);button.disabled=false;button.onclick=()=>{pair.setMode(mode);status.textContent=mode==='reference'?'显示原始投影':'显示紧凑表示投影';};}
  for(const mode of ['sun','point']){const button=document.querySelector('#'+mode);button.disabled=false;button.onclick=()=>{lighting(mode);status.textContent=mode==='sun'?'太阳光投影':'点光源投影';};}
  document.querySelector('#compare').disabled=false;document.querySelector('#compare').onclick=compare;
  document.querySelector('#save-report').onclick=()=>download(new Blob([JSON.stringify(lastReport,null,2)],{type:'application/json'}),'G1_027r15_leaf_shadow_report.json');
  const saveFrame=document.querySelector('#save-frame');saveFrame.disabled=false;saveFrame.onclick=()=>{renderer.render(scene,camera);canvas.toBlob(blob=>download(blob,'G1_027r15_leaf_shadow_frame.png'),'image/png');};
  await compare();
}catch(error){status.textContent='核验失败：'+error.message;console.error(error);}
