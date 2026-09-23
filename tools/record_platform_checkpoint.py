"""Consolidate the checked checkpoint, without claiming realtime acceptance."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];V='G1_012r5';E=R/'evidence'/V
qa=json.loads((E/'roundtrip.json').read_text());encoding=json.loads((E/'runtime_encoding.json').read_text());http=json.loads((E/'http_ready.json').read_text());visual=json.loads((E/'native_visual_review.json').read_text());w=json.loads((R/'runtime/station_road_working.json').read_text())
assert qa['native_reopen_verified'] and w['version']==V and all(x.get('status')==200 for x in http['checks'])
assert encoding['written_file_checked']
w['platform_fixtures']={'verification_checkpoint':V,'authored_identities_verified':qa['identities_verified'],'bounds_checked':len(qa['matches']),'max_bounds_error_m':max(x['max_error_m'] for x in qa['matches']),'native_reopen_verified':True,'source_fixture_ids':['fahrleitungen_mast.1800','fahrleitungen_mast.1793','haltestellen_infosystem.1143','haltestellen_infosystem.2584','haltestellen_infosystem.2120','haltestellen_infosystem.2585'],'native_views_inspected':[x['file'] for x in visual['images_actually_inspected']],'runtime_visual_review':False,'natural_use_review':False,'exact_info_subtypes_known':False}
w['next']='Continue AV459 missing information/SIPF/tactile details and neighboring near surfaces. South AV3573 foundation preflight available: correct grade/road joins before reconstructing trees68441/17167. Do not mistake raw height fit for finished ground.'
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
p=R/'CURRENT_STATUS.md';text=p.read_text(encoding='utf-8');lines=text.splitlines();new=[]
for line in lines:
 if line.startswith('|最新树木及构造施工候选|'):
  new.append(line.replace('|最新树木及构造施工候选|','|前一树木及构造检查点|').replace('`runtime/station_road_working.json` → ',''))
  new.append('|最新站台设施与表面施工候选|G1_012r5；`runtime/station_road_working.json` → `native/G1_012r5_platform_surfaces_working.blend`|两端源定位立杆与信息架142对象，正确双面文字/地图；清理已建地面内1.55m²摄影残片，修订四组路缘颗粒尺度及两杆涂层。2868身份、65项包围盒最大误差0.031mm、原生重开无缺图；三个人眼角度已实际查看。设备细部有推断，实时与自然使用未验收；默认仍007r5|')
 elif line.startswith('`web/assets/station_preview.json` 已指向'):
  new.append('`web/assets/station_preview.json` 已指向G1_012r5，5项候选资源HTTP检查均为200。三张实际原生检查图见 `evidence/G1_012r5/native_visual_review.json`。文件可供检查；CUA连接故障下尚未实看实时画面或试用，默认007r5保留。')
 elif line.startswith('下一批沿相接街面推进：'):
  new.append('012系列已替换mast1800/1793及信息组1143+2584、2120+2585。共点锚位与方向分别保留，标准管架与具体组合仍为推断；初稿背面空白、反字和地图90度旋转已依实际渲染修复。012r5清理靠近新信息架的残片并修订材料尺度，轨道视角复查保留整体关系。AV459的info417、SIPF25与tactile894仍未建，周围仍有严重摄影树团/楼面，不能称站台或整区完成。下一片南侧AV3573约1418.25m²及12树/20条VBZ设施记录已从现有数据整理；初步地面与路边高差5—38cm，须先修连续地面与接缝再立树，见 `planning/BELLEVUE_SOUTH_CONTINUATION.md`。')
 else:new.append(line)
p.write_text('\n'.join(new)+'\n',encoding='utf-8')
p=R/'CONSTRUCTION_LOG.md';t=p.read_text(encoding='utf-8');heading='## G1_012—012r5：站台两端设施、双面图文与表面'
if heading not in t:
 t+='\n\n'+heading+'\n\n沿用已有VBZ点位及2016目录，源定位mast1800/1793与两组信息架，保留官方顶高与各自方向；地面与源底高差异、代码74/88未解码均明确记录。共142新对象，标准圆管、共杆节点、套管、边框/玻璃、原创AV周边地图分别建模。初稿背面空白、文字反面方向和地图旋转均由实际图片发现后修正，地图当前位置按两端分别生成。\n\n012r4回读2868身份/65项包围盒；012r5随后按相机射线仅清理已建AV459内1.55m²残片，保护尚未重建设备。四组路缘将过大骨料改为更细代理尺度，两根杆加入原创1m尺度涂层PBR。三个人眼图已实际查看，背景树团和楼面仍明显失真。最终012r5同样回读2868身份/65项包围盒，最大误差0.031mm、重开无缺图；运行贴图编码检查完成。CUA无法连接，station候选可访问但未实看实时或试用，默认保留007r5。\n\n下一片南侧AV3573完成现有数据的地面支持预检，没有生成新模型：1418.246m²、12树、附近20条VBZ设施记录。初步稳健平面与道路高差尚不适合直接施工，不把源数据整理计作完成。\n'
 p.write_text(t,encoding='utf-8')
print(json.dumps({'version':V,'identities':qa['identities_verified'],'bounds':len(qa['matches']),'runtime_bytes':encoding['bytes'],'documented':True}))
