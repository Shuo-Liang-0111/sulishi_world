"""Record the first contiguous study area and visualize it against public surveys."""
from pathlib import Path
import json
from collections import Counter
import numpy as np
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'planning'
OUT.mkdir(exist_ok=True)
ORIGIN = [2683775, 1246700, 400]
BBOX = [2683420, 1246300, 2684200, 1247110]
# Follow the complete station and its public approaches, the plaza, opera and shore.
# This acquisition-independent boundary is a construction scope, not a legal boundary.
seed = Polygon([[2683470,1246940],[2683560,1247040],[2683780,1247040],
                [2684080,1246800],[2684140,1246620],[2683910,1246420],
                [2683650,1246420],[2683470,1246710]])
survey = json.loads((ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())
buildings = [f for f in survey['features'] if f['properties']['art_txt'].startswith('Gebaeude.')]
# Do not bisect real buildings along the nominal scope boundary.
selected = [f for f in buildings if seed.intersection(shape(f['geometry'])).area > 0.1]
boundary = unary_union([seed]+[shape(f['geometry']) for f in selected]).buffer(0)
data = {'type':'FeatureCollection','name':'G1_construction_scope',
        'crs':{'type':'name','properties':{'name':'EPSG:2056'}},
        'features':[{'type':'Feature','properties':{'id':'G1','role':'construction_scope',
            'status':'active_not_accepted','area_m2':boundary.area,
            'origin_lv95_ln02':ORIGIN,'geometry_basis':'project selection; whole intersected official building footprints'},
            'geometry':mapping(boundary)}]}
(OUT/'g1_scope.geojson').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
in_scope = lambda f: boundary.intersects(shape(f['geometry']))
counts={}
for file in ['av_bo_boflaeche_a','av_ei_flaechenelement_a','av_ei_linienelement',
             'av_geb_gebaeudeadresse_t','tbl_routennetz','bauminventar','wvz_brunnen']:
    fs=json.loads((ROOT/f'sources/features/{file}.geojson').read_text())['features']
    counts[file]=sum(in_scope(f) for f in fs)
spec={'schema_version':1,'id':'Zurich_G1','origin':ORIGIN,'horizontal_crs':'EPSG:2056',
      'vertical_crs':'EPSG:5728','native_axes':'X east, Y north, Z up; metres',
      'scope':'planning/g1_scope.geojson','scope_area_m2':boundary.area,
      'scope_bounds':list(boundary.bounds),'source_context_bbox':BBOX,
      'building_footprints':len(selected),'source_feature_counts':counts,
      'epoch':{'label':'Evidence-fused ordinary non-event built state',
               'review_date':'2026-09-21','photomesh':'2025 acquisition',
               'cadastral':'year-end 2025','station_plan':'2025-12',
               'swissimage':'acquisition date unresolved',
               'limitation':'Not a literal synchronized 2026-09-21 snapshot. Event tents are not permanent structures.'},
      'quality_status':'survey_and_reference_stage_not_accepted',
      'natural_open_places':['continuous outdoor public space','Stadelhofen public station concourse and stairs',
                             'one documented Bellevue pavilion public interior'],
      'natural_facilities':['existing drinking fountain 1285','documented seating','doors of selected public interior'],
      'excluded_this_goal':['research tasks','task props','scoring','embodied agent','complete transport operations'],
      'closed_interiors':'unselected interiors remain closed; never represented as usable',
      'scope_note':'Selection grew to preserve complete surveyed building footprints. Context data outside boundary is background only.'}
(OUT/'scene_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
fig,ax=plt.subplots(figsize=(12,12),dpi=170)
ax.imshow(Image.open(ROOT/'sources/references/swissimage-context.jpg'),
          extent=[BBOX[0]-ORIGIN[0],BBOX[2]-ORIGIN[0],BBOX[1]-ORIGIN[1],BBOX[3]-ORIGIN[1]])
for f in selected:
    g=shape(f['geometry']);x,y=g.exterior.xy
    ax.plot(np.array(x)-ORIGIN[0],np.array(y)-ORIGIN[1],color='#ffdf88',lw=.45,alpha=.65)
x,y=boundary.exterior.xy
ax.plot(np.array(x)-ORIGIN[0],np.array(y)-ORIGIN[1],color='#70f0ff',lw=2.2,label='G1 boundary (whole buildings retained)')
for label,x,y in [('Bellevue',2683550,1246835),('Sechselautenplatz',2683640,1246700),
                   ('Opernhaus',2683740,1246600),('Stadelhofen',2683860,1246800),
                   ('Public underpass / platforms',2683980,1246680),
                   ('Fountain 1285',2683631.684,1246676.128)]:
    ax.plot(x-ORIGIN[0],y-ORIGIN[1],'o',color='white',ms=3)
    ax.annotate(label,(x-ORIGIN[0],y-ORIGIN[1]),xytext=(5,6),textcoords='offset points',fontsize=8,
                color='white',bbox=dict(facecolor='#16242e',alpha=.8,edgecolor='none',pad=2))
ax.set_title('Zurich G1 | source-constrained construction boundary',loc='left')
ax.set_xlabel('East of local origin (m)');ax.set_ylabel('North of local origin (m)')
ax.grid(alpha=.2);ax.legend(loc='upper left',fontsize=8)
fig.text(.08,.02,'Base image: swisstopo SWISSIMAGE WMS | survey: Stadt Zurich, year-end 2025\nBoundary is project planning; image acquisition date unresolved. No completion claim.',fontsize=8)
fig.tight_layout(rect=[0,.045,1,1]);fig.savefig(OUT/'G1_scope_map.png');plt.close(fig)
print(json.dumps({'area_m2':round(boundary.area),'bounds':list(boundary.bounds),
                  'building_footprints':len(selected),'source_counts':counts},ensure_ascii=False))
