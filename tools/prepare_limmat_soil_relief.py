"""Prepare bounded, editable soil relief from the saved G1_019r2 native mesh.

The scanned CC0 material is a generic proxy, not a survey of Zurich soil. The
existing ground XY, pit outlines and root collars are preserved. Run with the
project Python; Blender authoring is a separate guarded step.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
import shapely
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "derived/bellevue/limmat_sidewalk"
SOURCE = DATA / "soil_native_019r2.json"
TEXTURE = ROOT / "sources/textures/polyhaven/forest_ground_05/textures/forest_ground_05_disp_4k.png"


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    plan = json.loads((DATA / "ground_input.json").read_text(encoding="utf-8"))
    assert np.array_equal(source["matrix_world"], np.eye(4))
    old_vertices = np.asarray(source["vertices"], dtype=np.float64)
    old_faces = np.asarray(source["faces"], dtype=np.int32)
    triangles = old_vertices[old_faces]
    original_area = np.abs(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])[:, 2]).sum() / 2
    # Split every triangle equally so that a shared edge receives identical
    # samples on both sides. Welding is only a sub-micron positional operation.
    for _ in range(3):
        a, b, c = np.moveaxis(triangles, 1, 0)
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        triangles = np.concatenate([np.stack(q, axis=1) for q in [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]])
    vertices, inverse = np.unique(np.round(triangles.reshape(-1, 3), 7), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3).astype(np.int32)
    base_z = vertices[:, 2].copy()
    uv = np.empty((len(vertices), 2), dtype=np.float64)
    owners = np.full(len(vertices), -1, dtype=np.int16)
    fade = np.zeros(len(vertices), dtype=np.float64)
    points = shapely.points(vertices[:, :2])
    reports = []
    for i, pit in enumerate(plan["pits"]):
        # Native meshes contain float32 source positions: allow <0.1mm drift at
        # their existing outline, without changing or expanding that outline.
        geom = shape(pit["geometry_local"])
        mask = shapely.covers(geom.buffer(0.0001), points)
        assert not np.any(owners[mask] >= 0), "Pit UV islands must not overlap"
        assert mask.any()
        owners[mask] = i
        rng = np.random.default_rng(pit["source"]["properties"]["objectid"])
        angle = float(rng.uniform(0, 2 * np.pi))
        rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        offset = rng.uniform(0, 1, 2)
        relative = vertices[mask, :2] - pit["xy_local"]
        uv[mask] = relative @ rot.T / 2.0 + offset
        edge_distance = shapely.distance(points[mask], geom.boundary)
        radial_distance = np.linalg.norm(relative, axis=1)
        radius = pit["inferred"]["trunk_diameter_m"] / 2
        fade[mask] = smoothstep((edge_distance - 0.00015) / 0.08) * smoothstep((radial_distance - radius * 1.08) / 0.12)
        reports.append({"source_id": pit["source"]["id"], "texture_rotation_radians": angle, "uv_offset": offset.tolist(), "physical_tile_m": 2.0, "vertex_count": int(mask.sum())})
    assert np.all(owners >= 0), "Soil vertex outside all original pits"
    assert np.all(owners[faces] == owners[faces[:, :1]]), "Face bridges different pits"
    height = np.asarray(Image.open(TEXTURE), dtype=np.float32) / 65535
    # Suppress only sub-centimetre height noise in the geometric samples. Full
    # original scan normal/albedo/roughness images remain untouched in Blender.
    height = gaussian_filter(height, sigma=12, mode="wrap")
    q = uv % 1
    h, w = height.shape
    sample = map_coordinates(height, [(1 - q[:, 1]) * h - 0.5, q[:, 0] * w - 0.5], order=1, mode="grid-wrap")
    relief = np.clip((sample - np.median(height)) * 0.020, -0.006, 0.006) * fade
    vertices[:, 2] += relief
    assert np.max(np.abs(relief)) <= 0.00600001
    t = vertices[faces]
    area = np.abs(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])[:, 2]).sum() / 2
    assert abs(area - original_area) < 0.0001
    edge = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique_edges, counts = np.unique(edge, axis=0, return_counts=True)
    assert counts.max() <= 2, "Non-manifold soil edge"
    edge_points = shapely.points(vertices[np.unique(unique_edges[counts == 1]), :2])
    union = shapely.union_all([shape(p["geometry_local"]) for p in plan["pits"]])
    boundary_error = shapely.distance(edge_points, union.boundary)
    # Any inherited triangulation cracks are reported, never silently accepted.
    max_boundary_error = float(boundary_error.max())
    assert max_boundary_error < 0.0001, ("Unexpected interior open edge", max_boundary_error)
    np.savez_compressed(DATA / "soil_relief_019r3.npz", vertices=vertices.astype(np.float32), faces=faces, uv=uv.astype(np.float32), base_z=base_z, fade=fade, pit_index=owners)
    report = {"base_version": "G1_019r2", "target_version": "G1_019r3", "object": "LM_SOIL", "source_mesh_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "height_map_sha256": hashlib.sha256(TEXTURE.read_bytes()).hexdigest(), "source_url": "https://polyhaven.com/a/forest_ground_05", "license": "CC0", "geometric_relief_inferred": True, "unchanged_xy_area_m2": float(area), "source_xy_area_m2": float(original_area), "vertices": len(vertices), "triangles": len(faces), "relief_quantiles_m": np.quantile(relief, [0, .1, .5, .9, 1]).tolist(), "outline_max_deviation_m": max_boundary_error, "edge_fade_m": .08, "root_collar_fade_m": .12, "pit_uvs": reports, "basis": "Generic 2m ground scan, rotated per pit at physical scale; bounded +/-6mm inferred relief tapers to the unchanged pit perimeter and existing root collar. No source location, road grade or tree geometry changed.", "visual_acceptance": False}
    (DATA / "soil_relief_019r3.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["vertices", "triangles", "unchanged_xy_area_m2", "relief_quantiles_m", "outline_max_deviation_m"]}))


if __name__ == "__main__":
    main()
