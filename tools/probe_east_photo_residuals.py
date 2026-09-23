"""Read-only rays tied to visible native image defects, using retained source geometry."""
import json,struct,argparse
from pathlib import Path
import numpy as np
from shapely.geometry import Point,shape
R=Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['G1_016r1','G1_017'],default='G1_016r1');V=parser.parse_args().version;origin=np.array([2683775,1246700,400.])
work=json.loads((R/'runtime/station_road_working.json').read_text());assert work['version']==V
cut=json.loads((R/work['source_cut_file']).read_text());overrides={str(x['node']):x for x in cut['overrides']}
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
camera_version=V if (R/'web/assets'/f'{V}_bellevue.json').exists() else 'G1_016r1'
meta=json.loads((R/'web/assets'/f'{camera_version}_bellevue.json').read_text())
trees=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
guards=json.loads((R/'derived/bellevue/south_context/photo_cut_basis.json').read_text())['protected_records']
def native(v):return np.array([v[0],-v[2],v[1]])
camera=meta['cameras']['BE_QA_SOUTH_EAST_INFO_WIDE'];pos=native(camera['position'])+origin
fwd=native(np.array(camera['target'])-camera['position']);fwd/=np.linalg.norm(fwd)
right=np.cross(fwd,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,fwd)
rays=[]
points=[(351,86,'left upper floating canopy'),(602,181,'central floating sliver'),(827,222,'central upper canopy slab'),(1023,192,'right isolated canopy fragment')] if V=='G1_016r1' else [(247,109,'remaining left floating canopy'),(303,114,'remaining dark triangular scrap'),(380,214,'remaining thin upright scrap'),(520,258,'remaining canopy block')]
for x,y,label in points:
    ty=np.tan(np.deg2rad(camera['fov']/2));d=fwd+right*(2*x/1280-1)*ty*(1280/840)+up*(1-2*y/840)*ty;d/=np.linalg.norm(d)
    rays.append({'image':'BE_QA_SOUTH_EAST_INFO_WIDE.png','pixel':[x,y],'label':label,'o':pos,'d':d})
pano=json.loads((R/'evidence'/camera_version/'service_reflection_east_info.json').read_text());pp=native(pano['position_yup'])+origin
for x,y,label in ([(737,38,'upper spiral remnant'),(746,113,'middle spiral remnant'),(737,182,'lower spiral remnant'),(351,65,'small floating top fragment')] if V=='G1_016r1' else []):
    az=(x/1024-.5)*2*np.pi;el=(.5-y/512)*np.pi;d=np.array([np.sin(az)*np.cos(el),np.cos(az)*np.cos(el),np.sin(el)])
    rays.append({'image':'service_reflection_east_info.png','pixel':[x,y],'label':label,'o':pp,'d':d})
def triangles(item):
    key=str(item['node']);c=np.array(item['mbs'][:3])
    if key in overrides:v=np.asarray(overrides[key]['vertices'],float).reshape(-1,3)
    else:
        raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0];v=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3).astype(float)
    return (v+c).reshape(-1,3,3)
reports=[]
for ray in rays:
    o,d=ray.pop('o'),ray.pop('d');hits=[]
    for item in manifest['items']:
        m=np.array(item['mbs']);delta=m[:3]-o;along=delta@d
        if along+m[3]<0 or along-m[3]>150 or np.linalg.norm(delta-d*along)>m[3]+.02:continue
        t=triangles(item)
        if not len(t):continue
        a=t[:,0];e1=t[:,1]-a;e2=t[:,2]-a;p=np.cross(d,e2);det=np.sum(e1*p,axis=1);valid=np.abs(det)>1e-9
        inv=np.divide(1,det,out=np.zeros_like(det),where=valid);s=o-a;u=np.sum(s*p,axis=1)*inv;q=np.cross(s,e1);v=q@d*inv;dist=np.sum(e2*q,axis=1)*inv
        ids=np.flatnonzero(valid&(u>=0)&(v>=0)&(u+v<=1)&(dist>0)&(dist<150))
        for i in ids:
            point=o+d*dist[i];near=sorted(trees,key=lambda f:np.linalg.norm(np.asarray(f['geometry']['coordinates'])[:2]-point[:2]))[:2]
            hits.append({'node':item['node'],'face':int(i),'distance_m':float(dist[i]),'lv95':point.tolist(),
                         'near_trees':[{'id':f['properties']['objectid'],'height':f['properties']['hoehe'],'horizontal_distance_m':float(np.linalg.norm(np.asarray(f['geometry']['coordinates'])[:2]-point[:2]))} for f in near],
                         'inside_original_guards':[g['id'] for g in guards if shape(g['geometry']).covers(Point(point[:2]))]})
    hits.sort(key=lambda h:h['distance_m']);reports.append({**ray,'source_hits':hits[:3]})
(R/'evidence'/V/'upper_photo_residual_rays.json').write_text(json.dumps({'version':V,'native_geometry_unchanged':True,'rays':reports},indent=2))
print(json.dumps(reports,indent=2))
