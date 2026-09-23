from pathlib import Path
import json,numpy as np
from shapely.geometry import Point,box
from shapely.affinity import scale
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parents[1];out=[]
for side,us,sg in [('W',.34,-1),('M',.77,1)]:
 lo,hi=sorted([us+sg*.66,us+sg*.015]);outer=box(lo,-1.24,hi,1.44);holes=unary_union([scale(Point(us+sg*.24,v).buffer(1,quad_segs=48),xfact=.225,yfact=.195,origin=(us+sg*.24,v)) for v in [-.8,.1,1.0]])
 tt=[list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(outer.difference(holes)).geoms];out.append({'side':side,'us':us,'sg':sg,'uv_bounds':[lo,-1.24,hi,1.44],'triangles_uv':tt})
(R/'derived/bellevue/south_service/countertops.json').write_text(json.dumps(out))
