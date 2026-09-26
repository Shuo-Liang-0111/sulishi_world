import * as THREE from 'three';
import {loadNativeLeafPair} from './native-leaf-instances.js';

// Optional production comparison reads the real current-world pack, not a
// reconstructed test buffer. The expanded mesh remains the frozen reference.
export async function loadLeafReviewPair(){
  const original=await loadNativeLeafPair('./assets/G1_027r15_leaf_diagnostic/tree_exact.json');
  if(!new URLSearchParams(location.search).has('production'))return original;
  const current=await loadNativeLeafPair('./assets/G1_027r15_current_r01/leaves/BE_TREE_69773_LEAVES.json');
  if(current.metadata.native_sha256!==original.metadata.native_sha256||current.metadata.native_object!==original.metadata.native_object)
    throw new Error('Production leaf and native reference identity differ');
  original.instanced.visible=false;
  const group=new THREE.Group();group.add(original.group,current.group);
  return {reference:original.reference,instanced:current.instanced,group,worldBounds:current.worldBounds,
    metadata:{...current.metadata,reference_binary_sha256:original.metadata.sha256,production_pack:true},
    setMode(mode){if(!['reference','instanced'].includes(mode))throw new Error('Unknown leaf review mode');original.reference.visible=mode==='reference';current.instanced.visible=mode==='instanced';},
    dispose(){original.dispose();current.dispose();}};
}
