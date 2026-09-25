# 当前施工状态

G1未完成，Goal保持active。H:/MyWorld/ZurichWorld是唯一活动代码与新产物目录。F历史资产及Blender/Python/Three.js仍为只读依赖；没有整库复制或删除F原件，原Goal的旧F目录由用户后续迁移指令替代。

## 当前可接续施工稿

H/native/G1_027r8_sternen_entrance_joinery.blend，97,242,858字节，17,200对象，SHA256为beeec6979340d5edcdfd51b8fae27c3e19f857e96cb7e11b506c4c46f2f5290a。workspace.local.json已指向此稿；旧r7及其之前版本保留。这是局部改善后的施工基底，不是整栋、整段或G1验收。

独立进程36340完成旧场所/桥面/链接库及当前立面检查，渲染SG_QA_ENTRY、SG_QA_DOOR_OPEN、SG_QA_CORNER、BF_QA_FLAGS；补充独立进程38148完成门扇数值检查和SG_QA_THRESHOLD。五张1280×840/24采样原始PNG均完整解码并实际查看，两进程实际退出0，stderr为空。退出收据为runtime/logs/blender-20260926_052608_646.exit.json和blender-20260926_055751_734.exit.json。目前没有Blender作业；下一次启动前仍先查询实际进程。

首轮新增门检查因run_path未指定__main__而跳过，已修正调用并增加同进程收据守卫。首轮原收据保留为fresh_view_batch_initial.json，修订收据明确不声称该项在首轮渲染前执行；38148独立从同一原生SHA256重新复核通过。详情见evidence/G1_027r8/visual_review.json及door_fresh_checks.json。

## 这批实际修正

Sternen Grill（Theaterstrasse22，EGID302060199）正面和侧巷八个开间重做连续上亮窗、外框、门扇与独立玻璃，解决中梃穿过招牌及原玻璃分割缝。第二/三开间补双扇门，第三开间有实际铰链控制；框、玻璃、拉手和活动五金一起转动。原门槛至内地坪55mm断缝以实体石材接续。

五个开度的实际求值检查、每态14门下支持点/15通口射线及50处地坪接续通过，检查后关闭状态恢复。全开中央0.9m测试通口、最小约8mm门底净距是几何结果，不是扫掠体碰撞或实际行走结论。默认关闭、public_runtime_enabled为false；门机制、制造尺寸和浅景室内均注明推断。没有新增公开可进入餐厅。

原24上层窗、165桥灯/旗杆、2039源摄影及既有工作摄影网格保持。曝光、整体灯光和原机位未改。实际图像确认连续亮窗、门体和门槛改善；邻楼及前景扫描楔片仍明显，上层窗重复及真实完整室内仍待处理。详见planning/STERNEN_GRILL_FRONTAGES_CN.md。

## 下一块：Theaterstrasse20及门前街面

已用AV23105、地址2505及EGID2372625确认UBS Bellevue身份；取得并实际查看MML建筑师两外观及一室内照片，资料足够进入具体建造。官方沿街边21.645394m、平面364.0742745m²、五条包络面保留，103个三角形使用原测量顶点。405.103m模型底面不能作为入口地坪。

38148已保存90条多层射线与9块相关摄影网格。沿街60条有24条在检查高度范围内无表面命中，其他多见高处雨篷和扫描片；Sternen侧30条都有既有铺面。首层、门槛及门前地面应一起重建。CTX_I3S_33552的同一连通分量包含楼体和前景，不能整块删除。下一批在实体和地面连接完成后有界替换，优先正常眼高两侧近景，不移动有依据的布局。

数据和限制见planning/UBS_THEATERSTRASSE20_CN.md、derived/ubs_theaterstrasse20/site_constraints.json及r8_geometry_probe.json；UBS新实体尚未施工。无需再泛泛搜集同类照片，重点做构造、材料和表面。

## 完整范围与同版实时合流

G1仍为Bellevue—Sechseläutenplatz—Stadelhofen约0.312km²连续区域、外接682×673m。UBS/Kronenhalle/Haus Bellevue未完成面、广场、站内公共通道与楼层联系、其他街道及边界仍需继续。最终需同版原生与实时游览，分别检查碰撞、开门、楼层及自然设施使用；不编排研究任务、不评分、不接入Agent，完整乘车网络留G2。

查看器默认仍旧007r5、候选018r3，不能据网页推断r8。上一批已从r7实际导出116个累计摄影变化块（104有面、12空块），5,213,816字节GLB、50,166三角形；独立往返验证、Three.js真实几何替换/恢复及7项守卫通过。r8工作摄影未改，但不能单独发布差分而缺少相配作者几何。

r7清点作者几何约3886万多边形，95.36%属树木；材质、灯、水体和操作状态尚须同版合流。悬铃木逐叶仿射位置拟合准确，但法线最大偏差约13.63°，未应用为实例化。当前没有最新完整实时或自然使用验收。详见planning/RUNTIME_REJOIN_AFTER_H_MIGRATION_CN.md。

## 迁移与同步

H代码迁移已完成；451份有效来源上轮核对无遗漏，F原件内容未变，H较新修订保留。新原生、缓存、渲染及记录均写H。F约636MiB空间不足仍存在，迁移代码没有释放其大型资产占用；固定库、贴图和软件依赖尚在F，F须保持连接。完整说明见planning/H_WORKSPACE_MIGRATION_CN.md。

稳定批次从H检查后提交GitHub；本批推送结果以Git历史和runtime/migration/github_push_027r8.json为准。重型资产、照片、渲染、本机配置和凭据不入Git。GitHub代码同步不是完整场景资产备份。旧012历史压缩文件的哈希核验尚未完成，但不是当前固定依赖，继续保留。
