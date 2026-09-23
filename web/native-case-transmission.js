import * as THREE from 'three';

// Three's general transmission blur ignores distance to an opaque backing.
// Only closed poster/map cases with a measured nearby opaque backing qualify.
// Use their actual outer-glass-to-paper distance for an approximate projected
// microfacet cone. PBR reflection, IOR, colour, roughness and both faces stay.
// This is a screen-space approximation, not multi-bounce ray-traced transmission.
export function applyNearBackingTransmission(root,{measureOnly=false}={}){
  const objects=new Map();root.updateMatrixWorld(true);
  root.traverse(o=>{if(o.userData.native_object)objects.set(o.userData.native_object,o);});
  const weight={value:1},records=[];
  const original='float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );';
  const replacement=`
    float legacyLod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
    vec4 caseViewPoint = viewMatrix * vec4( vWorldPosition, 1.0 );
    float projectedGap = nativeCaseBackingDistance * 0.5 * transmissionSamplerSize.y * abs( projectionMatrix[1][1] ) / max( abs( caseViewPoint.z ), 0.001 );
    float conePixels = projectedGap * applyIorToRoughness( roughness * roughness, ior );
    float lod = mix( legacyLod, log2( max( 1.0, conePixels ) ), nativeCaseBackingWeight );`;
  const point=new THREE.Vector3();
  function depths(object,axis){
    let min=Infinity,max=-Infinity;
    object.traverse(o=>{if(!o.isMesh)return;const a=o.geometry.attributes.position;
      for(let i=0;i<a.count;i++){point.fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld);const d=point.dot(axis);min=Math.min(min,d);max=Math.max(max,d);}
    });return {min,max};
  }
  function faceNormal(object,toward){
    let area=0;const result=new THREE.Vector3(),a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3();
    object.traverse(o=>{if(!o.isMesh)return;const p=o.geometry.attributes.position,index=o.geometry.index;
      for(let i=0,n=index?index.count:p.count;i<n;i+=3){
        a.fromBufferAttribute(p,index?index.getX(i):i).applyMatrix4(o.matrixWorld);
        b.fromBufferAttribute(p,index?index.getX(i+1):i+1).applyMatrix4(o.matrixWorld).sub(a);
        c.fromBufferAttribute(p,index?index.getX(i+2):i+2).applyMatrix4(o.matrixWorld).sub(a);
        b.cross(c);const size=b.lengthSq();if(size>area){area=size;result.copy(b).normalize();}
      }
    });if(result.dot(toward)<0)result.negate();return result;
  }
  for(const [name,glass] of objects){
    const poster=/^SV_AD_\d+_GLASS$/.test(name);
    const map=/^(CF|CF2|BSF|BSE)_INFO_(MAIN|RETURN)_NOTICE_GLASS(?:_REVERSE)?$/.test(name);
    if(!poster&&!map)continue;
    const paper=objects.get(name.replace('_GLASS',poster?'_ART':'_PRINT'));if(!paper)throw new Error('信息玻璃缺少对应底板: '+name);
    const glassCentre=new THREE.Box3().setFromObject(glass).getCenter(new THREE.Vector3());
    const paperCentre=new THREE.Box3().setFromObject(paper).getCenter(new THREE.Vector3());
    const axis=faceNormal(glass,glassCentre.sub(paperCentre)),g=depths(glass,axis),p=depths(paper,axis);
    const distance=g.max-p.max,gap=g.min-p.max;
    records.push({name,outer_glass_to_paper_m:distance,inner_glass_to_paper_m:gap});
    if(measureOnly)continue;
    if(!(distance>.004&&distance<.008&&gap>0&&gap<.003))throw new Error('信息玻璃与底板间距不符合已核验构造: '+name);
    glass.traverse(o=>{if(!o.isMesh)return;
      const apply=source=>{const material=source.clone();
        if(material.transmission<.9)throw new Error('近背板转换只适用于已核验的透明保护玻璃');
        material.onBeforeCompile=shader=>{
          const chunk=THREE.ShaderChunk.transmission_pars_fragment;
          if(!chunk.includes(original))throw new Error('Three.js折射接口发生变化，需重查');
          shader.uniforms.nativeCaseBackingDistance={value:distance};shader.uniforms.nativeCaseBackingWeight=weight;
          shader.fragmentShader='uniform float nativeCaseBackingDistance;\nuniform float nativeCaseBackingWeight;\n'+shader.fragmentShader.replace('#include <transmission_pars_fragment>',
            chunk.replace(original,replacement).replace('return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );',
              'return textureLod( transmissionSamplerMap, fragCoord.xy, lod );'));
        };
        material.customProgramCacheKey=()=> 'zurich-case-backed-transmission-v1';material.needsUpdate=true;
        return material;
      };o.material=Array.isArray(o.material)?o.material.map(apply):apply(o.material);
    });
  }
  return {records,setEnabled(value){weight.value=value?1:0;}};
}
