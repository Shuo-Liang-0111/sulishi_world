import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {TAARenderPass} from 'three/addons/postprocessing/TAARenderPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';

// Accumulate the actual scene at subpixel camera offsets only while stationary.
// Camera, texture, layer and door changes discard history: no motion ghosting.
export function createReviewAntialias(renderer,scene,camera){
  const composer=new EffectComposer(renderer),taa=new TAARenderPass(scene,camera);
  taa.sampleLevel=0;taa.unbiased=false;
  composer.addPass(taa);composer.addPass(new OutputPass());
  let previous='',lastChange=0;
  return {
    resize(w,h){composer.setSize(w,h);if(taa._holdRenderTarget)taa._holdRenderTarget.setSize(w*renderer.getPixelRatio(),h*renderer.getPixelRatio());previous='';},
    render(now,revision,animatedVisible=false){
      if(animatedVisible){
        // Four current-frame samples retain real motion. Reusing stationary
        // accumulation here would freeze/ghost an otherwise moving water mesh.
        previous='';lastChange=now;taa.accumulate=false;taa.sampleLevel=2;
        composer.render();return;
      }
      taa.sampleLevel=0;
      const key=[revision,...camera.position.toArray(),...camera.quaternion.toArray(),camera.fov,camera.near,camera.aspect].join(',');
      if(key!==previous){taa.accumulateIndex=-1;previous=key;lastChange=now;}
      if(now-lastChange<250){renderer.render(scene,camera);return;}
      taa.accumulate=true;composer.render();
    },
    getSamples(){return Math.max(0,taa.accumulateIndex);}
  };
}
