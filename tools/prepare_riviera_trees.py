"""Nine inventory Sophora trees and real openings in the saved AV145 pavement.

Positions/species/heights are source data. Pits, girths, crown form and soil
detail are explicitly inferred. Existing shared sidewalk and steps stay fixed.
"""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import Point, shape, mapping
from shapely.affinity import affine_transform
from shapely.ops import unary_union

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/riviera_quay'
plan=json.loads((D/'build_input.json').read_text())
# Reuse the actual021 grade and slab author, without its construction/output loop.
source=R/'tools/prepare_riviera_quay_build.py'
prefix=source.read_text().split('# Public paving is subdivided')[0]
ns={'__file__':str(source)};exec(compile(prefix,str(source),'exec'),ns)
O=np.array(plan['origin']);A=np.array(plan['anchor']);T=np.array(plan['along']);N=np.array(plan['across'])
grade=ns['grade'];foot=shape(plan['source_plan_lv95'])
inventory_path=R/'sources/features/bauminventar.geojson'
inventory=json.loads(inventory_path.read_text())['features']
trees=[f for f in inventory if foot.covers(shape(f['geometry']))]
assert len(trees)==9 and all('Sophora' in f['properties']['baumart_lat'] for f in trees)
forms={23522:(.24,[2.6,2.4],2.65),37402:(.34,[2.9,2.5],2.7),62437:(.36,[3.2,2.7],2.8),
       79383:(.42,[3.8,3.3],3.0),84969:(.28,[3.1,2.8],2.7),88495:(.37,[3.5,3.2],2.9),
       101985:(.25,[2.7,2.35],2.6),106877:(.53,[4.7,4.1],3.2),114015:(.38,[3.4,3.0],2.9)}
walk=unary_union([shape(p['plan_sd']) for p in plan['parts'] if p['role']=='asphalt'])
pits=[]
for f in sorted(trees,key=lambda f:f['properties']['objectid']):
    ident=f['properties']['objectid'];point=np.array(f['geometry']['coordinates']);delta=point-A
    sd=np.array([delta@T,delta@N]);diam,radii,clearance=forms[ident]
    radius=.72+diam*.28
    pit=Point(sd).buffer(radius,quad_segs=32).intersection(walk.buffer(-.15))
    assert pit.geom_type=='Polygon' and pit.covers(Point(sd))
    centre_height=grade(*sd)
    pits.append({'source':f,'xy_local':(point-O[:2]).tolist(),'sd':sd.tolist(),
      'origin':O.tolist(),'height_m':f['properties']['hoehe'],'ground_ln02_m':centre_height-.028,
      'geometry_sd':mapping(pit),'radius_m_inferred':radius,
      'inferred':{'seed':ident,'trunk_diameter_m':diam,'crown_radius_m':radii,'branch_clearance_m':clearance},
      'basis':'Inventory2022 XY/species/height; individual crown, girth, roots, open soil dimensions and wear inferred. AV145 and021 pavement height retained.'})
holes=unary_union([shape(p['geometry_sd']) for p in pits]);replacements=[]
for part in plan['parts']:
    if part['role']!='asphalt':continue
    g=shape(part['plan_sd']);remainder=g.difference(holes)
    if g.area-remainder.area<1e-9:continue
    ns['parts']=[]
    ns['add_slab'](part['name'],remainder,grade,lambda s,d:grade(s,d)-.18,'asphalt',part['source'])
    pieces=ns['parts'];assert len(pieces)==1 and pieces[0]['name']==part['name']
    replacements.append(dict(pieces[0],original_area_m2=part['area_m2']))
removed=sum(p['original_area_m2']-p['area_m2'] for p in replacements)
assert abs(removed-holes.area)<1e-7

# Soil relief uses the already reviewed CC0 scan. Its boundary and the trunk
# collar are fixed; millimetre relief cannot separate roots from the ground.
height_path=R/'sources/textures/polyhaven/forest_ground_05/textures/forest_ground_05_disp_4k.png'
height=gaussian_filter(np.asarray(Image.open(height_path),dtype=np.float32)/65535,sigma=12,mode='wrap')
median=float(np.median(height));h,w=height.shape
for entry in pits:
    ident=entry['source']['properties']['objectid'];rng=np.random.default_rng(ident)
    center=np.array(entry['sd']);poly=shape(entry['geometry_sd']);boundary=np.array(poly.exterior.coords)[:-1]
    vertices=[center];faces=[];ring_count=12;n=len(boundary)
    for j in range(1,ring_count+1):vertices.extend(center+(boundary-center)*j/ring_count)
    for k in range(n):faces.append([0,1+k,1+(k+1)%n])
    for j in range(1,ring_count):
        a=1+(j-1)*n;b=1+j*n
        for k in range(n):faces.extend([[a+k,b+k,b+(k+1)%n],[a+k,b+(k+1)%n,a+(k+1)%n]])
    sd=np.asarray(vertices);xy=A+sd[:,0,None]*T+sd[:,1,None]*N-O[:2]
    angle=rng.uniform(0,2*np.pi);rot=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    uv=(xy-entry['xy_local'])@rot.T/2+rng.uniform(0,1,2)
    q=uv%1;sample=map_coordinates(height,[(1-q[:,1])*h-.5,q[:,0]*w-.5],order=1,mode='grid-wrap')
    edge=np.array([poly.boundary.distance(Point(q)) for q in sd]);rad=np.linalg.norm(sd-center,axis=1)
    fade=np.clip(edge/.08,0,1)*np.clip((rad-entry['inferred']['trunk_diameter_m']*.6)/.12,0,1)
    relief=np.clip((sample-median)*.02,-.005,.005)*fade
    z=np.array([grade(*q)-400-.028 for q in sd])+relief
    v=np.c_[xy,z];ff=np.array(faces);cross=np.cross(v[ff[:,1]]-v[ff[:,0]],v[ff[:,2]]-v[ff[:,0]])[:,2]
    ff[cross<0]=ff[cross<0][:,::-1]
    area=float(abs(cross).sum()/2);assert abs(area-poly.area)<1e-7
    entry['soil_mesh']={'vertices':v.tolist(),'faces':ff.tolist(),'uv':uv.tolist(),'area_m2':area}
    entry['texture_rotation_rad']=angle
report={'version':'G1_021r1','base':'G1_021','inventory_trees':9,'pits':len(pits),'soil_area_m2':holes.area,
        'changed_paving_objects':len(replacements),'paving_area_before_m2':walk.area,'paving_area_after_m2':walk.area-holes.area,
        'coverage_gap_m2':abs(removed-holes.area),'inventory_sha256':hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        'grade_code_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'trees':pits,'paving_replacements':replacements,
        'survey_tree_identity_preserved':True,'individual_shape_and_pit_size_inferred':True}
(D/'tree_build_input.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['trees','paving_replacements']},indent=2))
