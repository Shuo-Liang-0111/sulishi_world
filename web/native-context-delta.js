import * as THREE from 'three';

// Preflight the complete change set before replacing a single source mesh.
// Original source materials/streamed textures remain attached to their identity.
export function preparePhotoGeometryDelta({photoRoot,patchRoot,changedNodes,emptyNodes=[],version}) {
  const ids=values=>values.map(String);
  const changed=ids(changedNodes),empty=ids(emptyNodes);
  if(new Set(changed).size!==changed.length||new Set(empty).size!==empty.length||
     empty.some(id=>!changed.includes(id)))throw new Error('摄影差分清单身份重复或缺失');
  photoRoot.updateMatrixWorld(true);patchRoot.updateMatrixWorld(true);
  const originals=new Map(),replacements=[],seen=new Set();
  photoRoot.traverse(object=>{
    if(!object.isMesh||object.userData.source_node===undefined)return;
    const id=String(object.userData.source_node);
    if(originals.has(id))throw new Error(`原始摄影分块身份重复 ${id}`);
    originals.set(id,object);
  });
  patchRoot.traverse(patch=>{
    if(!patch.isMesh)return;
    const id=String(patch.userData.source_node),original=originals.get(id);
    if(!original||!changed.includes(id)||empty.includes(id)||seen.has(id))
      throw new Error(`摄影差分身份不一致 ${id}`);
    if(patch.userData.construction_version!==undefined&&patch.userData.construction_version!==version)
      throw new Error(`摄影差分版本不一致 ${id}`);
    const error=Math.max(...patch.matrixWorld.elements.map((value,i)=>Math.abs(value-original.matrixWorld.elements[i])));
    if(!Number.isFinite(error)||error>.002)throw new Error(`摄影差分发生位移 ${id}: ${error} m`);
    const position=patch.geometry.getAttribute('position'),uv=patch.geometry.getAttribute('uv');
    const count=patch.geometry.index?.count??position?.count??0;
    if(!position||!uv||uv.count!==position.count||count===0||count%3!==0)
      throw new Error(`摄影差分三角形或贴图坐标缺失 ${id}`);
    if(!position.array.every(Number.isFinite)||!uv.array.every(Number.isFinite))
      throw new Error(`摄影差分包含无效坐标 ${id}`);
    seen.add(id);replacements.push({id,original,base:original.geometry,refined:patch.geometry});
  });
  // Validate empty identities before allocating replacement resources.
  for(const id of empty){
    if(!originals.has(id)||seen.has(id))throw new Error(`空摄影差分身份冲突 ${id}`);
    seen.add(id);
  }
  if(seen.size!==changed.length||changed.some(id=>!seen.has(id)))throw new Error('摄影差分清单与实际分块不一致');
  for(const id of empty){
    const original=originals.get(id),refined=new THREE.BufferGeometry();
    refined.setAttribute('position',new THREE.Float32BufferAttribute([],3));
    replacements.push({id,original,base:original.geometry,refined});
  }
  return {
    replacements,
    setActive(active){
      // A second competing change set must not silently overwrite this one.
      for(const item of replacements)if(item.original.geometry!==item.base&&item.original.geometry!==item.refined)
        throw new Error(`摄影分块已被其他版本改动 ${item.id}`);
      for(const item of replacements)item.original.geometry=active?item.refined:item.base;
    }
  };
}
