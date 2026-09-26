"""Compare the complete proposed island with actual r10 road geometry.

This consumes a saved, read-only native probe. It cannot alter a road or make
the candidate platform ready merely by comparing it to an earlier recipe.
"""
import hashlib
import json
import numpy as np
from shapely.geometry import Polygon, shape
from workspace_paths import read_path, write_path
from prepare_bank_tram_platform import Road


def main():
    pp = read_path('derived/bellevue/bank_tram_shelter/native_probe_G1_027r10_platform_full.json')
    ip = read_path('derived/bellevue/bank_tram_shelter/platform_input.json')
    probe, prepared = [json.loads(p.read_text()) for p in (pp, ip)]
    cp = json.loads(read_path('evidence/G1_027r10/checkpoint.json').read_text())
    assert probe['native_sha256'] == cp['native_sha256']
    assert probe['probe_scope'] == 'full_platform_end_noses_and_roads'
    area = shape(prepared['geometry_local']).buffer(4)
    road_roles = {'road_asphalt', 'road_concrete', 'road_joint', 'asphalt_road', 'asphalt_track'}
    tt, used = [], []
    for ob in probe['objects']:
        if ob.get('surface_role') not in road_roles:
            continue
        assert not ob['modifiers'], ('Unevaluated road modifiers', ob['name'])
        vv = np.asarray(ob['vertices_world'])
        added = 0
        for face in ob['faces']:
            for i in range(1, len(face)-1):
                tri = vv[[face[0], face[i], face[i+1]]]
                n = np.cross(tri[1]-tri[0], tri[2]-tri[0])
                if n[2] < .92*np.linalg.norm(n) or n[2] < 1e-9:
                    continue
                if not Polygon(tri[:, :2]).intersects(area):
                    continue
                tt.append(tri)
                added += 1
        if added:
            used.append(dict(name=ob['name'], surface_role=ob['surface_role'],
                             actual_mesh_digest=ob['mesh_digest'], selected_triangles=added))
    assert tt
    road = Road(tt)
    recipe_path = read_path('derived/bellevue/transport/road_input.json')
    recipe = json.loads(recipe_path.read_text())
    old_road = Road([t for p in recipe['pieces'] if p['kind']=='road_asphalt' for t in p['triangles']])
    rows = []
    for old in prepared['report']['perimeter_road_comparison']:
        z, distance = road.sample(old['xy'])
        recipe_z, _ = old_road.sample(old['xy'])
        assert distance < .012, ('Actual edge has no near road', old['xy'], distance)
        rows.append(dict(**old, current_road_z=z, current_nearest_road_distance_m=distance,
                         current_minus_recipe_road_m=z-recipe_z,
                         prepared_minus_current_road_m=old['platform_z']-z))
    error = np.array([r['current_minus_recipe_road_m'] for r in rows])
    delta = np.array([r['prepared_minus_current_road_m'] for r in rows])
    result = dict(version=probe['version'], native_sha256=probe['native_sha256'],
                  probe_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),
                  prepared_sha256=hashlib.sha256(ip.read_bytes()).hexdigest(),
                  current_road_objects=used, current_road_triangles=np.asarray(tt).tolist(),
                  boundary=rows,
                  current_minus_recipe_max_m=float(abs(error).max()),
                  current_upstand_quantiles_m=np.quantile(delta, [0,.1,.5,.9,1]).tolist(),
                  negative_upstands=int((delta<-.002).sum()),
                  native_changed=False, ready_for_native_build=False,
                  limits=['Native agreement validates the chosen old-road reference, not a survey measurement.',
                          'Resolve inferred floor shape and adjoining grade before any photographic replacement.'])
    # Stable native-road support is independent of any candidate floor model.
    # Keep it separate from this comparison to avoid circular preparation
    # fingerprints when a new platform candidate is assessed.
    support = {k:result[k] for k in ['version','native_sha256','probe_sha256',
               'current_road_objects','current_road_triangles','current_minus_recipe_max_m','native_changed']}
    support['legacy_road_recipe_sha256'] = hashlib.sha256(recipe_path.read_bytes()).hexdigest()
    write_path('derived/bellevue/bank_tram_shelter/current_road_support.json').write_text(
        json.dumps(support, separators=(',', ':')), encoding='utf-8')
    path = write_path('derived/bellevue/bank_tram_shelter/current_road_diagnosis.json')
    path.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ['current_road_triangles','current_road_objects','boundary']}, indent=2))
    print('CURRENT_ROAD_OBJECTS',len(used),'TRIANGLES',len(tt))


if __name__ == '__main__':
    main()
