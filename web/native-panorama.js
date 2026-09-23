// Native panoramas use a Blender equirectangular camera rotated (pi/2,0,0).
// Six physical emission-plane calibration: native U=.5 points +Y Blender
// (-Z glTF), U=.75 points +X. Three's U=.5 points +X, so sample native U+.25.
// Rotate linear pixels exactly; no material, exposure or geographic data edits.
export function alignNativePanorama(texture){
  if(texture.userData.zurichPanoramaAligned)return texture;
  const {data,width,height}=texture.image;
  if(width%4||data.length!==width*height*4)throw new Error('原生全景格式不符合已校准的四分之一圈转换');
  const row=new data.constructor(width*4),offset=width;
  for(let y=0;y<height;y++){
    const start=y*width*4;row.set(data.subarray(start,start+width*4));
    data.set(row.subarray(offset),start);data.set(row.subarray(0,offset),start+width*4-offset);
  }
  texture.userData.zurichPanoramaAligned=true;texture.needsUpdate=true;return texture;
}
