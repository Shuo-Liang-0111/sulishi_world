import * as THREE from 'three';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';

// Cycles DIFFUSE (direct + indirect, colour disabled) is outgoing radiance for
// unit diffuse colour, not irradiance. Reapply the editable PBR base colour in
// the shader. Do not add a second sun/environment diffuse term or darken it a
// second time with AO. View-dependent PBR specular remains live.
export async function applyNativeDiffuse({root,metadata,manager}){
  const record=metadata.static_diffuse_lighting;
  if(!record)return {receivers:0,static:false};
  if(record.version!==metadata.version||!record.uv_topology_verified)throw new Error('静态光照与当前几何版本不一致');
  const texture=await new HDRLoader(manager).loadAsync('./assets/'+record.file);
  texture.flipY=false;texture.mapping=THREE.UVMapping;
  texture.colorSpace=THREE.LinearSRGBColorSpace;texture.channel=1;
  texture.minFilter=THREE.LinearFilter;texture.magFilter=THREE.LinearFilter;
  texture.generateMipmaps=false;
  const names=new Set(record.receivers),found=new Set(),materials=new Map();
  const weight={value:1};
  root.traverse(o=>{
    if(!o.isMesh)return;
    let owner=o;while(owner.parent&&!owner.userData.native_object)owner=owner.parent;
    const name=owner.userData.native_object||o.name;
    if(!names.has(name))return;
    found.add(name);
    const apply=source=>{
      if(!source.aoMap||source.aoMap.channel!==1||!o.geometry.attributes.uv1)throw new Error('光照缺少已校核UV: '+name);
      if(materials.has(source))return materials.get(source);
      const material=source.clone();material.lightMap=texture;
      // No radiance/irradiance conversion is needed for the replacement below.
      material.lightMapIntensity=1;
      material.onBeforeCompile=shader=>{
        const line='vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;';
        if(!shader.fragmentShader.includes(line))throw new Error('当前Three.js光照接口与已校核版本不一致');
        shader.uniforms.nativeDiffuseWeight=weight;
        const maps=THREE.ShaderChunk.lights_fragment_maps.replace('irradiance += lightMapIrradiance;',
          '// Native diffuse is composed below; do not add it twice.');
        shader.fragmentShader=shader.fragmentShader.replace('#include <lights_fragment_maps>',maps);
        shader.fragmentShader='uniform float nativeDiffuseWeight;\n'+shader.fragmentShader.replace(line,
          'vec3 totalDiffuse = mix(reflectedLight.directDiffuse + reflectedLight.indirectDiffuse, lightMapTexel.rgb * material.diffuseColor, nativeDiffuseWeight);');
      };
      material.customProgramCacheKey=()=> 'zurich-native-static-diffuse-v1';
      material.userData.native_static_diffuse=metadata.version;
      material.needsUpdate=true;materials.set(source,material);return material;
    };
    o.material=Array.isArray(o.material)?o.material.map(apply):apply(o.material);
  });
  if(found.size!==names.size)throw new Error(`静态光照缺少构件 ${found.size}/${names.size}`);
  return {receivers:found.size,static:true,limitation:record.limitation,
    setEnabled(value){weight.value=value?1:0;}};
}
