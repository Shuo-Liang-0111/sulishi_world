# Stadelhofen 中央入口 v07 本地交付

本块已冻结，供主线独立验收与合入。三拱入口、雨篷、四级台阶、扶手及铺面保留；已修正扶手脱开、侧墙深度缝、台座支承、左端扫描假坡和墙脚端部窄缝。六张原图已完整解码并实际查看，独立原生检查和本版增量重放均通过。`accepted=false`，这不是主线接收或G1完成结论。

Blender已于 **2026-09-26T15:08:01.1290638Z** 明确归还主线。归还时实际无存活Blender，三个本版进程均已退出；本线停止，不启动新区域。[资源归还收据](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/resource_return.json)。

## 原生与增量

- [SF1_v07_stadelhofen_entry.blend](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/native/SF1_v07_stadelhofen_entry.blend)，4,266,108字节，SHA256 `90311677bd16012211931180e883de3e37bc1677f6fa1b11a8fbda4cc0b11db5`。
- [SF1_v07_author_increment.blend](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/native/SF1_v07_author_increment.blend)，4,140,333字节，SHA256 `97b600da998b81e474f35941712894ba83110cc0c518b32fa66aefd4d916efbb`。
- 唯一合入集合 `SF1_AUTHOR_ENTRANCE`：280对象，其中271基础网格。局部上下文、灯光与QA相机不合入主线。
- 固定只读基底 r8 的SHA256 `beeec6979340d5edcdfd51b8fae27c3e19f857e96cb7e11b506c4c46f2f5290a` 再次核对未变。局部baseline也未保存覆盖，主线当前工作稿未被本线写入。
- [冻结文件清单](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/package_manifest.json)、[v07源码与输入归档](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/archive/v07/build_input.json)；当前规格SHA256 `978645591a96e05f57dbc48c4dc5731465f9d6410a7cfcdf6f43e6e0e2fb0271`。

## 实際验证

- 独立重开：271基础网格有限、闭合、无退化面、正体积；294条路径支持、四级标高通过。
- 209处实际新旧地面内外配对，无缺失、不可靠多层或超过20mm处；最大平面投影差 **11.659mm**。另核验所选真实保留三角坡度均小于15°，最大13.268°，新增左边界使用|Nz|≥0.995；见[坡度复核](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/boundary_slope_audit.json)。
- 八柱与横管/底板真实相交，40处底板—垫层—实际地面接触、42处侧墙回接、824处台座支承通过。
- 左侧460个真实地面及75mm至1.95m站立带检查、45处墙脚与保留墙面/地基连接、20处端部实体封口通过。旧v05同地面检查检出52处异常；旧v06端部20条射线全部漏空，失败证据保留。
- 中央双门0–95°与扶手沿面区间最小分离约0.575m，作者地面保守竖向净距约8.000mm；只覆盖所述对象，不等于全场景扫掠或人体使用验收。门默认关闭，`public_runtime_enabled=false`。
- 独立增量重放导入全部280对象、重现四块裁切指纹；49块其他上下文网格及全部53个变换保留，门控制0→1→0正常；107条链接依赖记录均存在。
- ENTRY/REVERSE相机与v01完全一致；本版全部六相机位置、旋转、焦距及渲染参数与v05一致。没有靠改机位或曝光遮掩修复问题。

[完整几何检查](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/fresh_geometry_checks.json) · [本版独立增量重放](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/integration_replay.json) · [实际图像审查](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/visual_review.json)。

- PID 31548：实际退出0，stderr为空，[20260926_225704_273.process.json](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/runtime/20260926_225704_273.process.json)
- PID 32652：实际退出0，stderr为空，[20260926_225839_777.process.json](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/runtime/20260926_225839_777.process.json)
- PID 2348：实际退出0，stderr为空，[20260926_230552_359.process.json](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/runtime/20260926_230552_359.process.json)

## 最后一次边界修改

v05保留的摄影墙脚被拖成约27°斜坡，不能作为地面。v06/v07仅在左墙脚增加u[-3.50,-1.30]、v[-0.82,1.54]、z[9.80,11.40]的低位裁切，增加5.192m²，总平面 **161.301m²**；整体外接范围和测绘台座/台阶/雨篷不动。新地面依据108个邻近平缓点，拟合RMSE2.868mm、最大残差12.304mm，仍是相对摄影符合程度。v07仅延续低墙脚堵住77mm端部缝，没有再次扩大裁切。详见[资料、坐标与推断](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/SCOPE_AND_SOURCES_CN.md)。

| 当前摄影对象 | 删除原面 | 裁切原面 | 完全保留原面 | 删除表面积 m² |
| --- | ---: | ---: | ---: | ---: |
| CTX_I3S_32639 | 191 | 44 | 305 | 248.694612 |
| CTX_I3S_32645 | 59 | 9 | 42 | 57.394344 |
| CTX_I3S_32648 | 27 | 17 | 582 | 14.745112 |
| CTX_I3S_32651 | 30 | 9 | 360 | 14.105107 |

表面积不是平面面积。保留顶点和UV均精确保留；逐面编号、前后指纹、四个裁切盒见[当前裁切清单](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/derived/crop_manifest.json)。该清单已区别于v05，不能沿用旧156.109m²规格。

## 主线接续

在主线明确选择的新r10工作副本中调用[apply_increment.py](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/apply_increment.py)的`apply_to_current()`。助手先核对当前四块网格、已独立核正的世界变换和增量/规格SHA；只导入作者集合，并裁切主线当前对象，不append旧整块CTX。助手不保存原生、不改全局工作指针。

若目标块已被主线改变，应检查真实范围冲突并重订裁切，不能日常绕过网格守卫。主线仍须从当前总场景重开、看图、核验真实旧新边界与原施工区域回归，再决定是否接收。原始变换记录的求值时机错误及核正经过已经留档，当前依据[verified_source_transforms.json](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/derived/verified_source_transforms.json)。

## 原始视图

- [SF1_QA_ENTRY](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/SF1_QA_ENTRY.png)
- [SF1_QA_REVERSE](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/SF1_QA_REVERSE.png)
- [SF1_QA_APPROACH](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/SF1_QA_APPROACH.png)
- [SF1_QA_CONTEXT](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/SF1_QA_CONTEXT.png)
- [SF1_QA_DOOR_DETAIL](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/SF1_QA_DOOR_DETAIL.png)
- [SF1_QA_DOOR_OPEN](H:/MyWorld/ZurichWorld/parallel/stadelhofen_01/evidence/v07/SF1_QA_DOOR_OPEN.png)

## 保留限制

绝对入口标高约±0.15m不确定；门制造、铰链机制、材料光学、埋置基础和低墙脚接续均明确为推断。门后只是闭合浅景，目录板具体内容未复原。上层、两翼、周围摄影失真、站内真实公共连通、平台/地道、同版实时表现及完整G1仍待后续。F盘历史库与纹理仍为只读依赖，代码交付不是全场景资产备份。
