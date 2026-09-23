"""Bounded survey/photographic diagnosis for the northern Quaibruecke approach.

These records distinguish 2D boundaries, simplified official 3D surfaces and
observed photo geometry. Covered public water is never treated as exposed water.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from shapely.geometry import shape, Point
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parents[1]
D = R/'derived/bellevue/riviera_lower'
D.mkdir(exist_ok=True)
choices = {
    'av_bo_boflaeche_a.geojson': [145, 40750, 24105, 5939],
    'av_ei_flaechenelement_a.geojson': [20735, 28347, 47309, 39461, 18091],
    'av_ei_linienelement.geojson': list(range(2345, 2356))+[5675, 5676],
    'view_kuba_linien.geojson': [582],
    'view_kuba_flaechen.geojson': [477, 502, 552],
    'bauten_dachmodell_3d.geojson': [58782, 99963, 166432, 13249, 28507, 31458],
}
features = []
hashes = {}
for file, ids in choices.items():
    path = R/'sources/features'/file
    hashes[str(path.relative_to(R))] = hashlib.sha256(path.read_bytes()).hexdigest()
    found = [f for f in json.loads(path.read_text(encoding='utf-8'))['features']
             if f['properties']['objectid'] in ids]
    assert len(found) == len(ids), file
    features.extend(found)
lookup = {f['id']: f for f in features}
foot = shape(lookup['av_bo_boflaeche_a.40750']['geometry'])
stair = shape(lookup['av_ei_flaechenelement_a.47309']['geometry'])
wall = shape(lookup['av_ei_flaechenelement_a.20735']['geometry'])
tri = np.load(R/'derived/bellevue/riviera_quay/source_geometry.npz')['photo_triangles']
centres = tri.mean(axis=1)
normal = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
areas = np.linalg.norm(normal, axis=1)/2
core = foot.buffer(-.25).difference(stair.buffer(.18)).intersection(
    shape({'type':'Polygon','coordinates':[[[2683480,1246846],[2683505,1246846],
                                           [2683505,1246889],[2683480,1246889],[2683480,1246846]]]}))
sel = np.array([core.contains(Point(p)) for p in centres[:,:2]])
sel &= (abs(normal[:,2])>1.85*areas)&(areas>.2)&(centres[:,2]>406.5)&(centres[:,2]<406.78)
support = centres[sel]
assert len(support) >= 18
level = float(np.median(support[:,2]))
assert 406.62 < level < 406.72
report = {'lower_footprint_m2':foot.area, 'curved_wall_footprint_m2':wall.area,
          'side_stair_footprint_m2':stair.area, 'side_stair_riser_records':13,
          'photo_support_count':len(support), 'photo_floor_median_ln02_m':level,
          'photo_support_quantiles_ln02_m':np.quantile(support[:,2],[0,.1,.5,.9,1]).tolist(),
          'official_simplified_lower_roof_ln02_m':406.505,
          'official_simplified_bridge_bottom_ln02_m':407.57,
          'warning':'Uniform official extrusions are not detailed bridge soffit or surveyed floor profiles. Photo levels remain interpreted observations.',
          'covered_water_id':'av_ei_flaechenelement_a.28347',
          'covered_water_not_exposed_surface':True,
          'bridge_underpass_pending_separate_profile_review':True}
data = {'origin':[2683775.,1246700.,400.], 'features':features, 'source_sha256':hashes,
        'photo_floor_support':support.tolist(), 'report':report}
(D/'context.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

fig, axes = plt.subplots(1,2,figsize=(11,9),dpi=150)
for ax in axes:
    for ident,color in [('av_bo_boflaeche_a.40750','#46828c'),
                         ('av_bo_boflaeche_a.24105','#c4c1b5'),
                         ('av_ei_flaechenelement_a.20735','#865e45'),
                         ('av_ei_flaechenelement_a.18091','#865e45'),
                         ('av_ei_flaechenelement_a.47309','#d19542'),
                         ('av_ei_flaechenelement_a.39461','#9d82ab')]:
        g=shape(lookup[ident]['geometry'])
        ax.fill(*g.exterior.xy,facecolor=color,alpha=.32,edgecolor=color,lw=.8)
        pt=g.representative_point()
        ax.text(pt.x,pt.y,ident.split('.')[-1],fontsize=7,clip_on=True)
    for f in features:
        if f['id'].startswith('av_ei_linienelement.'):
            g=shape(f['geometry']);ax.plot(*g.xy,color='#764812',lw=.7)
    ax.scatter(support[:,0],support[:,1],c=support[:,2],vmin=406.6,vmax=406.8,s=8,cmap='viridis')
    ax.set_aspect('equal');ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=6)
    ax.grid(alpha=.15)
axes[0].set_xlim(2683475,2683510);axes[0].set_ylim(1246835,1246898)
axes[1].set_xlim(2683491,2683502);axes[1].set_ylim(1246852,1246865)
axes[0].set_title('Curved lower approach | source XY and photo floor support')
axes[1].set_title('Thirteen source riser lines | upper landing and wall')
fig.tight_layout();fig.savefig(D/'source_plan.png');plt.close(fig)
print(json.dumps(report,indent=2))
