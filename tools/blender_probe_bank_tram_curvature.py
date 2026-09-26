"""Read saved r13 canopy topology/normals before changing a visible finish defect."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import write_path
from blender_geometry_fingerprint import mesh_digest

native = Path(bpy.data.filepath)
assert bpy.context.scene['version'] == 'G1_027r13'
digest = hashlib.sha256(native.read_bytes()).hexdigest()
assert digest == 'bb05ad245a399bde56939d9a6e18cddc5a8092aa36f1e4badda11452dbb7b8bb'
before = native.stat()
target = write_path('derived/bellevue/bank_tram_shelter/curvature_probe_r13.json')
assert not target.exists()
rows = []
for name in ['BST_CANOPY_SOFFIT', 'BST_CANOPY_ROOF_METAL', 'BST_CANOPY_FASCIA']:
    ob = bpy.data.objects[name]
    me = ob.data
    me.calc_loop_triangles()
    normals = np.array([p.normal for p in me.polygons])
    edge_faces = {}
    for p in me.polygons:
        for a, b in zip(p.vertices, list(p.vertices)[1:] + list(p.vertices)[:1]):
            edge_faces.setdefault(tuple(sorted((a, b))), []).append(p.index)
    angles = [float(np.degrees(np.arccos(np.clip(normals[a] @ normals[b], -1, 1))))
              for adjacent in edge_faces.values() if len(adjacent) == 2
              for a, b in [adjacent]]
    rows.append(dict(
        object=name, digest=mesh_digest(me), matrix_world=[list(r) for r in ob.matrix_world],
        vertices=[list(v.co) for v in me.vertices], faces=[list(p.vertices) for p in me.polygons],
        corner_normals=[list(n.vector) for n in me.corner_normals],
        smooth_faces=sum(p.use_smooth for p in me.polygons), has_custom_normals=me.has_custom_normals,
        sharp_edges=sum(e.use_edge_sharp for e in me.edges),
        boundary_edges=sum(len(v) == 1 for v in edge_faces.values()),
        nonmanifold_edges=sum(len(v) > 2 for v in edge_faces.values()),
        face_turn_quantiles_deg=(np.percentile(angles, [25, 50, 90, 99, 100]).tolist()
                                 if angles else []),
        modifiers=[dict(name=m.name, type=m.type) for m in ob.modifiers],
        shadow_terminator_settings={p.identifier: getattr(ob.cycles, p.identifier)
                                    for p in ob.cycles.bl_rna.properties
                                    if p.identifier.startswith('shadow_terminator')}))
out = dict(version='G1_027r13', native_sha256=digest, process_id=os.getpid(),
           objects=rows, native_changed=False,
           diagnosis_status='Measurements only; distinguish coarse curvature from normal flags before repair.')
target.write_text(json.dumps(out, indent=2), encoding='utf-8')
assert native.stat().st_size == before.st_size and native.stat().st_mtime_ns == before.st_mtime_ns
print('BANK_CURVATURE_PROBE', json.dumps({r['object']: {k: r[k] for k in
      ['smooth_faces', 'sharp_edges', 'boundary_edges', 'nonmanifold_edges', 'face_turn_quantiles_deg']}
      for r in rows}), flush=True)
