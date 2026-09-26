import * as THREE from 'three';

// The diagnostic supports affine template positions and exact native positions.
// Native per-leaf normals are retained separately: one template normal transformed
// by each affine matrix would not reproduce the authored smooth shading.
export function decodeOctNormal(x,y){
  const z=1-Math.abs(x)-Math.abs(y),t=Math.max(-z,0);
  x+=x>=0?-t:t;y+=y>=0?-t:t;
  const length=Math.hypot(x,y,z);return [x/length,y/length,z/length];
}

function invariant(value,message){if(!value)throw new Error(message);}
const types={'<f4':Float32Array,'<u4':Uint32Array,'<u2':Uint16Array};
export function leafArray(metadata,buffer,key){
  const item=metadata.arrays[key],Type=types[item?.dtype];
  invariant(Type&&item.offset%Type.BYTES_PER_ELEMENT===0,`Invalid leaf array: ${key}`);
  const length=item.shape.reduce((a,b)=>a*b,1);
  invariant(length*Type.BYTES_PER_ELEMENT===item.bytes&&item.offset+item.bytes<=buffer.byteLength,`Truncated leaf array: ${key}`);
  return new Type(buffer,item.offset,length);
}

export function createNativeLeafPair(metadata,buffer){
  invariant(metadata.bytes===buffer.byteLength,'Leaf buffer size mismatch');
  const a=key=>leafArray(metadata,buffer,key),vertices=metadata.vertices_per_leaf;
  const material=()=>new THREE.MeshStandardMaterial({color:0xffffff,vertexColors:true,
    roughness:metadata.native_material.roughness,metalness:metadata.native_material.metallic,side:THREE.DoubleSide});
  const referenceGeometry=new THREE.BufferGeometry();
  referenceGeometry.setAttribute('position',new THREE.BufferAttribute(a('reference_positions'),3));
  referenceGeometry.setAttribute('normal',new THREE.BufferAttribute(a('reference_normals'),3));
  referenceGeometry.setAttribute('color',new THREE.BufferAttribute(a('reference_colors'),3));
  referenceGeometry.setIndex(new THREE.BufferAttribute(a('reference_indices'),1));
  const reference=new THREE.Mesh(referenceGeometry,material());
  reference.name='Expanded saved-native leaf geometry';

  const exact=metadata.position_policy==='exact_native_texture';
  const geometry=exact?new THREE.InstancedBufferGeometry():new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.BufferAttribute(a('template_positions'),3));
  geometry.setAttribute('normal',new THREE.BufferAttribute(a('reference_normals').slice(0,vertices*3),3));
  geometry.setAttribute('color',new THREE.BufferAttribute(a('template_colors'),3));
  geometry.setAttribute('nativeLeafVertex',new THREE.Float32BufferAttribute(Array.from({length:vertices},(_,i)=>i),1));
  geometry.setIndex(new THREE.BufferAttribute(a('template_indices'),1));
  const [width,height]=metadata.normal_texture_dimensions;
  invariant(width*height*2===a('native_normal_oct_texture').length&&width*height>=vertices*metadata.leaves,'Invalid native normal texture dimensions');
  const normalTexture=new THREE.DataTexture(a('native_normal_oct_texture'),width,height,THREE.RGFormat,THREE.FloatType);
  normalTexture.magFilter=normalTexture.minFilter=THREE.NearestFilter;
  normalTexture.generateMipmaps=false;normalTexture.flipY=false;
  normalTexture.colorSpace=THREE.NoColorSpace;normalTexture.needsUpdate=true;
  let positionTexture=null;
  if(exact){
    invariant(a('exact_native_position_texture').length===width*height*4,'Invalid native position texture dimensions');
    positionTexture=new THREE.DataTexture(a('exact_native_position_texture'),width,height,THREE.RGBAFormat,THREE.FloatType);
    positionTexture.magFilter=positionTexture.minFilter=THREE.NearestFilter;
    positionTexture.generateMipmaps=false;positionTexture.flipY=false;positionTexture.colorSpace=THREE.NoColorSpace;positionTexture.needsUpdate=true;
    geometry.setAttribute('nativeLeafColor',new THREE.InstancedBufferAttribute(a('instance_colors'),3));
    geometry.instanceCount=metadata.leaves;
  }
  const instancedMaterial=material();
  instancedMaterial.onBeforeCompile=shader=>{
    invariant(shader.vertexShader.includes('#include <defaultnormal_vertex>'),'Unsupported Three.js normal pipeline');
    shader.uniforms.nativeLeafNormals={value:normalTexture};
    shader.vertexShader=`uniform sampler2D nativeLeafNormals;
attribute float nativeLeafVertex;
vec3 nativeLeafNormal(){
  int index=gl_InstanceID*${vertices}+int(nativeLeafVertex);
  vec2 p=texelFetch(nativeLeafNormals,ivec2(index%${width},index/${width}),0).rg;
  vec3 n=vec3(p,1.0-abs(p.x)-abs(p.y));
  float t=max(-n.z,0.0);
  n.xy+=vec2(n.x>=0.0?-t:t,n.y>=0.0?-t:t);
  return normalize(n);
}
`+shader.vertexShader.replace('#include <defaultnormal_vertex>',`
// Stored normals already belong to the original object coordinate frame.
// Apply the object/view normal matrix, never instanceMatrix a second time.
vec3 transformedNormal=normalMatrix*nativeLeafNormal();
#ifdef FLIP_SIDED
transformedNormal=-transformedNormal;
#endif
`);
    if(exact){
      shader.uniforms.nativeLeafPositions={value:positionTexture};
      shader.vertexShader=`uniform sampler2D nativeLeafPositions;
attribute vec3 nativeLeafColor;
`+shader.vertexShader.replace('#include <begin_vertex>',`
int nativePositionIndex=gl_InstanceID*${vertices}+int(nativeLeafVertex);
vec3 transformed=texelFetch(nativeLeafPositions,ivec2(nativePositionIndex%${width},nativePositionIndex/${width}),0).xyz;
`).replace('#include <color_vertex>','#include <color_vertex>\nvColor*=nativeLeafColor;');
    }
  };
  instancedMaterial.customProgramCacheKey=()=>`native-leaf-v2-${exact?'exact':'affine'}-${vertices}-${width}`;
  const instanced=exact?new THREE.Mesh(geometry,instancedMaterial):new THREE.InstancedMesh(geometry,instancedMaterial,metadata.leaves);
  instanced.name=exact?'Exact native position and normal textures':'Affine leaves with saved-native normal texture';
  const colors=a('instance_colors');
  invariant(colors.length===metadata.leaves*3,'Leaf color count mismatch');
  if(!exact){
    const matrices=a('instance_matrices');invariant(matrices.length===metadata.leaves*16,'Leaf matrix count mismatch');
    instanced.instanceMatrix.array.set(matrices);instanced.instanceMatrix.needsUpdate=true;
    instanced.instanceColor=new THREE.InstancedBufferAttribute(colors,3);
  }
  const bounds=new THREE.Box3(new THREE.Vector3().fromArray(metadata.native_local_bounds[0]),new THREE.Vector3().fromArray(metadata.native_local_bounds[1]));
  instanced.boundingBox=bounds.clone();instanced.boundingSphere=bounds.getBoundingSphere(new THREE.Sphere());
  if(exact){geometry.boundingBox=bounds.clone();geometry.boundingSphere=bounds.getBoundingSphere(new THREE.Sphere());}
  const group=new THREE.Group();group.rotation.x=-Math.PI/2;
  for(const ob of [reference,instanced]){
    ob.matrixAutoUpdate=false;ob.matrix.set(...metadata.object_matrix_world.flat());
    ob.castShadow=true;ob.receiveShadow=true;group.add(ob);
  }
  instanced.visible=false;group.updateMatrixWorld(true);
  const worldBounds=bounds.clone().applyMatrix4(reference.matrixWorld);
  return {reference,instanced,group,worldBounds,normalTexture,positionTexture,exact,
    setMode(mode){invariant(['reference','instanced'].includes(mode),'Unknown leaf mode');reference.visible=mode==='reference';instanced.visible=mode==='instanced';},
    dispose(){for(const ob of [reference,instanced]){ob.geometry.dispose();ob.material.dispose();}normalTexture.dispose();if(positionTexture)positionTexture.dispose();}};
}

export async function loadNativeLeafPair(metadataURL){
  const response=await fetch(metadataURL);invariant(response.ok,'Leaf metadata unavailable');
  const metadata=await response.json();
  const data=await fetch(new URL(metadata.file,new URL(metadataURL,location.href)));invariant(data.ok,'Leaf geometry unavailable');
  const buffer=await data.arrayBuffer();
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),v=>v.toString(16).padStart(2,'0')).join('');
  invariant(digest===metadata.sha256,'Leaf geometry hash mismatch');
  return {metadata,...createNativeLeafPair(metadata,buffer)};
}
