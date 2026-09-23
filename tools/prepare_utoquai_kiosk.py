"""Extract cached Utoquai2f survey constraints; no new scene geometry or web IO."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'derived/bellevue/utoquai_kiosk'
OUT.mkdir(parents=True, exist_ok=True)
ORIGIN = np.array([2683775., 1246700., 400.])


def features(name):
    path = ROOT / 'sources/features' / (name + '.geojson')
    return json.loads(path.read_text(encoding='utf-8'))['features']


def main():
    foot = next(f for f in features('av_bo_boflaeche_a') if f['id'] == 'av_bo_boflaeche_a.20161')
    assert foot['properties']['gwr_egid'] == 302020548
    addr = next(f for f in features('av_geb_gebaeudeadresse_t') if f['id'] == 'av_geb_gebaeudeadresse_t.39399')
    parts = [f for f in features('bauten_dachmodell_3d') if f['properties']['egid'] == 302020548]
    assert {f['properties']['type'] for f in parts} == {'RoofSurface', 'GroundSurface', 'WallSurface'}
    roof = next(f for f in parts if f['properties']['type'] == 'RoofSurface')
    roof_z = np.array(roof['geometry']['coordinates'][0][0])[:, 2]
    assert np.ptp(roof_z) < .0001
    polygon = orient(shape(foot['geometry']), sign=1.)
    ring = np.array(polygon.exterior.coords)[:-1]
    centre = np.array(polygon.centroid.coords[0])
    ground = json.loads((ROOT / 'derived/bellevue/limmat_sidewalk/ground_input.json').read_text(encoding='utf-8'))
    grid = ground['grade_grid']
    grade = RegularGridInterpolator((grid['x'], grid['y']), grid['z'], bounds_error=True)
    ground_z = grade(ring - ORIGIN[:2]) + ORIGIN[2]
    edges = []
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        tangent = (b - a) / np.linalg.norm(b - a)
        edges.append({'index': i, 'a_lv95': a.tolist(), 'b_lv95': b.tolist(), 'length_m': float(np.linalg.norm(b - a)), 'outward_xy': [float(tangent[1]), float(-tangent[0])], 'adjacent_surface_ln02_m': [float(ground_z[i]), float(ground_z[(i + 1) % len(ring)])]})
    rec = {'egid': 302020548, 'address': 'Utoquai2f', 'operator_reference_identity': 'Imbiss Riviera', 'origin': ORIGIN.tolist(), 'centre_lv95': centre.tolist(), 'footprint': foot, 'footprint_ccw_lv95': mapping(polygon), 'area_m2': float(polygon.area), 'address_point': addr, 'source_parts': parts, 'roof_ln02_m': float(roof_z[0]), 'perimeter_grade_ln02_m': ground_z.tolist(), 'roof_above_adjacent_ground_m': (roof_z[0] - ground_z).tolist(), 'edges': edges, 'basis': 'Existing AV93 octagonal footprint17.601514m2, EGID/address and official flat roof411.255m LN02. GroundSurface405.322m is the model extrusion bottom, NOT the public entrance floor. Perimeter grade comes from the already authored AV24105 surface and spans about19cm. Resolve plinth and staff threshold against that grade. Counter/hatch proportions, exact material, unseen faces and interior are inferred from limited dated exterior reference.', 'opening_layout_accepted': False, 'interior_floor_selected': False, 'native_authored': False, 'external_requests': 0, 'next': 'Build the eight-sided shell to source roof/footprint, then align metal posts, pale panels, serving hatches, ledges and a minimal coherent counter interior. Keep staff access distinct from public service approach. Inspect both street and river faces before bounded removal of source working mesh; original I3S preserved.'}
    (OUT / 'source_input.json').write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding='utf-8')
    reference = ROOT / 'sources/references/utoquai_2f/kiosk_exterior_reference.jpg'
    assert reference.is_file()
    (reference.parent / 'exterior_receipt.json').write_text(json.dumps({'image': reference.name, 'image_url': 'https://production-livingdocs-bluewin-ch.imgix.net/2025/03/21/4515accf-56a2-4699-801e-ff1e4e32624d.png?auto=format&w=994', 'article_url': 'https://www.bluewin.ch/de/news/schweiz/wir-kaempfen-bis-zum-schluss-stadt-zuerich-will-den-riviera-imbiss-am-seebecken-nach-42-jahren-weghaben-2616008.html', 'image_capture_date': None, 'dated_article': '2025-03-21', 'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sha256': hashlib.sha256(reference.read_bytes()).hexdigest(), 'rights': 'Publisher photograph, reference study only. Not a material, generated texture, or distributable asset.', 'actually_viewed': True, 'observed': 'Pale sheet panels; narrow aluminium posts; dark flat roof trim with edge streaks; outward raised metal service hatches; stainless ledges, serving counter and visible warm pale interior. Tight crop does not prove all sides, openings, threshold or complete plan.', 'not_claimed': 'No present-day operating/permit claim; photo is not a surveyed as-built drawing.'}, indent=2), encoding='utf-8')
    print(json.dumps({'area_m2': rec['area_m2'], 'sides': len(edges), 'roof_ln02_m': rec['roof_ln02_m'], 'perimeter_grade_range': [float(ground_z.min()), float(ground_z.max())], 'native_authored': False}))


if __name__ == '__main__':
    main()
