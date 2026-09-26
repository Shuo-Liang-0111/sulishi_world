import * as THREE from 'three';

// An algebraic specialization for the saved neutral-hue nodes. It preserves
// original image pixels and sampling, rather than estimating a replacement tint.
export async function loadNativeHSVMaterials(version,nativeSha){
  const response=await fetch(`./assets/${version}_hsv_materials.json`);if(!response.ok)throw new Error('Native HSV recipes unavailable');
  const metadata=await response.json();if(metadata.version!==version||metadata.native_sha256!==nativeSha)throw new Error('Native HSV source mismatch');
  const recipes=new Map(metadata.materials.map(r=>[r.name,r])),textures=new Map(),loader=new THREE.TextureLoader();
  return {metadata,async apply(root){
    const materials=new Set();root.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])if(recipes.has(m.name))materials.add(m);});
    for(const m of materials){
      if(m.userData.nativeHSV)continue;const r=recipes.get(m.name);
      if(!textures.has(r.image))textures.set(r.image,loader.loadAsync(r.image));
      const texture=(await textures.get(r.image)).clone();texture.colorSpace=THREE.SRGBColorSpace;texture.flipY=false;
      texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.anisotropy=8;
      const [sx,sy]=r.mapping.scale,[lx,ly]=r.mapping.location,angle=r.mapping.rotation[2],c=Math.cos(angle),s=Math.sin(angle);
      const a=c*sx,b=-s*sy,d=s*sx,e=c*sy;
      // Native V=1-glTF_V. Transform to native UV, apply the native POINT
      // mapping, and transform back. Scaling V also changes its offset.
      texture.matrixAutoUpdate=false;texture.matrix.set(a,-b,b+lx,-d,e,1-e-ly,0,0,1);
      m.map=texture;m.color.setRGB(1,1,1);m.opacity=r.alpha;
      const before=m.onBeforeCompile;m.onBeforeCompile=function(shader,renderer){
        before.call(this,shader,renderer);
        if(!shader.fragmentShader.includes('#include <map_fragment>'))throw new Error('Unsupported material colour pipeline');
        shader.uniforms.nativeHSVSaturation={value:r.saturation};shader.uniforms.nativeHSVValue={value:r.value};
        shader.fragmentShader='uniform float nativeHSVSaturation;\nuniform float nativeHSVValue;\n'+shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
float nativeHSVMax=max(diffuseColor.r,max(diffuseColor.g,diffuseColor.b));
diffuseColor.rgb=nativeHSVValue*mix(vec3(nativeHSVMax),diffuseColor.rgb,nativeHSVSaturation);`);
      };
      m.customProgramCacheKey=()=>`zurich-native-neutral-hsv-v1`;m.userData.nativeHSV={version,source_image:r.image_sha256,saturation:r.saturation,value:r.value};m.needsUpdate=true;
    }
    return materials.size;
  }};
}
