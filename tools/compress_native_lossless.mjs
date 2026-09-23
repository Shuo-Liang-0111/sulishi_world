// Reversible storage encoding of one old raw checkpoint. Never edits its data.
// Produces a separate candidate first; replacement needs a Blender reopen receipt.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import z from 'node:zlib';
import {pipeline} from 'node:stream/promises';
import {Writable} from 'node:stream';
const root=path.resolve('F:/MyWorld/ZurichWorld');
const source=path.join(root,'native/G1_017_canopy_continuity_working.blend');
const candidate=path.join(root,'native/G1_017_lossless_encoding_check.blend');
const receipt=path.join(root,'evidence/G1_017/native_lossless_encoding.json');
for(const p of [source,candidate])if(path.dirname(fs.realpathSync(path.dirname(p))+'/'+path.basename(p))!==path.join(root,'native'))throw Error('Path escaped native directory');
if(process.argv.includes('--replace-verified')){
  const r=JSON.parse(fs.readFileSync(receipt,'utf8'));
  const q=JSON.parse(fs.readFileSync(path.join(root,'evidence/G1_017/lossless_native_reopen.json'),'utf8'));
  if(!r.decoded_identical || q.version!=='G1_017' || q.file.replaceAll('\\','/').toLowerCase()!==candidate.replaceAll('\\','/').toLowerCase())throw Error('Missing exact reopen evidence');
  const hash=async file=>{const h=crypto.createHash('sha256');for await(const b of fs.createReadStream(file))h.update(b);return h.digest('hex');};
  if(await hash(source)!==r.source_sha256 || await hash(candidate)!==r.compressed_sha256)throw Error('A file changed after verification');
  fs.renameSync(candidate,source);
  r.replaced_after_native_reopen=true;r.final_path=source;fs.writeFileSync(receipt,JSON.stringify(r,null,2));
  console.log(JSON.stringify({reversible:true,bytes_reclaimed:r.original_bytes-r.compressed_bytes,path:source}));
} else {
  if(fs.existsSync(candidate)||fs.existsSync(receipt))throw Error('Inspect prior compression before retry');
  const stat=fs.statSync(source);const fd=fs.openSync(source,'r');const header=Buffer.alloc(7);fs.readSync(fd,header,0,7,0);fs.closeSync(fd);
  if(header.toString()!=='BLENDER')throw Error('Source is not an uncompressed Blender file');
  const rawHash=crypto.createHash('sha256'),compressedHash=crypto.createHash('sha256');
  const output=fs.openSync(candidate,'wx');let originalBytes=0,compressedBytes=0,frames=0;
  try{
    for await(const chunk of fs.createReadStream(source,{highWaterMark:256*1024})){
      rawHash.update(chunk);originalBytes+=chunk.length;
      const data=z.zstdCompressSync(chunk,{params:{[z.constants.ZSTD_c_compressionLevel]:4,[z.constants.ZSTD_c_checksumFlag]:1}});
      fs.writeSync(output,data);compressedHash.update(data);compressedBytes+=data.length;frames++;
    }
    fs.fsyncSync(output);
  } finally {fs.closeSync(output);}
  const decoded=crypto.createHash('sha256');let decodedBytes=0;
  await pipeline(fs.createReadStream(candidate),z.createZstdDecompress(),new Writable({write(b,e,cb){decoded.update(b);decodedBytes+=b.length;cb();}}));
  const raw=rawHash.digest('hex');const exact=decodedBytes===originalBytes&&decoded.digest('hex')===raw;
  if(!exact||fs.statSync(source).size!==stat.size||fs.statSync(source).mtimeMs!==stat.mtimeMs)throw Error('Exact data preservation failed');
  fs.mkdirSync(path.dirname(receipt),{recursive:true});
  const r={source,candidate,original_bytes:originalBytes,compressed_bytes:compressedBytes,source_sha256:raw,compressed_sha256:compressedHash.digest('hex'),frames,decoded_identical:exact,replaced_after_native_reopen:false,encoding:'Concatenated independently checksummed Zstandard frames; exact original bytes recoverable'};
  fs.writeFileSync(receipt,JSON.stringify(r,null,2));console.log(JSON.stringify({candidate,originalBytes,compressedBytes,exact}));
}
