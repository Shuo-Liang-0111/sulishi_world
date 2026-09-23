"""Recover visible yellow bars using official walking crossings + SWISSIMAGE.

No network or rendering. This produces review candidates, never an automatic
claim that every crossing or its current legal layout has been reproduced.
"""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image
from shapely.geometry import shape,box,MultiPoint,mapping,Polygon
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/transport'
B=[2683500,1246765,2683650,1246910];domain=box(*B)
photo=ROOT/'sources/references/swissimage-bellevue-detail.jpg';im=Image.open(photo)
rgb=np.asarray(im).astype(float)/255;hsv=np.asarray(im.convert('HSV')).astype(float)/255
H,W=rgb.shape[:2];dx=(B[2]-B[0])/W;dy=(B[3]-B[1])/H
xs=B[0]+(np.arange(W)+.5)*dx;ys=B[3]-(np.arange(H)+.5)*dy
yellow=(hsv[:,:,0]>.105)&(hsv[:,:,0]<.19)&(hsv[:,:,1]>.29)&(hsv[:,:,2]>.24)
features=json.loads((ROOT/'sources/features/tbl_routennetz.geojson').read_text())['features']
routes=[f for f in features if f['properties'].get('fuss')==1 and 'berquerung' in str(f['properties'].get('name')) and shape(f['geometry']).intersects(domain)]
road=shape(json.loads((OUT/'road_input.json').read_text())['road_mask'])
bars=[];notes=[]
for f in routes:
    route=shape(f['geometry']);roi=route.buffer(3.0).intersection(domain);b=roi.bounds
    ix=np.where((xs>=b[0])&(xs<=b[2]))[0];iy=np.where((ys>=b[1])&(ys<=b[3]))[0]
    if not len(ix) or not len(iy):continue
    sub=yellow[np.ix_(iy,ix)].copy();xx,yy=np.meshgrid(xs[ix],ys[iy]);
    from shapely import contains_xy
    sub &= contains_xy(roi,xx,yy)
    # Fill only compression pinholes. The physical bar is fitted to observed pixels.
    sub=ndimage.binary_closing(sub,structure=np.ones((2,2)))
    labels,n=ndimage.label(sub);direction=np.array(route.coords[-1])-np.array(route.coords[0]);direction/=np.linalg.norm(direction)
    count=0
    for k in range(1,n+1):
        rows,cols=np.where(labels==k)
        if len(rows)<18:continue
        points=np.column_stack((xs[ix[cols]],ys[iy[rows]]));rect=MultiPoint(points).minimum_rotated_rectangle
        if rect.geom_type!='Polygon':continue
        xy=np.array(rect.exterior.coords)[:4];edges=np.roll(xy,-1,axis=0)-xy;lengths=np.linalg.norm(edges,axis=1)
        long=float(lengths.max());short=float(lengths.min());d=edges[np.argmax(lengths)]/long
        fill=len(rows)*dx*dy/max(rect.area,1e-6);align=abs(np.dot(d,direction))
        if not(.24<short<.85 and 1.8<long<6.2 and long/short>3 and fill>.42 and align<.52):continue
        if any(rect.intersection(shape(a['geometry'])).area>.5*rect.area for a in bars):continue
        # Pixel centres undershoot a photographed paint edge by about half a pixel.
        rect=rect.buffer(dx*.35,join_style=2).intersection(road)
        if rect.area<.45:continue
        bars.append({'type':'Feature','properties':{'id':f'BE_CROSSING_BAR_{len(bars):03d}','route_id':f['id'],'route_name':f['properties']['name'],'observed_length_m':long,'observed_width_m':short,'pixel_fill_ratio':float(fill),'status':'orthophoto interpreted candidate; visual review required','plan_basis':'Official walking connection plus observed SWISSIMAGE yellow paint pixels; pixel-edge fit is approximate'},'geometry':mapping(rect)})
        count+=1
    notes.append({'id':f['id'],'name':f['properties']['name'],'candidate_bars':count})
record={'type':'FeatureCollection','features':bars,'source_image_sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'routes_reviewed':notes,'interpretation_status':'candidate_not_yet_accepted'}
(OUT/'crossings_candidates.geojson').write_text(json.dumps(record,ensure_ascii=False,indent=2))
fig,ax=plt.subplots(figsize=(12,12),layout='constrained');ax.imshow(im,extent=[B[0],B[2],B[1],B[3]])
for f in routes:
    xy=np.array(shape(f['geometry']).coords);ax.plot(xy[:,0],xy[:,1],color='#ffffff',lw=.65,alpha=.7)
for f in bars:
    g=shape(f['geometry']);pp=g.geoms if hasattr(g,'geoms') else [g]
    for p in pp:
        if p.geom_type!='Polygon':continue
        xy=np.array(p.exterior.coords);ax.plot(xy[:,0],xy[:,1],c='#00ffff',lw=.65)
ax.set_xlim(B[0],B[2]);ax.set_ylim(B[1],B[3]);ax.set_aspect('equal');ax.ticklabel_format(style='plain',useOffset=False)
ax.set_title('Visible crossing paint candidates / cyan; official walking links / white')
fig.savefig(OUT/'crossings_interpretation.png',dpi=145)
print(json.dumps({'routes':len(routes),'bars':len(bars),'routes_reviewed':notes},ensure_ascii=False))
