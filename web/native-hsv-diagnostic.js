import * as THREE from 'three';
import {loadNativeHSVMaterials} from './native-hsv-materials.js';

const version='G1_027r15',sha='496397518d867f64a0ea2f8052b0247881ef0bbd9c5aa570a9857e71e6cf2b9d';
const status=document.querySelector('#status'),reportElement=document.querySelector('#report');
const production=await loadNativeHSVMaterials(version,sha);
const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setSize(1,1);renderer.toneMapping=THREE.NoToneMapping;renderer.outputColorSpace=THREE.LinearSRGBColorSpace;
const target=new THREE.WebGLRenderTarget(1,1,{type:THREE.FloatType,format:THREE.RGBAFormat,colorSpace:THREE.LinearSRGBColorSpace,depthBuffer:false,stencilBuffer:false});
const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-1,1,1,-1,0,2);camera.position.z=1;
const pixels=new Float32Array(4),swatches=document.querySelector('#swatches').getContext('2d'),rows=[];
const points=[[.137,.239],[.513,.717],[1.213,-.311],[-.467,1.357],[.847,.421],[2.371,3.169]];
const linear=c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4;
const srgb=c=>c<=.0031308?12.92*c:1.055*c**(1/2.4)-.055;
function independentHSV(rgb,saturation,value){
  const hi=Math.max(...rgb),lo=Math.min(...rgb),chroma=hi-lo;
  let hue=0;
  if(chroma){if(hi===rgb[0])hue=((rgb[1]-rgb[2])/chroma)%6;else if(hi===rgb[1])hue=(rgb[2]-rgb[0])/chroma+2;else hue=(rgb[0]-rgb[1])/chroma+4;}
  hue=(hue/6+1)%1;const sat=hi===0?0:chroma/hi;
  const vv=hi*value,cc=vv*sat*saturation,hh=hue*6,xx=cc*(1-Math.abs(hh%2-1)),offset=vv-cc;
  const basis=hh<1?[cc,xx,0]:hh<2?[xx,cc,0]:hh<3?[0,cc,xx]:hh<4?[0,xx,cc]:hh<5?[xx,0,cc]:[cc,0,xx];
  return basis.map(c=>c+offset);
}
let result;
try{
  for(const recipe of production.metadata.materials){
    const mesh=new THREE.Mesh(new THREE.PlaneGeometry(2,2),new THREE.MeshBasicMaterial());mesh.material.name=recipe.name;scene.add(mesh);
    await production.apply(scene);const map=mesh.material.map;map.generateMipmaps=false;map.minFilter=map.magFilter=THREE.NearestFilter;map.anisotropy=1;map.needsUpdate=true;
    const original=document.createElement('canvas');original.width=map.image.width;original.height=map.image.height;
    const context=original.getContext('2d',{willReadFrequently:true});context.drawImage(map.image,0,0);const image=context.getImageData(0,0,original.width,original.height).data;
    const samples=[];
    for(const [u,v] of points){
      const uv=mesh.geometry.getAttribute('uv');for(let i=0;i<uv.count;i++)uv.setXY(i,u,v);uv.needsUpdate=true;
      // Reproduce the independent native UV operation, not Three's matrix.
      const nativeU=u*recipe.mapping.scale[0],nativeV=(1-v)*recipe.mapping.scale[1],theta=recipe.mapping.rotation[2];
      const uu=Math.cos(theta)*nativeU-Math.sin(theta)*nativeV+recipe.mapping.location[0];
      const vv=Math.sin(theta)*nativeU+Math.cos(theta)*nativeV+recipe.mapping.location[1];
      const fx=uu-Math.floor(uu),fy=1-vv-Math.floor(1-vv),x=Math.floor(fx*original.width),y=Math.floor(fy*original.height),offset=4*(y*original.width+x);
      const source=[image[offset],image[offset+1],image[offset+2]].map(x=>linear(x/255));
      const expected=independentHSV(source,recipe.saturation,recipe.value);
      renderer.setRenderTarget(target);renderer.render(scene,camera);renderer.readRenderTargetPixels(target,0,0,1,1,pixels);
      const actual=Array.from(pixels.slice(0,3)),error=Math.max(...expected.map((x,i)=>Math.abs(x-actual[i])));
      samples.push({gltf_uv:[u,v],source_pixel:[x,y],expected_linear_rgb:expected,actual_linear_rgb:actual,max_linear_rgb_error:error});
    }
    const activePrograms=renderer.info.programs.length;
    const shaderErrors=renderer.info.programs.filter(p=>p.diagnostics?.runnable===false).length;
    if(!activePrograms||shaderErrors)throw new Error('Actual material shader did not compile successfully');
    rows.push({material:recipe.name,source_image_sha256:recipe.image_sha256,active_programs_when_rendered:activePrograms,shader_errors:shaderErrors,samples});
    const index=rows.length-1;
    for(let p=0;p<points.length;p++){
      const sample=samples[p],x=index*128+p*20;
      swatches.fillStyle='rgb('+sample.expected_linear_rgb.map(c=>Math.round(255*srgb(c))).join(',')+')';swatches.fillRect(x,0,20,64);
      swatches.fillStyle='rgb('+sample.actual_linear_rgb.map(c=>Math.round(255*srgb(c))).join(',')+')';swatches.fillRect(x,64,20,64);
    }
    scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();map.dispose();
  }
  const max=Math.max(...rows.flatMap(x=>x.samples.map(x=>x.max_linear_rgb_error)));
  result={version,native_sha256:sha,source:'actual source images and production onBeforeCompile translation',materials:rows,
    independent_reference:'Native POINT UV operation and explicit RGB to HSV to RGB; nearest sampling for isolated channel check.',
    max_linear_rgb_error:max,tolerance:.001,passed:max<.001,
    maximum_active_programs:Math.max(...rows.map(x=>x.active_programs_when_rendered)),shader_errors:rows.reduce((sum,x)=>sum+x.shader_errors,0),
    native_render_equivalence:false,full_runtime_published:false};
  status.textContent=result.passed?'通道核验通过；完整原生画面仍待比较。':'通道核验失败，禁止当作已通过的材质使用。';
}catch(error){result={version,passed:false,error:error.message,materials:rows,native_render_equivalence:false};status.textContent='核验中止：'+error.message;console.error(error);}
reportElement.textContent=JSON.stringify(result,null,2);document.querySelector('#save').disabled=false;
document.querySelector('#save').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=version+'_hsv_browser_report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
renderer.setRenderTarget(null);target.dispose();renderer.dispose();
