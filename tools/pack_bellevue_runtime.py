"""Browser-compatible lossless decoded-pixel image encoding; preserve every geometry byte."""
import json,struct,io,hashlib,argparse,zlib
from pathlib import Path
from PIL import Image
parser=argparse.ArgumentParser();parser.add_argument('--version');args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1];V=args.version or json.loads((ROOT/'runtime/bellevue_working.json').read_text())['version'];assets=ROOT/'web/assets'
assert __import__('re').fullmatch(r'G1_\d{3}(?:r\d+)?',V)
raw=(assets/f'{V}_bellevue.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0]
j=json.loads(raw[20:20+length]);old=raw[28+length:];image_ids={im['bufferView']:im for im in j['images']}
binary=bytearray();proof=[];geometry_hash=hashlib.sha256();output_geometry_hash=hashlib.sha256()
def recompress_png_losslessly(blob):
    # Pillow decodes 16-bit RGB PNG to 8-bit RGB. Preserve the original filtered
    # scanline bytes and IHDR instead; only the zlib stream changes.
    assert blob[:8]==b'\x89PNG\r\n\x1a\n'
    chunks=[];pos=8
    while pos<len(blob):
        n=struct.unpack_from('>I',blob,pos)[0];typ=blob[pos+4:pos+8];data=blob[pos+8:pos+8+n]
        crc=struct.unpack_from('>I',blob,pos+8+n)[0];assert zlib.crc32(typ+data)&0xffffffff==crc
        chunks.append((typ,data));pos+=12+n
    assert pos==len(blob) and chunks[0][0]==b'IHDR' and chunks[-1][0]==b'IEND'
    decoded=zlib.decompress(b''.join(data for typ,data in chunks if typ==b'IDAT'))
    compressed=zlib.compress(decoded,6);assert zlib.decompress(compressed)==decoded
    out=bytearray(blob[:8]);inserted=False
    for typ,data in chunks:
        if typ==b'IDAT':
            if inserted:continue
            data=compressed;inserted=True
        out.extend(struct.pack('>I',len(data))+typ+data+struct.pack('>I',zlib.crc32(typ+data)&0xffffffff))
    return bytes(out),{'source_bit_depth':blob[24],'runtime_bit_depth':blob[24],
        'filtered_scanlines_identical':True,'scanline_sha256':hashlib.sha256(decoded).hexdigest()}

for i,view in enumerate(j['bufferViews']):
    off=view.get('byteOffset',0);blob=old[off:off+view['byteLength']]
    if i in image_ids:
        image=image_ids[i];source_image=Image.open(io.BytesIO(blob))
        mode='RGBA' if 'A' in source_image.getbands() or 'transparency' in source_image.info else 'RGB'
        if blob[:8]==b'\x89PNG\r\n\x1a\n' and blob[24]==16:
            encoded,extra=recompress_png_losslessly(blob)
            size=source_image.size
        else:
            decoded=source_image.convert(mode);buf=io.BytesIO();decoded.save(buf,format='PNG',compress_level=6)
            encoded=buf.getvalue();again=Image.open(io.BytesIO(encoded)).convert(mode)
            assert decoded.size==again.size and decoded.tobytes()==again.tobytes()
            size=decoded.size;extra={'source_bit_depth':8,'runtime_bit_depth':8}
        proof.append({'name':image['name'],'buffer_view':i,'size':size,'mode':mode,'decoded_pixels_identical':True,'source_bytes':len(blob),'runtime_bytes':len(encoded),'runtime_sha256':hashlib.sha256(encoded).hexdigest(),**extra})
        blob=encoded;image['mimeType']='image/png'
    else:geometry_hash.update(blob);output_geometry_hash.update(blob)
    while len(binary)%4:binary.append(0)
    view['byteOffset']=len(binary);view['byteLength']=len(blob);binary.extend(blob)
while len(binary)%4:binary.append(0)
j['buffers']=[{'byteLength':len(binary)}];js=json.dumps(j,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
path=assets/f'{V}_bellevue_runtime.glb'
path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary)
# Read the actual written file, not just the in-memory construction, when asserting
# that runtime repacking retained every non-image buffer byte.
written=path.read_bytes();written_length=struct.unpack_from('<I',written,12)[0]
written_json=json.loads(written[20:20+written_length]);written_bin=written[28+written_length:]
written_hash=hashlib.sha256()
for i,view in enumerate(written_json['bufferViews']):
    if i in image_ids:continue
    off=view.get('byteOffset',0);written_hash.update(written_bin[off:off+view['byteLength']])
assert written_hash.hexdigest()==geometry_hash.hexdigest()
for p in proof:
    view=written_json['bufferViews'][p['buffer_view']];off=view.get('byteOffset',0)
    assert hashlib.sha256(written_bin[off:off+view['byteLength']]).hexdigest()==p['runtime_sha256']
metadata=json.loads((assets/f'{V}_bellevue.json').read_text());metadata['authored_runtime']={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(assets/f'{V}_bellevue.json').write_text(json.dumps(metadata,indent=2))
report={'version':V,'bytes':path.stat().st_size,'images':proof,'geometry_source_hash':geometry_hash.hexdigest(),'geometry_runtime_hash':written_hash.hexdigest(),'written_file_checked':True,'source_export_retained':True}
(ROOT/f'evidence/{V}/runtime_encoding.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
