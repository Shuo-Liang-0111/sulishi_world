"""Source-located fixture replacement; unidentified model details remain inferred."""
from pathlib import Path
import json,hashlib,runpy,math,numpy as np
from shapely.geometry import shape,Point,Polygon,mapping
from shapely.ops import unary_union
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];cfg=globals().get('FIXTURE_CONFIG',{});D=R/cfg.get('out_dir','derived/bellevue/corner_fixtures');D.mkdir(exist_ok=True);V=R/'sources/features/vbz'
def feature(layer,ident):return next(f for f in json.loads((V/(layer+'.geojson')).read_text())['features'] if f['id']==layer+'.'+str(ident))
mast=feature('fahrleitungen_mast',cfg.get('mast_id',1800));info=[feature('haltestellen_infosystem',i) for i in cfg.get('info_ids',[1143,2584])];c=np.array(info[0]['geometry']['coordinates'][0]);m=np.array(mast['geometry']['coordinates'][0])
av=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features'];platform=shape(next(f['geometry'] for f in av if f['id']=='av_bo_boflaeche_a.'+str(cfg.get('platform_id',459))))
bearing=math.radians(float(info[0]['properties']['orientierung']));bearing2=math.radians(float(info[1]['properties']['orientierung']));u=np.array([math.sin(bearing),math.cos(bearing)]);v=np.array([math.sin(bearing2),math.cos(bearing2)])
candidates=[]
for su in [-1,1]:
 for sv in [-1,1]:
  ends=[c,c+u*su*.75,c+v*sv*.75];foot=unary_union([Point(p).buffer(.035) for p in ends]);inside=platform.covers(foot);clearance=min(Point(p).distance(platform.boundary) for p in ends)
  candidates.append((inside,clearance,su,sv))
valid=[x for x in candidates if x[0]];assert valid
if cfg.get('orientation_signs'):
 chosen=[x for x in valid if [x[2],x[3]]==cfg['orientation_signs']];assert chosen;_,clearance,su,sv=chosen[0]
else:_,clearance,su,sv=max(valid)
u*=su;v*=sv
rec={'mast':mast,'information':info,'origin':[2683775,1246700,400],'mast_ground_local':8.557884216308594,'info_ground_local':8.550666809082031,'ground_basis':'Ray hits on reconstructed AV459, same source-supported working grade as existing platform','u':u.tolist(),'v':v.tolist(),'post_end_clearance_m':clearance,'inferred':{'kind':'Two orthogonal rounded tubular information frames sharing an anchor; exact source type74/88 interpretation not known','main_height_m':3.15,'side_height_m':2.10,'leg_centres_m':.70,'tube_radius_m':.027,'orientation_interpretation':'Source orientation61.40 interpreted as bearing from north; signs selected to remain inside real platform. Bearing convention and exact anchor semantics not independently surveyed.','sign_faces':'Original readable local-map layout using AV data, not a reproduction of the current posted notice or route timetable.','mast':'Official XY and top420.5 preserved. Taper, collars, service cover and ground socket inferred; recorded base408.75 differs from reconstructed local ground by0.192m.'},'references':['sources/references/bellevue_shelters/VBZ_Montagekatalog_2016.pdf#page=5','sources/references/bellevue_shelters/VBZ_Montagekatalog_2016.pdf#page=6','sources/references/bellevue_shelters/VBZ_Montagekatalog_2016.pdf#page=7','sources/references/bellevue_shelters/VBZ_Montagekatalog_2016.pdf#page=13'],'accepted':False}
rec['mast_ground_local']=cfg.get('mast_ground_local',rec['mast_ground_local']);rec['info_ground_local']=cfg.get('info_ground_local',rec['info_ground_local']);rec['inferred']['orientation_interpretation']='Both recorded orientation values interpreted as bearings from north; vector signs keep all legs on the existing real platform. Exact anchor convention remains inferred.';rec['inferred']['kind']='Two joined rounded tubular information frames; exact source type74/88 interpretation not known';rec['inferred']['mast']='Official XY and source top preserved; taper, collars, access cover and ground sleeve inferred.'
rec['ground_basis']=cfg.get('ground_basis',rec['ground_basis'])
(D/'input.json').write_text(json.dumps(rec,indent=2))
# A legible, original geographical neighborhood panel. No invented service times.
N=1536;im=Image.new('RGB',(1024,N),(239,239,229));dr=ImageDraw.Draw(im);font='C:/Windows/Fonts/arial.ttf';bold='C:/Windows/Fonts/arialbd.ttf'
def f(sz,b=False):return ImageFont.truetype(bold if b else font,sz)
dr.rectangle((0,0,1024,164),fill=(24,75,118));dr.text((54,43),'Bellevue',font=f(72,True),fill='white');dr.text((54,191),'Zürich · Umgebung',font=f(43,True),fill=(37,44,47))
box=(50,282,974,1310);xmin,xmax=c[0]-230,c[0]+230;ymin,ymax=c[1]-330,c[1]+180
def P(xy):return (box[0]+(xy[0]-xmin)/(xmax-xmin)*(box[2]-box[0]),box[3]-(xy[1]-ymin)/(ymax-ymin)*(box[3]-box[1]))
clip=Polygon([(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]);mapim=Image.new('RGB',(1024,N),(239,239,229));md=ImageDraw.Draw(mapim)
for ff in av:
 g=shape(ff['geometry']).intersection(clip);kind=ff['properties']['art_txt'];color=(202,200,188) if kind.startswith('Gebaeude.') else (220,227,211) if kind.startswith('humusiert.') else (191,218,226) if kind.startswith('Gewaesser.') or kind=='befestigt.Wasserbecken' else (252,251,244) if kind.startswith('befestigt.Strasse_Weg.') else (229,229,218)
 for p in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[])):
  if p.geom_type!='Polygon' or p.is_empty:continue
  md.polygon([P(xy) for xy in p.exterior.coords],fill=color,outline=(184,185,174))
