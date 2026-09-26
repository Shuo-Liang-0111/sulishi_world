// Scalar 3-D improved Perlin with Jenkins lookup3 lattice hashes. The hash,
// gradient and fBM definitions are shared by MaterialX and Blender. This
// implementation is limited to the independently recorded FBM/no-distortion
// nodes, and must pass actual installed-Blender samples before scene use.
export const nativeFBMGLSL = /* glsl */`
uint zRot(uint v,uint n){return (v<<n)|(v>>(32u-n));}
uint zLattice(ivec3 q){
  uvec3 h=uvec3(q)+uvec3(0xdeadbf08u);
  h.z=(h.z^h.y)-zRot(h.y,14u);
  h.x=(h.x^h.z)-zRot(h.z,11u);
  h.y=(h.y^h.x)-zRot(h.x,25u);
  h.z=(h.z^h.y)-zRot(h.y,16u);
  h.x=(h.x^h.z)-zRot(h.z,4u);
  h.y=(h.y^h.x)-zRot(h.x,14u);
  return (h.z^h.y)-zRot(h.y,24u);
}
float zGradient(ivec3 cell,vec3 delta){
  uint h=zLattice(cell)&15u;
  float u=h<8u?delta.x:delta.y;
  float v=h<4u?delta.y:((h==12u||h==14u)?delta.x:delta.z);
  return ((h&1u)==0u?u:-u)+((h&2u)==0u?v:-v);
}
float zSignedNoise(vec3 source){
  vec3 p=sign(source)*mod(abs(source),100000.0)+.5*step(vec3(1000000.0),abs(source));
  ivec3 cell=ivec3(floor(p));vec3 t=p-floor(p);
  vec3 smoothT=t*t*t*(t*(6.0*t-15.0)+10.0);
  float corner[8];
  for(int z=0;z<2;z++)for(int y=0;y<2;y++)for(int x=0;x<2;x++){
    ivec3 d=ivec3(x,y,z);corner[x+2*y+4*z]=zGradient(cell+d,t-vec3(d));
  }
  float lower=mix(mix(corner[0],corner[1],smoothT.x),mix(corner[2],corner[3],smoothT.x),smoothT.y);
  float upper=mix(mix(corner[4],corner[5],smoothT.x),mix(corner[6],corner[7],smoothT.x),smoothT.y);
  return .982*mix(lower,upper,smoothT.z);
}
float zNativeFBM(vec3 position,float scale,float detail,float roughness,float lacunarity,bool normalized){
  vec3 p=position*scale;
  float frequency=1.0,amplitude=1.0,total=0.0,weight=0.0;
  int levels=int(floor(clamp(detail,0.0,15.0)));
  for(int level=0;level<=15;level++){
    if(level>levels)break;
    total+=amplitude*zSignedNoise(p*frequency);weight+=amplitude;
    amplitude*=clamp(roughness,0.0,1.0);frequency*=lacunarity;
  }
  float fractional=fract(clamp(detail,0.0,15.0));
  float extended=total+amplitude*zSignedNoise(p*frequency);
  if(normalized)return mix(.5+.5*total/weight,.5+.5*extended/(weight+amplitude),fractional);
  return mix(total,extended,fractional);
}
`;
