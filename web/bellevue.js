import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
import {RectAreaLightUniformsLib} from 'three/addons/lights/RectAreaLightUniformsLib.js';
import {applyNativeDiffuse} from './native-diffuse-lighting.js';
import {alignNativePanorama} from './native-panorama.js';
import {applyNearBackingTransmission} from './native-case-transmission.js';
import {createNativeFountainWater} from './native-fountain-water.js';
import {preparePhotoGeometryDelta} from './native-context-delta.js';

// The construction delta retains the original source geometry and source texture LODs.
export async function loadBellevue({scene,renderer,photoRoot,version}) {
  const response=await fetch(`./assets/${version}_bellevue.json`);
  if(!response.ok)throw new Error('Bellevue 导出清单无法读取');
  const metadata=await response.json();
  if(metadata.version!==version)throw new Error('Bellevue 原生与实时版本不一致');
  const errors=[];const manager=new THREE.LoadingManager();manager.onError=url=>errors.push(url);
  const loader=new GLTFLoader(manager);
  // Use native image decoding for large local construction maps. The app browser's
  // fetch/blob ImageBitmap path rejected these while smaller source maps succeeded.
  loader.register(parser=>({
    name:'ZURICH_construction_image_loader',
    loadTexture(index){
      const imageLoader=new THREE.TextureLoader(manager);
      return parser.loadTextureImage(index,parser.json.textures[index].source,imageLoader);
    }
  }));
  const [authored,patch,hdr]=await Promise.all([
    loader.loadAsync(`./assets/${(metadata.authored_runtime||metadata.authored).file}`),
    loader.loadAsync(`./assets/${metadata.context_patch.file}`),
    new HDRLoader(manager).loadAsync(`./assets/${version}_sky.hdr`)
  ]);
  if(errors.length||renderer.getContext().isContextLost())throw new Error('亭体纹理加载或渲染失败，未接受当前场景');
  const photoDelta=preparePhotoGeometryDelta({photoRoot,patchRoot:patch.scene,
    changedNodes:metadata.changed_nodes,emptyNodes:metadata.context_empty_nodes||[],version});
  const root=authored.scene;root.visible=false;root.name='Bellevue editable native export';
  const identities=new Set(),doors=[];
  const invalidOcclusion=new Set(metadata.indirect_occlusion?.invalid_scalar_ao_receivers||[]);
  root.traverse(o=>{
    if(o.userData.native_object)identities.add(o.userData.native_object);
    if(o.userData.interaction_role==='curved_sliding_door_leaf')doors.push(o);
    if(o.isMesh){
      let owner=o;while(owner.parent&&!owner.userData.native_object)owner=owner.parent;
      if(invalidOcclusion.has(owner.userData.native_object||o.name)){
        const copy=m=>{const c=m.clone();c.userData.invalidInheritedAO=true;return c;};
        o.material=Array.isArray(o.material)?o.material.map(copy):copy(o.material);
      }
      const mats=Array.isArray(o.material)?o.material:[o.material];
      o.castShadow=!mats.some(m=>m.transmission>.1);o.receiveShadow=true;
      // 6 mm roof folds are below the shadow-map texel size. Their own shadow
      // sampling creates dotted acne; keep the actual geometry and material visible.
      if(String(o.userData.native_object||o.name).includes('BE_ROOF_STANDING_SEAM')){
        o.castShadow=false;o.receiveShadow=false;
      }
      // Isolated, reversible checks; never used by the normal review entry.
      const diagnostic=new URLSearchParams(location.search).get('roof-diagnostic');
      if(diagnostic==='no-shadows'){o.castShadow=false;o.receiveShadow=false;}
      if(diagnostic==='no-seams'&&String(o.userData.native_object||o.name).includes('BE_ROOF_STANDING_SEAM'))o.visible=false;
      for(const m of mats){
        if(m.map)m.map.anisotropy=8;if(m.normalMap)m.normalMap.anisotropy=8;
        // Finite-distance AO contains no diffuse bounce. Retain a small indirect
        // component instead of turning sheltered downward faces completely black.
        // This is a realtime approximation, not a native GI equivalence claim.
        if(m.aoMap)m.aoMapIntensity=m.userData.invalidInheritedAO?0:.85;
      }
    }
  });
  if(identities.size!==metadata.exported_authored_objects||doors.length!==2)throw new Error('原生对象身份或门扇导出不完整');
  scene.add(root);
  const pmrem=new THREE.PMREMGenerator(renderer);const env=pmrem.fromEquirectangular(alignNativePanorama(hdr)).texture;hdr.dispose();pmrem.dispose();
  // Nearby glass needs the actual streets/roof around it, rather than an empty
  // sky in every reflection direction. These captures come from this native file.
  // Keep this explicitly approximate until moving reflections are implemented.
  const localReflections=[];
  for(const probe of metadata.local_reflection_probes||[]){
    const image=await new HDRLoader(manager).loadAsync('./assets/'+probe.file);
    const generator=new THREE.PMREMGenerator(renderer);
    const texture=generator.fromEquirectangular(alignNativePanorama(image)).texture;image.dispose();generator.dispose();
    localReflections.push({...probe,texture,position:new THREE.Vector3().fromArray(probe.position_yup)});
  }
  if(localReflections.length){
    root.updateMatrixWorld(true);const box=new THREE.Box3(),center=new THREE.Vector3();
    root.traverse(o=>{
      if(!o.isMesh)return;
      let owner=o;while(owner.parent&&!owner.userData.native_object)owner=owner.parent;
      const name=owner.userData.native_object||o.name;
      if((!name.startsWith('SV_')&&!name.startsWith('BSE_')&&!name.startsWith('F59_'))||name.includes('SKYLIGHT'))return;
      box.setFromObject(o);box.getCenter(center);
      let probe;
      if(name.startsWith('F59_'))probe=localReflections.find(p=>p.key==='FOUNTAIN');
      else if(name.startsWith('BSE_BIN'))probe=localReflections.find(p=>p.key==='EAST_BIN');
      else if(name.startsWith('BSE_'))probe=localReflections.find(p=>p.key==='EAST_INFO');
      else if(name.startsWith('SV_NORTH')||name.startsWith('SV_AD_'))probe=localReflections.find(p=>p.key==='NORTH');
      else if(name.startsWith('SV_FRONT')||name.startsWith('SV_ENTRY'))probe=localReflections.find(p=>p.key==='FRONT');
      else probe=localReflections.reduce((a,b)=>a.position.distanceToSquared(center)<b.position.distanceToSquared(center)?a:b);
      const apply=m=>{
        if((!(m.transmission>.1)&&!name.startsWith('BSE_')&&!name.startsWith('F59_'))||!probe)return m;
        const copy=m.clone();copy.envMap=probe.texture;copy.needsUpdate=true;
        copy.userData.local_reflection_probe=probe.key;return copy;
      };
      o.material=Array.isArray(o.material)?o.material.map(apply):apply(o.material);
    });
  }
  const diffuseLighting=await applyNativeDiffuse({root,metadata,manager});
  const caseTransmission=applyNearBackingTransmission(root);
  const fountainWater=createNativeFountainWater(root,metadata,authored.animations);
  const lighting=new THREE.Group();RectAreaLightUniformsLib.init();
  for(const item of metadata.lights){
    const color=new THREE.Color().fromArray(item.color);
    const side=item.diameter_m*Math.sqrt(Math.PI)/2;
    // Keep the native radiance scale used by the exported HDR. Mixing a lumen
    // conversion into only the fixtures overexposes them relative to that sky.
    const light=new THREE.RectAreaLight(color,1,item.type==='AREA_RECTANGLE'?item.width_m:side,item.type==='AREA_RECTANGLE'?item.height_m:side);light.power=item.power_W;
    light.position.fromArray(item.position);light.lookAt(light.position.clone().add(new THREE.Vector3(0,-1,0)));lighting.add(light);
  }
  scene.add(lighting);lighting.visible=false;
  let active=false,open=1,targetOpen=1;
  return {
    root,metadata,doors,diffuseLighting,caseTransmission,fountainWater,
    setLightingProbe(part,enabled){
      if(part==='case-distance')caseTransmission.setEnabled(enabled);
      if(part==='native-diffuse')diffuseLighting.setEnabled?.(enabled);
      if(part==='environment')scene.environment=enabled?env:null;
      if(part==='fixtures')lighting.visible=enabled;
      if(part==='occlusion')root.traverse(o=>{
        if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.aoMap)m.aoMapIntensity=enabled&&!m.userData.invalidInheritedAO?.85:0;
      });
    },
    setActive(value){
      photoDelta.setActive(value);
      active=value;root.visible=value;lighting.visible=value;
      scene.environment=value?env:null;
    },
    toggleDoor(){targetOpen=targetOpen>.5?0:1;return targetOpen>.5;},
    getDoorState(){return {target:targetOpen,current:open};},
    update(dt,elapsedDt=dt){
      if(!active)return;
      fountainWater?.update(elapsedDt);
      open=THREE.MathUtils.clamp(open+Math.sign(targetOpen-open)*Math.min(dt/1.7,Math.abs(targetOpen-open)),0,1);
      for(const door of doors)door.quaternion.setFromAxisAngle(new THREE.Vector3(0,1,0),Number(door.userData.open_rotation_z)*open);
    }
  };
}
