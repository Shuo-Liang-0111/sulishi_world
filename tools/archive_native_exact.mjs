// Lossless, fully reversible storage encoding of a specifically named checkpoint.
// Replacement requires both decoded-byte identity and an independent Blender reopen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import z from 'node:zlib';
const root=path.resolve('F:/MyWorld/ZurichWorld');
const [filename,version]=process.argv.slice(2);
if(!/^G1_\d+(?:r\d+)?_[a-z_]+\.blend$/.test(filename||'')||!/^G1_\d+(?:r\d+)?$/.test(version||''))throw Error('Explicit checkpoint filename and version required');
const source=path.join(root,'native',filename), candidate=source.replace(/\.blend$/,'.lossless-check.blend');
const folder=path.join(root,'evidence/storage',filename.replace(/\.blend$/,''));
const receipt=path.join(folder,'encoding.json'),reopen=path.join(folder,'reopen.json');
for(const p of [source,candidate])if(fs.realpathSync(path.dirname(p))!==fs.realpathSync(path.join(root,'native')))throw Error('Target escaped native directory');
const hash=async file=>{const h=crypto.createHash('sha256');for await(const b of fs.createReadStream(file))h.update(b);return h.digest('hex');};
// Node24's streaming wrapper rejects some otherwise valid concatenated frames.
// Parse standard frame/block boundaries and independently decode each checksum.
function decodedHash(file){
  const fd=fs.openSync(file,'r'),size=fs.fstatSync(fd).size,h=crypto.createHash('sha256');let p=0,bytes=0,frames=0;
  const read=(at,count)=>{const b=Buffer.alloc(count);if(fs.readSync(fd,b,0,count,at)!==count)throw Error('Short frame read');return b;};
  try{while(p<size){
    let at=p;const b=read(at,6);if(b.readUInt32LE(0)!==0xfd2fb528)throw Error('Invalid frame magic at '+at);
    const d=b[4],single=!!(d&32),flag=d>>6,dict=[0,1,2,4][d&3],fcs=flag===0?(single?1:0):[0,2,4,8][flag];
    at+=5+(single?0:1)+dict+fcs;let last=false;
    while(!last){const bh=read(at,3).readUIntLE(0,3);last=!!(bh&1);const type=(bh>>1)&3,sz=bh>>3;if(type===3)throw Error('Reserved block type');at+=3+(type===1?1:sz);}
    if(d&4)at+=4;const raw=z.zstdDecompressSync(read(p,at-p));h.update(raw);bytes+=raw.length;frames++;p=at;
  }}finally{fs.closeSync(fd);}
  if(p!==size)throw Error('Unexpected trailing bytes');return {bytes,frames,sha256:h.digest('hex')};
}
if(process.argv.includes('--replace-verified')){
  const r=JSON.parse(fs.readFileSync(receipt,'utf8')), q=JSON.parse(fs.readFileSync(reopen,'utf8'));
  if(!r.decoded_identical||!q.native_reopen||q.version!==version||path.resolve(q.file).toLowerCase()!==candidate.toLowerCase())throw Error('Missing exact reopen evidence');
  if(await hash(source)!==r.source_sha256||await hash(candidate)!==r.compressed_sha256)throw Error('Checkpoint changed after verification');
  fs.renameSync(candidate,source);
  r.replaced_after_native_reopen=true;r.final_path=source;fs.writeFileSync(receipt,JSON.stringify(r,null,2));
  console.log(JSON.stringify({path:source,bytes_reclaimed:r.original_bytes-r.compressed_bytes,decoded_identical:true}));
}else if(process.argv.includes('--verify-existing')){
  if(fs.existsSync(receipt)||!fs.existsSync(candidate))throw Error('Recovery only for unrecorded candidate');
  const stat=fs.statSync(source),raw=await hash(source),decoded=decodedHash(candidate);
  if(decoded.sha256!==raw||decoded.bytes!==stat.size||fs.statSync(source).mtimeMs!==stat.mtimeMs)throw Error('Existing candidate not identical');
  fs.mkdirSync(folder,{recursive:true});
  fs.writeFileSync(receipt,JSON.stringify({source,candidate,version,original_bytes:stat.size,compressed_bytes:fs.statSync(candidate).size,source_sha256:raw,compressed_sha256:await hash(candidate),frames:decoded.frames,decoded_identical:true,replaced_after_native_reopen:false,encoding:'Checksummed concatenated Zstandard frames; each frame decoded independently; exact original bytes recoverable',recovery:'Node streaming wrapper failed; independent frame decoder verified complete exact original data'},null,2));
  console.log(JSON.stringify({candidate,decoded_identical:true,frames:decoded.frames}));
}else{
  if(fs.existsSync(candidate)||fs.existsSync(receipt))throw Error('Inspect prior attempt before retry');
  const stat=fs.statSync(source),fd=fs.openSync(source,'r'),header=Buffer.alloc(7);fs.readSync(fd,header,0,7,0);fs.closeSync(fd);
  if(header.toString()!=='BLENDER')throw Error('Only raw Blender checkpoints are eligible');
  const rawHash=crypto.createHash('sha256'),compressedHash=crypto.createHash('sha256');
  const out=fs.openSync(candidate,'wx');let originalBytes=0,compressedBytes=0,frames=0;
  try{for await(const chunk of fs.createReadStream(source,{highWaterMark:256*1024})){
    rawHash.update(chunk);originalBytes+=chunk.length;
    const data=z.zstdCompressSync(chunk,{params:{[z.constants.ZSTD_c_compressionLevel]:4,[z.constants.ZSTD_c_checksumFlag]:1}});
    for(let offset=0;offset<data.length;)offset+=fs.writeSync(out,data,offset,data.length-offset);compressedHash.update(data);compressedBytes+=data.length;frames++;
  }fs.fsyncSync(out);}finally{fs.closeSync(out);}
  const decoded=decodedHash(candidate);
  const raw=rawHash.digest('hex'),exact=decoded.bytes===originalBytes&&decoded.sha256===raw;
  if(!exact||fs.statSync(source).size!==stat.size||fs.statSync(source).mtimeMs!==stat.mtimeMs)throw Error('Exact preservation failed');
  fs.mkdirSync(folder,{recursive:true});
  fs.writeFileSync(receipt,JSON.stringify({source,candidate,version,original_bytes:originalBytes,compressed_bytes:compressedBytes,source_sha256:raw,compressed_sha256:compressedHash.digest('hex'),frames,decoded_identical:exact,replaced_after_native_reopen:false,encoding:'Checksummed concatenated Zstandard frames; exact original bytes recoverable'},null,2));
  console.log(JSON.stringify({candidate,originalBytes,compressedBytes,exact}));
}
