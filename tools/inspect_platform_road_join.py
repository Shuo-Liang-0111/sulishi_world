"""Measure actual authored platform/road join before constructing its missing face."""
import json
from pathlib import Path
import numpy as np
from shapely.geometry import shape, Polygon, Point
from shapely import STRtree
from shapely.ops import nearest_points

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
roads=json.loads((ROOT/'derived/bellevue/transport/road_input.json').read_text())
origin=np.array(data['origin'][:2])
platform=np.array(data['ground_surface_triangles'])
road=np.array([t for p in roads['pieces'] if p['kind']=='road_asphalt' for t in p['triangles']])

class Surface:
    def __init__(self,t):
        self.t=t;self.polys=[Polygon(v[:,:2]) for v in t];self.tree=STRtree(self.polys)
    def sample(self,xy):
        p=Point(xy);idx=int(self.tree.nearest(p));poly=self.polys[idx];q=np.array(nearest_points(poly,p)[0].coords[0])
        t=self.t[idx];ab=(t[1:,:2]-t[0,:2]).T
        weights=np.linalg.solve(ab,q-t[0,:2]);z=float(t[0,2]+weights@(t[1:,2]-t[0,2]))
        return z,float(p.distance(poly))

if __name__=='__main__':
    top=Surface(platform);bottom=Surface(road);ring=shape(data['island']).exterior
    rows=[]
    for s in np.arange(0,ring.length,.5):
        xy=np.array(ring.interpolate(s).coords[0])-origin
        z,dt=top.sample(xy);rz,dr=bottom.sample(xy)
        rows.append({'station_m':float(s),'lv95':(xy+origin).tolist(),'top_ln02':z+400,'road_ln02':rz+400,'upstand_m':z-rz,'road_distance_m':dr,'platform_distance_m':dt})
    heights=np.array([r['upstand_m'] for r in rows]);dist=np.array([r['road_distance_m'] for r in rows])
    result={'samples':rows,'summary':{'upstand_quantiles_m':np.quantile(heights,[0,.05,.5,.95,1]).tolist(),'road_distance_max_m':float(dist.max()),'negative_upstand_count':int((heights<0).sum()),'warning':'Approximate photograph-derived grade supports; not surveyed curb height or accepted accessibility.'}}
    (ROOT/'derived/bellevue/transport/platform_join.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['summary']))
