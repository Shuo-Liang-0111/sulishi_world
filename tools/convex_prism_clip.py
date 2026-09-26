"""Pure numeric, attribute-preserving subtraction of convex vertical prisms."""
import numpy as np


def polygon_area(poly):
    if len(poly) < 3: return 0.
    p = np.asarray(poly)[:, :3]
    return sum(np.linalg.norm(np.cross(p[i]-p[0], p[i+1]-p[0]))/2 for i in range(1, len(p)-1))


def prism(xy, zmin, zmax, role):
    p = np.asarray(xy, dtype=float)
    assert len(p) >= 3 and zmin < zmax
    twice_area = sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(p, np.roll(p, -1, axis=0)))
    if twice_area < 0: p = p[::-1]
    planes = [[0., 0., 1., -zmin], [0., 0., -1., zmax]]
    for a, b in zip(p, np.roll(p, -1, axis=0)):
        edge = b-a; n = np.array([-edge[1], edge[0]]) / np.linalg.norm(edge)
        planes.append([*n, 0., -float(n @ a)])
    return dict(planes=np.asarray(planes), bmin=np.r_[p.min(0), zmin],
                bmax=np.r_[p.max(0), zmax], role=role)


def split(poly, plane):
    inside, outside = [], []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        da, db = np.dot(a[:3], plane[:3])+plane[3], np.dot(b[:3], plane[:3])+plane[3]
        ia, ib = da >= -1e-10, db >= -1e-10
        (inside if ia else outside).append(a)
        if ia != ib:
            p = a+(b-a)*da/(da-db)
            inside.append(p); outside.append(p)
    return inside, outside


def subtract(poly, volume):
    outside = []; current = poly
    for plane in volume['planes']:
        if len(current) < 3: break
        current, part = split(current, plane)
        if len(part) >= 3 and polygon_area(part) > 1e-10: outside.append(part)
    return outside


def subtract_many(triangle, volumes):
    """Return unchanged flag and kept triangles as original barycentric weights."""
    triangle = np.asarray(triangle)
    initial = [np.r_[v, w] for v, w in zip(triangle, np.eye(3))]
    parts = [initial]
    lo, hi = triangle.min(0), triangle.max(0)
    n = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
    norm = np.linalg.norm(n)
    if norm < 1e-12: return True, [], 0.
    for volume in volumes:
        if np.any(hi < volume['bmin']-1e-9) or np.any(lo > volume['bmax']+1e-9): continue
        if volume['role'] == 'ground_only' and abs(n[2])/norm < .965: continue
        next_parts = []
        for part in parts:
            a = np.asarray(part)[:, :3]
            if np.any(a.max(0) < volume['bmin']-1e-9) or np.any(a.min(0) > volume['bmax']+1e-9):
                next_parts.append(part); continue
            next_parts.extend(subtract(part, volume))
        parts = next_parts
        if not parts: break
    original = norm/2; remaining = sum(polygon_area(p) for p in parts)
    assert -1e-9 <= remaining <= original+1e-7, (original, remaining)
    if abs(original-remaining) < 1e-8: return True, [], 0.
    weights = []
    for part in parts:
        for i in range(1, len(part)-1):
            tri = np.array([part[0], part[i], part[i+1]])
            if polygon_area(tri) < 1e-10: continue
            w = tri[:, 3:]
            assert np.min(w) >= -1e-7 and np.max(abs(w.sum(1)-1)) < 1e-7
            assert np.max(abs(w @ triangle - tri[:, :3])) < 1e-7
            weights.append(w.tolist())
    return False, weights, original-remaining
