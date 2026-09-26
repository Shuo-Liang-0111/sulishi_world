import * as THREE from 'three';
import {nativeFBMGLSL} from './native-fbm.js';
const version='G1_027r15',sha='496397518d867f64a0ea2f8052b0247881ef0bbd9c5aa570a9857e71e6cf2b9d';
const status=document.querySelector('#status'),swatches=document.querySelector('#swatches').getContext('2d');let result;
const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setSize(1,1);renderer.toneMapping=THREE.NoToneMapping;renderer.outputColorSpace=THREE.LinearSRGBColorSpace;
const target=new THREE.WebGLRenderTarget(1,1,{type:THREE.FloatType,format:THREE.RGBAFormat,colorSpace:THREE.LinearSRGBColorSpace,depthBuffer:false,stencilBuffer:false});
const material=new THREE.ShaderMaterial({glslVersion:THREE.GLSL3,uniforms:{p:{value:new THREE.Vector3()},scale:{value:1},detail:{value:1},roughness:{value:.5},lacunarity:{value:2},normalized:{value:true}},
  vertexShader:'void main(){gl_Position=vec4(position.xy,0.,1.);}',
  fragmentShader:nativeFBMGLSL+'\nuniform vec3 p; uniform float scale, detail, roughness, lacunarity; uniform bool normalized; out vec4 outputColour; void main(){float f=zNativeFBM(p,scale,detail,roughness,lacunarity,normalized);outputColour=vec4(vec3(f),1.);}'});
const scene=new THREE.Scene(),camera=new THREE.Camera();scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),material));const pixel=new Float32Array(4);
try{
  const response=await fetch(`./assets/${version}_native_fbm_reference.json`);if(!response.ok)throw new Error('Installed Blender reference unavailable');
  const reference=await response.json();if(reference.native_sha256!==sha)throw new Error('Native source mismatch');
  const samples=[];
  for(const [index,item] of reference.samples.entries()){
    material.uniforms.p.value.fromArray(item.position);
    for(const name of ['scale','detail','roughness','lacunarity'])material.uniforms[name].value=item.parameters[name];
    material.uniforms.normalized.value=item.parameters.normalize;
    renderer.setRenderTarget(target);renderer.render(scene,camera);renderer.readRenderTargetPixels(target,0,0,1,1,pixel);
    const actual=pixel[0],expected=item.native_noise_fac,error=Math.abs(actual-expected);
    samples.push({...item,actual_noise_fac:actual,absolute_error:error});
    swatches.fillStyle=`rgb(${Array(3).fill(Math.round((expected*.25+.5)*255)).join(',')})`;swatches.fillRect(index*16,0,16,64);
    swatches.fillStyle=`rgb(${Array(3).fill(Math.round((actual*.25+.5)*255)).join(',')})`;swatches.fillRect(index*16,64,16,64);
  }
  const maximum=Math.max(...samples.map(s=>s.absolute_error)),errors=renderer.info.programs.filter(p=>p.diagnostics?.runnable===false).length;
  result={version,native_sha256:sha,native_blender:reference.blender_version,reference:reference.reference,samples,max_absolute_error:maximum,tolerance:.0001,
    compiled_programs:renderer.info.programs.length,shader_errors:errors,passed:maximum<.0001&&renderer.info.programs.length>0&&!errors,
    coordinates_bump_lighting_visually_verified:false,full_runtime_published:false};
  status.textContent=result.passed?'原生标量噪声核验通过；坐标、凹凸与完整材质尚待画面对照。':'原生标量噪声核验失败，禁止投入场景。';
}catch(error){result={version,passed:false,error:error.message};status.textContent='核验中止：'+error.message;console.error(error);}
document.querySelector('#report').textContent=JSON.stringify(result,null,2);document.querySelector('#save').disabled=false;
document.querySelector('#save').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=version+'_fbm_browser_report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
renderer.setRenderTarget(null);target.dispose();renderer.dispose();
