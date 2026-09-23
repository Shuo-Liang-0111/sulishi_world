"""Record observed native results and verified files; keep runtime acceptance open."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];V='G1_013r2';E=R/'evidence'/V
qa=json.loads((E/'roundtrip.json').read_text());encoding=json.loads((E/'runtime_encoding.json').read_text());http=json.loads((E/'http_ready.json').read_text());visual=json.loads((E/'native_visual_review.json').read_text());geom=json.loads((E/'fixture_geometry_check.json').read_text());w=json.loads((R/'runtime/station_road_working.json').read_text())
assert qa['native_reopen_verified'] and w['version']==V and encoding['written_file_checked'] and all(x.get('status')==200 for x in http['checks'])
w['south_public_space']={'verification_checkpoint':V,'ground_area_m2':1418.2459585209083,'new_tree_ids':[17167,68441],'remaining_inventory_trees':10,'new_fixture_objects':104,'authored_identities_verified':qa['identities_verified'],'bounds_checked':len(qa['matches']),'max_bounds_error_m':max(x['max_error_m'] for x in qa['matches']),'native_reopen_verified':True,'native_views_inspected':[x['file'] for x in visual['images_actually_inspected']],'runtime_visual_review':False,'natural_use_review':False,'input_files':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'derived/bellevue/south_context/platform_input.json',R/'derived/bellevue/south_context/tree_inputs.json',R/'derived/bellevue/south_context/info/input.json',R/'derived/bellevue/south_context/fixtures_input.json',R/'derived/bellevue/south_context/canopy_refinement.json']}}
w['next']='Continue actual AV3573 canopy/central pavilion and remaining facilities. Resolve real EGID302040350 roof/ground relationship before replacing its plan hole or entering it. Ten source trees remain unreconstructed. Partial photographic tree/canopy remnants still fail near-view acceptance. Runtime review pending CUA connection recovery.'
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
p=R/'CURRENT_STATUS.md';t=p.read_text(encoding='utf-8');lines=[]
for line in t.splitlines():
 if line.startswith('|最新站台设施与表面施工候选|'):
  lines.append(line.replace('|最新站台设施与表面施工候选|','|前一站台设施与表面检查点|').replace('`runtime/station_road_working.json` → ',''))
  lines.append(f'|最新南侧公共空间施工候选|{V}；`runtime/station_road_working.json` → `native/G1_013r2_south_near_working.blend`|1418.246m²真实地籍人行面、四个源步行连接附近坡端、两棵独立树、104个设施构件。三个人眼实图已看；{qa["identities_verified"]}身份/{len(qa["matches"])}项包围盒回读并原生重开。剩余树团、中央亭体仍不合格；实时/自然使用未验收|')
 elif line.startswith('`web/assets/station_preview.json` 已指向'):
  lines.append('`web/assets/station_preview.json` 已指向G1_013r2，5项资源HTTP检查均为200。原生实图记录见 `evidence/G1_013r2/native_visual_review.json`。本轮重新尝试CUA仍返回nodeRepl.fetch失败，未实看实时或试用，默认007r5保留。')
 elif '下一片南侧AV3573约1418.25m²及12树/20条VBZ设施记录' in line:
  lines.append(line.split('下一片南侧AV3573')[0]+'南侧AV3573已进入013系列实体施工，当前进展及残留见下文。')
 else:lines.append(line)
if '013系列已构建AV3573连续人行面' not in '\n'.join(lines):
 k=next(i for i,x in enumerate(lines) if x.startswith('008系列推进了'))
 lines[k:k]=['013系列已构建AV3573连续人行面1418.246m²、路缘与12树穴，保留160.966m²真实建筑内孔；该孔不是可以补满的空地。17167/68441两棵树保持源位置与20/16m高度，根颈落入土面，树冠/树皮为推断。两立杆1799/4217、信息组2864+2581、DFI67及Haifisch631已成为实体，具体信息组与110L桶型为明确推断。实际渲染发现后修正摄影树冠边缘及金属曲面假接缝；其余10树、中央亭体与部分残片仍未完成。地面非微小三角面最大坡度5.049%，极微小面最大11.54%另记，不能声称全网格5%或无障碍通过。详见 `planning/BELLEVUE_SOUTH_CONTINUATION.md`。','']
p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
p=R/'CONSTRUCTION_LOG.md';t=p.read_text(encoding='utf-8');heading='## G1_013—013r2：南侧连续地面、树木与日常设备'
if heading not in t:
 t+='\n\n'+heading+'\n\n沿用现有AV3573、道路、树木与VBZ设施数据，重建1418.246m²人行面、路缘、12树穴及四处源步行连接附近的坡端。先调整地面与现有道路的关系，保留真实建筑孔；不将官方建筑405.029m GroundSurface直接当作约408.4m街面。正常人眼图暴露中央亭体未完成与摄影残片，未判合格。\n\n重建20m树17167与16m树68441；源位置/高度保留，独立分枝、根颈、冠宽与表皮为推断。初版圆形裁切留下明显树团边缘，013r2按现有影像与相邻树位限定替换区域，保护完整亭体屋檐平面与未重建设备，不按单机位删遮挡。仍有10树及背景残片待处理。\n\n104个设施构件对应两根源立杆、一个双向信息架、一块DFI与一个Haifisch垃圾桶。必要补查仅针对垃圾桶厂家结构图；实际110L型号未证实。垃圾桶有真实投口、内胆、封闭斜顶和门缝；初版曲面明暗接缝由法线造成，改为径向法线并加入轻微磨纹粗糙度。厂家图标称桶身450mm，当前模型檐口454mm为细部代理，未冒充实测。信息牌使用原创AV地图，DFI没有虚构班次。\n\n三张013r2原生实图已查看，接地、源顶高和投口射线核验通过；导出回读'+str(qa['identities_verified'])+'身份/'+str(len(qa['matches']))+'项包围盒，最大误差'+str(round(max(x['max_error_m'] for x in qa['matches'])*1000,4))+'mm，原生重开无缺图。CUA本轮仍不能连接，候选更新不代表实时或日常使用验收。G1继续。\n'
 p.write_text(t,encoding='utf-8')
print(json.dumps({'version':V,'identities':qa['identities_verified'],'bounds':len(qa['matches']),'runtime_bytes':encoding['bytes'],'recorded':True}))
