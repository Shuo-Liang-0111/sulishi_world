"""Source-only geometry preparation; no Blender use, no writes outside this package."""
from pathlib import Path
import json, hashlib, struct, math
import numpy as np
from PIL import Image
from shapely.geometry import shape, Polygon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
A=np.array([42.906,83.491]);B=np.array([51.020,74.613]);U=(B-A)/np.linalg.norm(B-A);N=np.array([U[1],-U[0]])
W=np.linalg.norm(B-A)
def Q(v):
    v=np.asarray(v);return np.column_stack([(v[:,:2]-A)@U,(v[:,:2]-A)@N,v[:,2]])
def P(u,v):return A+U*u+N*v
manifest=json.loads((OUT/'derived/source_node_manifest.json').read_text())
origin=np.array(manifest['origin']);alltri=[];alluv=[];nodeids=[];textures={}
for o in manifest['items']:
    raw=Path(o['geometry']).read_bytes();nv,nf=struct.unpack_from('<II',raw)
    v=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3).astype(float)+np.array(o['mbs'][:3])-origin
    uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2).copy()
    alltri.extend(v.reshape(-1,3,3));alluv.extend(uv.reshape(-1,3,2));nodeids.extend([o['node']]*(nv//3));textures[o['node']]=o['texture']
tri=np.array(alltri);q=Q(tri.reshape(-1,3)).reshape(-1,3,3);uv=np.array(alluv)
np.savez_compressed(OUT/'derived/source_triangles.npz',world=tri,local=q,uv=uv,node=np.array(nodeids))
def z_samples(u,v):
    xy=P(u,v);a=tri[:,0,:2];d1=tri[:,1,:2]-a;d2=tri[:,2,:2]-a
    det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0];valid=np.abs(det)>1e-8
    safe=np.where(valid,det,1);t=xy-a
    b=(t[:,0]*d2[:,1]-t[:,1]*d2[:,0])/safe;c=(d1[:,0]*t[:,1]-d1[:,1]*t[:,0])/safe
    hits=np.where(valid&(b>=0)&(c>=0)&(b+c<=1))[0]
    return [dict(z=float(tri[i,0,2]+b[i]*(tri[i,1,2]-tri[i,0,2])+c[i]*(tri[i,2,2]-tri[i,0,2])),node=nodeids[i]) for i in hits]
samples=[dict(u=float(u),v=float(v),xy=P(u,v).tolist(),hits=z_samples(u,v)) for u in np.linspace(-1,W+1,15) for v in [-.3,.3,.8,1.3,1.8,2.3,3,4.05,5,6,7,8,10]]
features=[]
for layer in ['av_ei_flaechenelement_a','av_ei_linienelement']:
    data=json.loads((OUT/'derived'/f'{layer}_local.geojson').read_text())
    s=Polygon([P(u,v)+origin[:2] for u,v in [(-2,-1),(W+2,-1),(W+2,10),(-2,10)]])
    for f in data['features']:
        g=shape(f['geometry'])
        if g.intersects(s):features.append(f)
spec=dict(origin=origin.tolist(),A=A.tolist(),B=B.tolist(),U=U.tolist(),N=N.tolist(),width_m=W,
    identification=dict(egid=2372568,av_building='av_bo_boflaeche_a.38215',address='Stadelhoferstrasse 8',address_id='av_geb_gebaeudeadresse_t.328'),
    canopy_survey=dict(front_corners=[[39.917,80.754,15.307],[48.016,71.851,15.307]],back_corners=[[42.906,83.491,15.307],[51.02,74.613,15.307]],warning='LOD2 represents canopy as 0.5 m prism; do not copy this as fabrication thickness'),
    scope_local=dict(u=[-.32,W+.32],v=[-.72,8.0],z=[9.0,15.8]),
    scope_basis='Central three-arch entrance only; facade width and canopy outline from 2025 surveyed model. Forecourt edge and material extents to be refined after photograph review.',
    measurements_pending=['landing and forecourt heights','step profile','opening widths/spring heights','exact boundary seams'])
(OUT/'derived/site_spec.json').write_text(json.dumps(spec,indent=2))
(OUT/'derived/ground_source_samples.json').write_text(json.dumps(samples,indent=2))
(OUT/'derived/entrance_survey_features.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features)))
print('frame',json.dumps(spec),flush=True)
print('features',[(f['id'],f['properties'].get('art_txt'),shape(f['geometry']).bounds) for f in features],flush=True)

# Orthographic source diagnostic, preserving captured RGB and original UVs.
# This is a source inspection image, never a final material or evidence render.
def raster(name,axes,depth_axis,bounds,size,greater=True):
    width,height=size;x0,x1,y0,y1=bounds
    coords=np.stack([(q[:,:,axes[0]]-x0)/(x1-x0)*(width-1),(y1-q[:,:,axes[1]])/(y1-y0)*(height-1)],axis=-1)
    img=np.zeros((height,width,3),np.uint8)+205;zbuf=np.full((height,width),-np.inf if greater else np.inf)
    texcache={}
    for i,c in enumerate(coords):
        # Restrict front elevation to the relevant neighborhood.
        if depth_axis==1 and (q[i,:,1].min()>12 or q[i,:,1].max()<-2):continue
        xa=max(0,int(np.floor(c[:,0].min())));xb=min(width-1,int(np.ceil(c[:,0].max())))
        ya=max(0,int(np.floor(c[:,1].min())));yb=min(height-1,int(np.ceil(c[:,1].max())))
        if xb<xa or yb<ya:continue
        d1=c[1]-c[0];d2=c[2]-c[0];det=d1[0]*d2[1]-d1[1]*d2[0]
        if abs(det)<1e-6:continue
        xx,yy=np.meshgrid(np.arange(xa,xb+1),np.arange(ya,yb+1));tx=xx-c[0,0];ty=yy-c[0,1]
        b=(tx*d2[1]-ty*d2[0])/det;cc=(d1[0]*ty-d1[1]*tx)/det;a=1-b-cc
        dep=a*q[i,0,depth_axis]+b*q[i,1,depth_axis]+cc*q[i,2,depth_axis]
        mask=(a>=0)&(b>=0)&(cc>=0)&((dep>zbuf[ya:yb+1,xa:xb+1]) if greater else (dep<zbuf[ya:yb+1,xa:xb+1]))
        if not mask.any():continue
        node=nodeids[i]
        if node not in texcache:texcache[node]=np.array(Image.open(textures[node]).convert('RGB'))
        tex=texcache[node];uvp=a[:,:,None]*uv[i,0]+b[:,:,None]*uv[i,1]+cc[:,:,None]*uv[i,2]
        px=np.clip(np.rint(uvp[:,:,0]*(tex.shape[1]-1)).astype(int),0,tex.shape[1]-1)
        py=np.clip(np.rint(uvp[:,:,1]*(tex.shape[0]-1)).astype(int),0,tex.shape[0]-1)
        block=img[ya:yb+1,xa:xb+1];block[mask]=tex[py[mask],px[mask]];zbuf[ya:yb+1,xa:xb+1][mask]=dep[mask]
    Image.fromarray(img).save(OUT/'evidence'/name)
raster('SOURCE_ONLY_front_orthographic.png',(0,2),1,(-3,W+3,9,25),(1400,1240))
raster('SOURCE_ONLY_top_orthographic.png',(0,1),2,(-4,W+4,-3,11),(1400,960))
fig,ax=plt.subplots(figsize=(12,6))
for v in [0.3,1.3,2.3,3,4.05,5,6,7,8,10]:
    rows=[s for s in samples if s['v']==v]
    xs=[];ys=[]
    for s in rows:
        hits=[h['z'] for h in s['hits'] if 9<h['z']<13]
        if hits:xs.append(s['u']);ys.append(max(hits))
    ax.plot(xs,ys,'.-',label=f'v={v}m')
ax.legend(ncol=3);ax.set(xlabel='Facade u (m)',ylabel='Z above LN02 400m (source mesh)',title='Unfiltered source ground/step hits; obstructions may contaminate samples');ax.grid()
fig.savefig(OUT/'evidence/source_ground_profiles.png',dpi=130);plt.close(fig)
print('source diagnostic images written',flush=True)
