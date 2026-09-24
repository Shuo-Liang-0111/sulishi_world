"""Pure geometry helpers for bounded, source-supported027r1 repair preparation.

XY is project-local metres. This uses NumPy/Shapely in the project environment,
not in Blender; final editable vertex patches are validated before application.
"""
import numpy as np
from shapely import STRtree, points, shortest_line, get_point, get_coordinates
from shapely.geometry import Polygon

class Surface:
    def __init__(self,triangles):
        self.t=np.asarray(triangles)
        self.poly=np.array([Polygon(t[:,:2]) for t in self.t],dtype=object)
        self.tree=STRtree(self.poly)
        n=np.cross(self.t[:,1]-self.t[:,0],self.t[:,2]-self.t[:,0])
        assert (n[:,2]>0).all()
        self.gradient=-n[:,:2]/n[:,2,None]

    def sample(self,xy):
        xy=np.atleast_2d(xy);p=points(xy);idx=self.tree.nearest(p)
        q=get_coordinates(get_point(shortest_line(self.poly[idx],p),0))
        z=self.t[idx,0,2]+((q-self.t[idx,0,:2])*self.gradient[idx]).sum(1)
        # Shared edges and tiny float32 bottom triangles can have several
        # projected intersections. A ground ray selects the highest one; an
        # arbitrary nearest polygon can instead pick the slab underside.
        pairs=self.tree.query(p,predicate='intersects')
        if pairs.shape[1]:
            at,face=pairs
            heights=self.t[face,0,2]+((xy[at]-self.t[face,0,:2])*self.gradient[face]).sum(1)
            highest=np.full(len(xy),-np.inf);np.maximum.at(highest,at,heights)
            z=np.where(np.isfinite(highest),highest,z)
        return z,np.linalg.norm(q-xy,axis=1)

def smoothstep(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

def weight(xy):
    x,y=np.atleast_2d(xy).T
    # Complete approach transition, fading before untouched station platforms,
    # north shore and southern upper promenade. Local coordinates in metres.
    return (smoothstep((x+297)/10)*smoothstep((-254-x)/11)*
            smoothstep((y-110)/9)*smoothstep((155-y)/10))

class Grade:
    def __init__(self,surfaces,coefficients):
        self.surfaces={k:Surface(surfaces[k]) for k in ['road','walk','bank']}
        self.coef=np.asarray(coefficients)

    def raw(self,xy):
        p=(np.atleast_2d(xy)-[-270,135])/20
        a=np.c_[np.ones(len(p)),p,p[:,0]**2,p[:,0]*p[:,1],p[:,1]**2]
        return a@self.coef-400

    def target(self,xy,kind):
        xy=np.atleast_2d(xy);z=self.raw(xy)
        bank,d=self.surfaces['bank'].sample(xy)
        tie=smoothstep(1-d/1.5)
        # Source photography constrains the grade; the 30mm dropped-edge and
        # 120mm raised-walk profile are inferred local construction details.
        z=z+(.12 if kind=='walk' else 0)
        z=z*(1-tie)+(bank-(.03 if kind=='road' else 0))*tie
        return z

    def delta(self,xy,kind):
        old,_=self.surfaces[kind].sample(xy)
        return weight(xy)*(self.target(xy,kind)-old)


class RefinedGrade(Grade):
    """Continuous extension of the retained bank at polygon nearest-edge ties.

Outside a triangulated bank, selecting just one nearest face creates Voronoi
height jumps. Blend nearest projected heights in a distance-scaled local band;
the band tends to zero at the bank boundary. Existing bank geometry is fixed.
    """
    def target(self,xy,kind):
        xy=np.atleast_2d(xy);bank=self.surfaces['bank']
        h,d=bank.sample(xy)
        active=np.flatnonzero((d>1e-6)&(d<1.5))
        if len(active):
            p=points(xy[active]);scale=np.minimum(.08,d[active]*.20)
            pairs=bank.tree.query(p,predicate='dwithin',distance=d[active]+12*scale)
            at,face=pairs
            q=get_coordinates(get_point(shortest_line(bank.poly[face],p[at]),0))
            dist=np.linalg.norm(q-xy[active[at]],axis=1)
            z=bank.t[face,0,2]+((q-bank.t[face,0,:2])*bank.gradient[face]).sum(1)
            w=np.exp(-(dist-d[active[at]])/scale[at])
            total=np.bincount(at,weights=w,minlength=len(active))
            h[active]=np.bincount(at,weights=w*z,minlength=len(active))/total
        tie=smoothstep(1-d/1.5)
        z=self.raw(xy)+(.12 if kind=='walk' else 0)
        return z*(1-tie)+(h-(.03 if kind=='road' else 0))*tie
