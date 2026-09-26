import * as THREE from 'three';
import {nativeFBMGLSL} from './native-fbm.js';

const parameters=n=>new THREE.Vector4(n?.scale??1,n?.detail??0,n?.roughness??.5,n?.lacunarity??2);
const uniformsGLSL=/* glsl */`
varying vec3 zObjectCoordinate;
varying vec3 zUVCoordinate;
uniform vec4 zRampParameters,zBumpParameters,zRampLow,zRampHigh;
uniform vec2 zRampPositions;
uniform bool zRampNormalized,zBumpNormalized,zRampUV,zBumpUV,zEase;
uniform int zRampChannel;
uniform float zBumpStrength,zBumpDistance,zBumpWidth;
float zNoiseValue(vec3 p,vec4 options,bool normalized){return zNativeFBM(p,options.x,options.y,options.z,options.w,normalized);}
vec4 zRampValue(){
  float factor=zNoiseValue(zRampUV?zUVCoordinate:zObjectCoordinate,zRampParameters,zRampNormalized);
  float t=clamp((factor-zRampPositions.x)/(zRampPositions.y-zRampPositions.x),0.,1.);
  if(zEase)t=t*t*(3.-2.*t);
  return mix(zRampLow,zRampHigh,t);
}
vec3 zApplyBump(vec3 baseNormal,vec3 surfacePosition){
  if(zBumpStrength<=0.)return baseNormal;
  vec3 p=zBumpUV?zUVCoordinate:zObjectCoordinate;
  float h=zNoiseValue(p,zBumpParameters,zBumpNormalized);
  float dx=(zNoiseValue(p+dFdx(p)*zBumpWidth,zBumpParameters,zBumpNormalized)-h)*zBumpDistance/zBumpWidth;
  float dy=(zNoiseValue(p+dFdy(p)*zBumpWidth,zBumpParameters,zBumpNormalized)-h)*zBumpDistance/zBumpWidth;
  vec3 px=dFdx(surfacePosition),py=dFdy(surfacePosition);
  vec3 rx=cross(py,baseNormal),ry=cross(baseNormal,px);
  float determinant=dot(px,rx);
  if(abs(determinant)<1e-20)return baseNormal;
  vec3 bumped=normalize(abs(determinant)*baseNormal-sign(determinant)*(dx*rx+dy*ry));
  return normalize(mix(baseNormal,bumped,clamp(zBumpStrength,0.,1.)));
}
`;

export async function loadNativeFBMMaterials(version,nativeSha){
  const response=await fetch(`./assets/${version}_fbm_materials.json`);if(!response.ok)throw new Error('Native procedural recipes unavailable');
  const metadata=await response.json();if(metadata.version!==version||metadata.native_sha256!==nativeSha||!metadata.noise_scalar_verified)throw new Error('Native procedural source mismatch');
  const recipes=new Map(metadata.materials.map(r=>[r.name,r]));
  return {metadata,apply(root){
    const materials=new Set();root.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])if(recipes.has(m.name)){
      const recipe=recipes.get(m.name);
      if((recipe.ramp?.noise.coordinate==='UV'||recipe.bump?.noise.coordinate==='UV')&&!o.geometry.getAttribute('uv'))throw new Error('Native UV material has no exported UV: '+o.name);
      materials.add(m);
    }});
    for(const m of materials){
      if(m.userData.nativeFBM)continue;
      const r=recipes.get(m.name),ramp=r.ramp,bump=r.bump;
      if(m.map||m.normalMap||m.bumpMap||m.roughnessMap)throw new Error('Unexpected image channel in procedural-only material: '+m.name);
      m.color.fromArray(r.base);m.roughness=r.roughness;
      const uniforms={zRampParameters:{value:parameters(ramp?.noise)},zBumpParameters:{value:parameters(bump?.noise)},
        zRampNormalized:{value:ramp?.noise.normalize??true},zBumpNormalized:{value:bump?.noise.normalize??true},
        zRampUV:{value:ramp?.noise.coordinate==='UV'},zBumpUV:{value:bump?.noise.coordinate==='UV'},
        zRampLow:{value:new THREE.Vector4().fromArray(ramp?.elements[0].color??[0,0,0,1])},zRampHigh:{value:new THREE.Vector4().fromArray(ramp?.elements[1].color??[1,1,1,1])},
        zRampPositions:{value:new THREE.Vector2(...(ramp?.elements.map(e=>e.position)??[0,1]))},zEase:{value:ramp?.interpolation==='EASE'},
        zRampChannel:{value:ramp?(ramp.channel==='Base Color'?1:2):0},zBumpStrength:{value:bump?.strength??0},
        zBumpDistance:{value:bump?.distance??0},zBumpWidth:{value:Math.max(.00001,bump?.filter_width??.1)}};
      const before=m.onBeforeCompile;
      m.onBeforeCompile=function(shader,renderer){
        before.call(this,shader,renderer);Object.assign(shader.uniforms,uniforms);
        for(const include of ['begin_vertex','map_fragment','roughnessmap_fragment','normal_fragment_maps'])if(!(shader.vertexShader+shader.fragmentShader).includes(`#include <${include}>`))throw new Error('Unsupported native material shader pipeline');
        shader.vertexShader='varying vec3 zObjectCoordinate;\nvarying vec3 zUVCoordinate;\n'+shader.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
zObjectCoordinate=vec3(position.x,-position.z,position.y);
zUVCoordinate=vec3(uv.x,1.-uv.y,0.);`);
        shader.fragmentShader=nativeFBMGLSL+uniformsGLSL+shader.fragmentShader;
        shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>','#include <map_fragment>\nif(zRampChannel==1)diffuseColor.rgb=zRampValue().rgb;')
          .replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nif(zRampChannel==2)roughnessFactor=zRampValue().r;')
          .replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\nnormal=zApplyBump(normal,-vViewPosition);');
      };
      m.customProgramCacheKey=()=> 'zurich-native-fbm-simple-v1';m.userData.nativeFBM={version,material:r.name,bump_native_equivalence:false};m.needsUpdate=true;
    }
    return materials.size;
  }};
}
