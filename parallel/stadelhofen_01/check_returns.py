"""Rays cross the observed v03 depth gap between wing and pilaster."""
from sf1_common import *

def check(C,build_bvh):
    tree=build_bvh([o for o in C.objects if o.get('sf1_role')=='facade'])
    rows=[]
    for side in [-1,1]:
        for z in np.linspace(11.43,15.72,21):
            a=P(-1.70 if side<0 else W+1.70,-.585,float(z));direction=Vector((*list(U*(-side)),0))
            h,n,idx,dist=tree.ray_cast(Vector(a),direction,1.70)
            rows.append(dict(side=side,z=float(z),hit=list(h) if h is not None else None,hit_local_uvz=list(Q(h)) if h is not None else None,blocked_gap=h is not None))
    return dict(samples=rows,passed=all(r['blocked_gap'] for r in rows),scope='42 sideways rays across the former 145mm depth gap; also visually inspect approach view. Not a complete facade weatherproofing certification.')
