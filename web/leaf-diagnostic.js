import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {loadNativeLeafPair} from './native-leaf-instances.js';
const canvas=document.querySelector('#canvas'),status=document.querySelector('#status'),metrics=document.querySelector('#metrics');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.AgXToneMapping;
const scene=new THREE.Scene();scene.background=new THREE.Color('#8e9da5');
const camera=new THREE.PerspectiveCamera(48,1,.02,2000);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;
const sun=new THREE.DirectionalLight(0xfff1de,3),hemi=new THREE.HemisphereLight(0xd2e8ff,0x494438,1.1);
scene.add(sun,sun.target,hemi);
function resize(){const w=canvas.clientWidth,h=canvas.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
addEventListener('resize',resize);resize();
let pair,busy=false,lastReport=null;
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function draw(){requestAnimationFrame(draw);if(!busy){controls.update();renderer.render(scene,camera);}}draw();
async function compare(){
  busy=true;document.querySelector('#compare').disabled=true;
  const savedPosition=camera.position.clone(),savedQuaternion=camera.quaternion.clone(),aspect=camera.aspect;
  const center=pair.worldBounds.getCenter(new THREE.Vector3()),size=pair.worldBounds.getSize(new THREE.Vector3()),radius=size.length()/2;
  const width=640,height=480,target=new THREE.WebGLRenderTarget(width,height,{depthBuffer:true});
  const results=[];
  try{
    camera.aspect=width/height;camera.updateProjectionMatrix();
    for(const [name,direction,distance] of [['north',[0,.15,1],2.9],['east',[1,.2,0],2.9],['under',[.2,-.7,.8],1.6],['close',[-.4,.1,.9],1.35]]){
      camera.position.copy(center).addScaledVector(new THREE.Vector3(...direction).normalize(),radius*distance);
      camera.lookAt(center);camera.updateMatrixWorld(true);
      sun.position.copy(center).add(new THREE.Vector3(25,18,12));sun.target.position.copy(center);
      pair.reference.visible=false;pair.instanced.visible=false;
      renderer.setRenderTarget(target);renderer.render(scene,camera);
      const background=new Uint8Array(width*height*4);renderer.readRenderTargetPixels(target,0,0,width,height,background);
      const images=[];
      for(const mode of ['reference','instanced']){
        pair.setMode(mode);renderer.setRenderTarget(target);renderer.render(scene,camera);
        const pixels=new Uint8Array(width*height*4);renderer.readRenderTargetPixels(target,0,0,width,height,pixels);images.push(pixels);
      }
      let total=0,max=0,different=0,referenceForeground=0,instanceForeground=0;
      for(let p=0;p<width*height;p++){
        let pixelMax=0,foregroundA=0,foregroundB=0;
        for(let c=0;c<3;c++){
          const d=Math.abs(images[0][p*4+c]-images[1][p*4+c]);total+=d*d;max=Math.max(max,d);pixelMax=Math.max(pixelMax,d);
          foregroundA=Math.max(foregroundA,Math.abs(images[0][p*4+c]-background[p*4+c]));
          foregroundB=Math.max(foregroundB,Math.abs(images[1][p*4+c]-background[p*4+c]));
        }
        if(pixelMax>2)different++;if(foregroundA>2)referenceForeground++;if(foregroundB>2)instanceForeground++;
      }
      results.push({view:name,rms_8bit:Math.sqrt(total/(width*height*3)),max_8bit:max,pixels_over_2:different,
        reference_foreground_pixels:referenceForeground,instance_foreground_pixels:instanceForeground,total_pixels:width*height});
    }
    const report={version:pair.metadata.version,native_sha256:pair.metadata.native_sha256,position_policy:pair.metadata.position_policy||'affine',binary_sha256:pair.metadata.sha256,views:results,
      shader_errors:renderer.info.programs.filter(p=>p.diagnostics?.runnable===false).length,
      full_runtime_published:false,native_material_equivalence:false};
    report.comparison_passed=report.shader_errors===0&&results.every(r=>r.reference_foreground_pixels>1000&&r.instance_foreground_pixels>1000&&r.rms_8bit<.2&&r.pixels_over_2/r.total_pixels<.002);
    lastReport=report;document.querySelector('#save-report').disabled=false;
    metrics.textContent=JSON.stringify(report,null,2);metrics.dataset.complete='true';
    status.textContent=report.comparison_passed?'四角度数值对比通过；仍需独立查看画面。':'四角度对比未通过，保留原始表示。';
  }finally{
    renderer.setRenderTarget(null);target.dispose();camera.position.copy(savedPosition);camera.quaternion.copy(savedQuaternion);camera.aspect=aspect;camera.updateProjectionMatrix();
    pair.setMode(lastReport?.comparison_passed?'instanced':'reference');busy=false;document.querySelector('#compare').disabled=false;
  }
}
try{
  pair=await loadNativeLeafPair('./assets/G1_027r15_leaf_diagnostic/tree_exact.json');scene.add(pair.group);
  const center=pair.worldBounds.getCenter(new THREE.Vector3()),radius=pair.worldBounds.getSize(new THREE.Vector3()).length()/2;
  camera.position.copy(center).add(new THREE.Vector3(1,.35,1).normalize().multiplyScalar(radius*2.7));controls.target.copy(center);controls.update();
  sun.position.copy(center).add(new THREE.Vector3(25,18,12));sun.target.position.copy(center);
  for(const mode of ['reference','instanced']){const button=document.querySelector('#'+mode);button.disabled=false;button.onclick=()=>{pair.setMode(mode);status.textContent=mode==='reference'?'显示原始叶片':'显示紧凑表示';};}
  document.querySelector('#compare').disabled=false;document.querySelector('#compare').onclick=compare;
  const closeButton=document.querySelector('#close-view');closeButton.disabled=false;
  closeButton.onclick=()=>{camera.position.copy(center).addScaledVector(new THREE.Vector3(-.4,.1,.9).normalize(),radius*1.35);controls.target.copy(center);controls.update();status.textContent='近景检查';};
  document.querySelector('#save-report').onclick=()=>download(new Blob([JSON.stringify(lastReport,null,2)],{type:'application/json'}),'G1_027r15_leaf_browser_report.json');
  const saveFrame=document.querySelector('#save-frame');saveFrame.disabled=false;
  saveFrame.onclick=()=>{renderer.render(scene,camera);canvas.toBlob(blob=>download(blob,'G1_027r15_leaf_browser_frame.png'),'image/png');};
  status.textContent='已加载同版原始几何与紧凑表示。';
  await compare();
}catch(error){status.textContent='核验失败：'+error.message;console.error(error);}
