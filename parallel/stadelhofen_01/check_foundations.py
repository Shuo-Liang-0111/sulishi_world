"""Actual plinth underside versus the independently tessellated ground bed."""
from sf1_common import *

def check(C,build_bvh):
    bed=build_bvh([o for o in C.objects if o.name=='SF1_APRON_CONTINUOUS_SUBBASE'])
    rows=[]
    def inside(pt,poly):
        x,y=pt;yes=False
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:yes=not yes
        return yes
    for i,poly in enumerate(D['wall_outlines']):
        body=build_bvh([bpy.data.objects['SF1_CHEEK_%d_MASONRY'%i]])
        q=np.array(poly);lo=q.min(axis=0)+.01;hi=q.max(axis=0)-.01
        for u in np.linspace(lo[0],hi[0],int(math.ceil((hi[0]-lo[0])/.1))+1):
            for v in np.linspace(lo[1],hi[1],int(math.ceil((hi[1]-lo[1])/.1))+1):
                if not inside([u,v],poly):continue
                g,_,_,_=bed.ray_cast(Vector(P(u,v,12.)),Vector((0,0,-1)),3.)
                b,_,_,_=body.ray_cast(Vector(P(u,v,9.7)),Vector((0,0,1)),2.)
                gap=float(b.z-g.z) if g is not None and b is not None else None
                rows.append(dict(plinth=i,uv=[float(u),float(v)],body_bottom_z=float(b.z) if b is not None else None,bed_top_z=float(g.z) if g is not None else None,gap_m=gap,passed=gap is not None and gap<=.004))
    return dict(samples=rows,maximum_gap_m=max(r['gap_m'] for r in rows if r['gap_m'] is not None),missing=sum(r['gap_m'] is None for r in rows),passed=all(r['passed'] for r in rows),scope='Actual evaluated stone underside must reach the separate continuous ground bed. Buried foundation depth is inferred, not surveyed.')