im.paste(mapim.crop(box),box[:2]);dr=ImageDraw.Draw(im);px,py=P(c);dr.ellipse((px-15,py-15,px+15,py+15),fill=(183,45,40),outline='white',width=3);dr.text((px+22,py-22),'Standort',font=f(29,True),fill=(50,53,49));dr.text((899,301),'N',font=f(29,True),fill=(34,51,65));dr.line((913,396,913,343),fill=(34,51,65),width=4);dr.polygon([(913,332),(905,351),(921,351)],fill=(34,51,65))
scale=100/(xmax-xmin)*(box[2]-box[0]);dr.line((65,1383,65+scale,1383),fill=(35,46,50),width=5);dr.text((65,1401),'100 m',font=f(27),fill=(35,46,50));dr.text((425,1401),'Stadt Zürich · Geodaten',font=f(25),fill=(60,65,63));im.save(D/'neighborhood_map.png')
(D/'panel_receipt.json').write_text(json.dumps({'kind':'Original inferred sign layout from existing AV map geometry; no route or departure assertions','file':'neighborhood_map.png','sha256':hashlib.sha256((D/'neighborhood_map.png').read_bytes()).hexdigest(),'av_source':'sources/features/av_bo_boflaeche_a.geojson','bounds_lv95':[xmin,ymin,xmax,ymax]},indent=2))
# The earlier guard cylinders retained photographic tree smear above these devices.
# This step supplies their actual replacement entities and removes only the guarded volume.
mask=unary_union([Point(m).buffer(.82,quad_segs=40),Point(c).buffer(1.07,quad_segs=40)])
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':mask,'CUT_LOWER':cfg.get('cut_lower',408.70),'CUT_UPPER':422.70,'CUT_BASE':cfg.get('cut_base','haus_trees_approach_refined_cut.json'),'CUT_OUTPUT':cfg.get('cut_output','corner_fixture_photo_cut.json'),'CUT_STATS_KEY':'corner_fixture_replacement','CUT_DESCRIPTION':f'Replace {mast["id"]} and {[x["id"] for x in info]} within radii0.82/1.07m by source-located physical entities. UpperLN02422.70; model subtype and fine equipment geometry explicitly inferred. Original source retained.'})
print(json.dumps({'input':str(D/'input.json'),'clearance_m':clearance,'u':u.tolist(),'v':v.tolist()}))
