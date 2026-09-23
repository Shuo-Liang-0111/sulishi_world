"""Bounded photo replacement for rebuilt bridge and diagnosed cyan water.

Bridge underside replacement follows reconstructed geometry. Outside it, the
water classification is a local source-atlas heuristic requiring visual review;
it is not a general segmentation claim. Mooring structures are protected.
"""
from pathlib import Path
import argparse,ast,hashlib,json,struct
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import shape,Point,Polygon,mapping
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/quaibruecke_water'
parser=argparse.ArgumentParser();parser.add_argument('--full-water',action='store_true');args=parser.parse_args()
P=json.loads((D/'build_input.json').read_text(encoding='utf-8'))
B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text(encoding='utf-8'))
water=shape(P['water']);bridge=shape(P['bridge'])
A=np.array(B['bridge_anchor']);T=np.array(B['bridge_along']);N=np.array(B['bridge_across']);coef=np.array(B['bridge_deck_coefficients'])
def deck(x,y):
    st,d=(np.array([x,y])-A)@np.array([T,N]).T
    return float(coef@[1,st,st*st,d])
features=json.loads((R/'sources/features/av_ei_flaechenelement_a.geojson').read_text(encoding='utf-8'))['features']
docks=unary_union([shape(f['geometry']).buffer(10) for f in features if f['properties'].get('art_txt')=='Landungssteg'])
region=(water if args.full_water else water.intersection(bridge.buffer(35))).difference(docks)
helper=ast.parse((R/'tools/prepare_limmat_sidewalk_cut.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in {'clip','fan','subtract'}],type_ignores=[]),'bounded_cut_helpers','exec'))
volumes=[]
for part in P['parts']:
    if part['name'].startswith('DECK_'):
        v=np.array(part['vertices']);volumes.append(dict(id=part['name'],mask=shape(part['plan']),
            lo=403.,hi=float(v[:,2].min()+400+.035),relative=False))
# The retained first span is now supported by the same rebuilt water and piers.
for part in B['parts']:
    if part['name'].startswith('BRIDGE_SLAB_'):
        v=np.array(part['vertices']);volumes.append(dict(id='EAST_'+part['name'],mask=shape(part['plan']),
            lo=403.,hi=float(v[:,2].min()+400+.035),relative=False))
if args.full_water:volumes=[] # The024 bridge-volume replacement is already saved.
basename='quaibruecke_water_structure_cut.json' if args.full_water else 'quaibruecke_opening_cut.json'
basepath=R/'derived/bellevue/west_context'/basename;base=json.loads(basepath.read_text(encoding='utf-8'))
overrides={str(r['node']):r for r in base['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text(encoding='utf-8'))
bary=np.array([[a,b,1-a-b] for a in [.12,.30,.48,.66] for b in [.12,.30,.48,.66] if a+b<.91])
replaced=[];changed=[];counts=[];samples=[]
for item in manifest['items']:
    m=np.array(item['mbs']);centre=Point(m[:2]);near=[q for q in volumes if centre.distance(q['mask'])<=m[3]]
    if not near and centre.distance(region)>m[3]:continue
    key=str(item['node'])
    if key in overrides:
        q=overrides[key];xyz=np.array(q['vertices']).reshape(-1,3);uv=np.array(q['uv_source_v_unflipped']).reshape(-1,2)
    else:
        raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
        xyz=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)
        uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2)
    atlas=Image.open(item['texture']).convert('RGB');pixels=np.array(atlas);size=np.array(atlas.size)
    vv=[];uu=[];dirty=False;removed_water=0
    for face,(tri,tex) in enumerate(zip((xyz+m[:3]).reshape(-1,3,3),uv.reshape(-1,3,2))):
        poly=Polygon(tri[:,:2]);cent=Point(tri.mean(0)[:2]);pieces=[np.c_[tri,tex]]
        if region.covers(cent) and poly.distance(docks)>.10 and tri[:,2].min()>401 and tri[:,2].max()<410.3:
            pix=tex*size
            lo=np.maximum(np.floor(pix.min(0)).astype(int),0);hi=np.minimum(np.ceil(pix.max(0)).astype(int)+1,size)
            mask=Image.new('L',tuple(np.maximum(hi-lo,1)),0)
            ImageDraw.Draw(mask).polygon([tuple(p-lo) for p in pix],fill=255)
            rgb=pixels[lo[1]:hi[1],lo[0]:hi[0]][np.array(mask)>0].astype(float)
            if not len(rgb):rgb=pixels[np.clip(int(pix[:,1].mean()),0,size[1]-1),np.clip(int(pix[:,0].mean()),0,size[0]-1)][None,:].astype(float)
            cyan=(rgb[:,1]>rgb[:,0]*1.16+4)&(rgb[:,2]>rgb[:,0]*1.16+4)&(abs(rgb[:,1]-rgb[:,2])<75)
            fraction=float(cyan.mean())
            # First atlas review found small white boats missed by sparse
            #barycentric samples. Inspect every source texel and protect even
            #small neutral bright islands, rather than erasing these objects.
            object_like=(rgb.max(1)>95)&(rgb[:,0]>.72*rgb[:,1])&(rgb[:,0]>.72*rgb[:,2])
            if fraction>=.995 and not object_like.any():
                overlap=poly.intersection(region).area/max(poly.area,1e-10)
                rec=dict(node=key,working_face=face,cyan_fraction=fraction,centre=tri.mean(0).tolist(),
                    source_texture_sha256=item['texture_sha256'],projected_overlap_fraction=overlap)
                if overlap>.995 or (poly.area<1e-8 and region.buffer(-.05).covers(cent)):
                    pieces=[];dirty=True;removed_water+=1;replaced.append(rec)
                    rec['projected_area_m2']=poly.area
                    samples.append((rec,tex.copy(),item['texture']))
                else:
                    pieces,did=subtract(pieces[0],dict(id='local_cyan_water',mask=region,lo=401.,hi=410.3,relative=False))
                    if did:dirty=True;removed_water+=1;replaced.append(rec)
        for vol in near:
            if poly.distance(vol['mask'])>.001 or tri[:,2].min()>vol['hi'] or tri[:,2].max()<vol['lo']:continue
            nxt=[]
            for piece in pieces:
                out,did=subtract(piece,vol);nxt.extend(out);dirty=dirty or did
            pieces=nxt
            if not pieces:break
        for piece in pieces:vv.extend((piece[:,:3]-m[:3]).tolist());uu.extend(piece[:,3:].tolist())
    if dirty:
        overrides[key]={'node':item['node'],'vertices':vv,'uv_source_v_unflipped':uu,'source_sha256':item['geometry_sha256']}
        changed.append(key);counts.append(dict(node=key,before_triangles=len(xyz)//3,after_triangles=len(vv)//3,water_faces=removed_water))
out=R/'derived/bellevue/west_context'/('quaibruecke_full_water_cut.json' if args.full_water else 'quaibruecke_water_structure_cut.json')
label='G1_024r1 entire already-authored water footprint' if args.full_water else 'G1_024 actual four-pier bridge underside/water context'
out.write_text(json.dumps({'mask_basis':base['mask_basis']+'; '+label+'. Bounded cyan source-atlas water replacement; mooring/dock10m regions protected. Original nodes retained.',
    'base_cut_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'overrides':list(overrides.values()),
    'changed_nodes':len(overrides),'water_structure_changed_nodes':changed},separators=(',',':')),encoding='utf-8')
(D/('full_water_photo_cut_basis.json' if args.full_water else 'photo_cut_basis.json')).write_text(json.dumps({'region':mapping(region),'protected_moorings':mapping(docks),
    'changed_nodes':counts,'water_faces':replaced,'classifier':'local cyan texture heuristic plus source water, not a general segmentation guarantee',
    'visual_review_required':True},indent=2),encoding='utf-8')
tiles=[];by_node={}
for sample in samples:
    key=sample[0]['node']
    if key not in by_node or sample[0]['projected_area_m2']>by_node[key][0]['projected_area_m2']:by_node[key]=sample
for rec,tex,path in by_node.values():
    atlas=Image.open(path).convert('RGB');pix=tex*np.array(atlas.size)
    lo=np.maximum(np.floor(pix.min(0)).astype(int)-4,0);hi=np.minimum(np.ceil(pix.max(0)).astype(int)+4,atlas.size)
    crop=atlas.crop((*lo,*hi)).resize((240,170));draw=ImageDraw.Draw(crop)
    pts=(pix-lo)/np.maximum(hi-lo,1)*[240,170];draw.line([tuple(p) for p in [*pts,pts[0]]],fill='magenta',width=2)
    tile=Image.new('RGB',(250,200),'white');tile.paste(crop,(5,25));ImageDraw.Draw(tile).text((5,5),f"{rec['node']} f{rec['working_face']}",fill='black');tiles.append(tile)
if tiles:
    montage=Image.new('RGB',(1000,200*((len(tiles)+3)//4)),'white')
    for i,tile in enumerate(tiles):montage.paste(tile,((i%4)*250,(i//4)*200))
    montage.save(D/('full_water_source_atlas_review.png' if args.full_water else 'water_source_atlas_review.png'))
print(json.dumps({'changed_nodes':changed,'water_faces_selected':len(replaced),'override_bytes':out.stat().st_size}))
