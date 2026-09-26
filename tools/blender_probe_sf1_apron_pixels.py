"""Read-only ray/texture diagnosis of the dark strip in SF1 approach view."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


native_hash = sha(bpy.data.filepath)
assert native_hash == '90df6b61e3dc1beef7d0a33abf9365a98dcf7af35eafd06209ebd46bf30f74db'
scene = bpy.context.scene
assert scene['version'] == 'G1_027r11'
package = ROOT / 'parallel/stadelhofen_01'
spec = json.loads((package / 'derived/build_input.json').read_text())
inventory = json.loads((package / 'derived/native_context_inventory.json').read_text())
objects = list(bpy.data.collections[spec['import_collection']].objects)
objects += [bpy.data.objects[row['original_name']] for row in inventory['objects']
            if row['original_name'].startswith('CTX_')]
deps = bpy.context.evaluated_depsgraph_get()
verts, faces, meta = [], [], []
for obj in objects:
    if obj.type != 'MESH' or obj.hide_render:
        continue
    ev = obj.evaluated_get(deps)
    mesh = ev.to_mesh()
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        points = [ev.matrix_world @ mesh.vertices[i].co for i in tri.vertices]
        offset = len(verts)
        verts.extend(points)
        faces.append([offset, offset + 1, offset + 2])
        uv = [list(mesh.uv_layers.active.data[i].uv) for i in tri.loops] if mesh.uv_layers.active else None
        material = obj.material_slots[tri.material_index].material if tri.material_index < len(obj.material_slots) else None
        meta.append((obj.name, tri.polygon_index, points, uv, material.name if material else None))
    ev.to_mesh_clear()
tree = BVHTree.FromPolygons(verts, faces, all_triangles=True)
cam = bpy.data.objects['SF1_QA_APPROACH']
scene.render.resolution_x, scene.render.resolution_y = 1400, 960
scene.render.resolution_percentage = 100
frame = cam.data.view_frame(scene=scene)
xmin, xmax = min(v.x for v in frame), max(v.x for v in frame)
ymin, ymax = min(v.y for v in frame), max(v.y for v in frame)
A, U, N = [np.asarray(spec[k]) for k in ['A', 'U', 'N']]
pixels = [(90,738),(120,744),(150,754),(180,764),(210,773),(240,782),(270,791),
          (290,797),(320,801),(180,750),(180,785),(240,770),(240,800),(310,812)]
rows = []
for x, y in pixels:
    v = Vector((xmin + (x + .5) / 1400 * (xmax - xmin),
                ymax - (y + .5) / 960 * (ymax - ymin), frame[0].z))
    direction = (cam.matrix_world.to_3x3() @ v).normalized()
    pos, normal, index, distance = tree.ray_cast(cam.matrix_world.translation, direction, 100)
    row = dict(pixel=[x, y], hit=pos is not None)
    if pos is not None:
        name, poly, points, uv, matname = meta[index]
        xy = np.asarray(pos)[:2] - A
        row.update(object=name, polygon=poly, xyz=list(pos), normal=list(normal),
                   sf1_uvz=[float(xy @ U), float(xy @ N), float(pos.z)], material=matname)
        if uv and matname:
            p = np.asarray(points)
            w = np.linalg.lstsq((p[1:] - p[0]).T, np.asarray(pos) - p[0], rcond=None)[0]
            texuv = np.asarray(uv)[0] + w @ (np.asarray(uv)[1:] - np.asarray(uv)[0])
            row['texture_uv'] = texuv.tolist()
            mat = bpy.data.materials[matname]
            row['image_samples'] = []
            for node in mat.node_tree.nodes if mat.use_nodes else []:
                if node.type != 'TEX_IMAGE' or not node.image:
                    continue
                im = node.image
                width, height = im.size
                if not width or not height:
                    continue
                ix, iy = int((texuv[0] % 1) * width), int((texuv[1] % 1) * height)
                at = (iy * width + ix) * im.channels
                row['image_samples'].append(dict(image=im.name, path=im.filepath,
                    sample_pixel=[ix, iy], rgba=list(im.pixels[at:at + im.channels]),
                    interpolation=node.interpolation, coordinates_linked=bool(node.inputs['Vector'].links)))
    rows.append(row)
assert sha(bpy.data.filepath) == native_hash
out = dict(version=scene['version'], native_sha256=native_hash, process_id=os.getpid(),
           camera=cam.name, image_size=[1400, 960], region='left front apron exterior dark strip',
           ray_object_scope='SF1 authored geometry and the actual current 53-object local photo context',
           saved=False, rays=rows)
write_path('evidence/G1_027r11/apron_dark_strip_probe.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out), flush=True)
