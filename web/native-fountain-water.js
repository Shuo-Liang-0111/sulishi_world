import * as THREE from 'three';

// Play the native keyframe track, keeping the basin and water boundary fixed.
// This is a visual surface approximation, not a fluid/contact solver.
export function createNativeFountainWater(root,metadata,clips){
  const record=metadata.fountain_water;
  if(!record)return null;
  if(record.version!==metadata.version)throw new Error('喷泉水面与工程版本不一致');
  const surfaces=[];
  root.traverse(o=>{
    if(!o.isMesh)return;
    let owner=o;while(owner.parent&&!owner.userData.native_object)owner=owner.parent;
    if(owner.userData.native_object===record.surface)surfaces.push(o);
  });
  if(!surfaces.length||surfaces.some(o=>!o.geometry.morphAttributes.position?.length)){
    throw new Error('原生水面形变未完整导出');
  }
  root.updateMatrixWorld(true);
  for(const surface of surfaces)surface.geometry.computeBoundingSphere();
  const clip=THREE.AnimationClip.findByName(clips,record.animation_clip);
  if(!clip||clip.duration<=0||!clip.tracks.some(t=>t.name.includes('morphTargetInfluences'))){
    throw new Error('原生水面动画缺失');
  }
  const mixer=new THREE.AnimationMixer(root),action=mixer.clipAction(clip);
  action.setLoop(THREE.LoopRepeat,Infinity).play();mixer.update(0);
  const frustum=new THREE.Frustum(),matrix=new THREE.Matrix4(),sphere=new THREE.Sphere();
  let enabled=true;
  return {
    update(dt){if(enabled)mixer.update(Math.max(0,dt));},
    setEnabled(value){enabled=Boolean(value);},
    visibleFrom(camera){
      if(!enabled||!root.visible)return false;
      matrix.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);
      frustum.setFromProjectionMatrix(matrix);
      return surfaces.some(o=>{
        if(!o.visible)return false;
        sphere.copy(o.geometry.boundingSphere).applyMatrix4(o.matrixWorld);
        return frustum.intersectsSphere(sphere);
      });
    },
    getState(){return {enabled,elapsed:mixer.time,phase:action.time,duration:clip.duration,
      weights:surfaces.map(o=>[...o.morphTargetInfluences]),
      approximation:record.limitation,naturalUseAccepted:false};}
  };
}
