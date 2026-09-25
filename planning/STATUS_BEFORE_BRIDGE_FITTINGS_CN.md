# 当前施工状态

G1未完成，Goal服务已恢复active。2026-09-25用户指定H:/MyWorld/ZurichWorld为活动工作目录；代码、后续新原生/导出/证据及缓存均写H。历史资产从F:/MyWorld/ZurichWorld读取，必须保持F连接。地域和验收边界不变，不创建替代Goal。

## 当前原生与验收差距

最新施工原生为H:/MyWorld/ZurichWorld/native/G1_027r3_bridge_edge_cleanup_working.blend，95,659,084字节，16,453对象；SHA256为8e823dadd201b94f948f311f4008a87b14a59af7e16d899e6d7af1f313b81c91。独立重开及两张原机位实看后，workspace.local.json已指向H中此稿。F的027r2和固定库020r2、021r2、025r1及原图保留，不覆盖或删除。

本次已从H启动Blender实际重开，MCP1.7/协议9正常、遥测false；12项既有场所检查从H执行通过，三固定库、24共享网格、322新网格重新核验，原生文件未重存。结果在H/runtime/migration/native_reopen.json和H/evidence/G1_027r2；已查看实体视口。本次没有改变场景几何、材质或质量标准，也没有新增视觉/自然使用验收结论。

027r2的南侧QB_QA_SOUTH已从H启动独立补渲染，进程24152完成退出，PNG完整解码并实际查看；收据在H/evidence/G1_027r2/south_view_recovery.json。原F零字节失败文件保留为历史，不作为有效图。白线已连续，细暗缝、浅起伏、单调铺面及邻近摄影楼面/旗帜失真仍存在。8849接缝探针最大差12.058毫米，3953标线面心不再埋入铺面；窄面仍有24.61%坡面，不能称无障碍或完整碰撞已验收。

027r3仅从三块摄影工作副本移除124个已定位的折叠桥缘残面，其他面顶点和UV逐值保持；2039块原始网格、道路与实体桥结构不变。跨盘保存前后，外部贴图、字体和三个库解析到相同文件。首次独立重开被旧检查器的链接图片路径误解析拦下；修复检查器后，进程10436完整通过场所几何、三库哈希、24共享网格、322铺面网格和有限面/UV核验，缺图0，退出0，两张PNG完整解码并实际查看。南侧桥缘折叠青片消失，东向道路和栏杆保留；旗帜、灯头和相邻楼面摄影失真仍然明显。仅保留这次有限修复，不声称整个桥头验收。见planning/BRIDGE_EDGE_CLEANUP_CN.md及evidence/G1_027r3/visual_review.json。

实时默认007r5、候选018r3，尚无027r3匹配实时导出或自然使用验收。F/runtime/station_road_working.json可能仍指027r1，是旧记录，不能覆盖H当前选择。详细027r2事实见planning/BRIDGE_SURFACE_REFINEMENT_CN.md；迁移前状态保留在planning/STATUS_BEFORE_H_WORKSPACE_CN.md。

## 工作目录和接续

迁移详情见planning/H_WORKSPACE_MIGRATION_CN.md。当前启动、检查和渲染链路已适配H，历史脚本不应无序执行；含固定F写根的旧脚本复用前逐项移植。Blender/Python/Three.js安装暂留F只读使用，H不是独立资产备份。代码迁移不会释放F的大型占用，但新增工作不应再写F。

作者和完整渲染须串行。作者33644、失败的首轮渲染34940均已退出；修复后的独立渲染10436退出0，记录在runtime/logs/blender-20260925_231449_549.exit.json。2026-09-25 23:31从H重新打开027r3，作者PID28388；23:52复核MCP正常。实际进程状态在继续前重新核实，不并开完整渲染。下一次用tools/start_blender.ps1默认打开H中027r3；长调用先查最终文件和进程，不重复提交。

用户再次确认迁移后，重新核对F来源的443份有效源码/文档，H无遗漏；10份插件构建副本与H正式源码相同，不重复拷贝。verify_workspace.py已按当前原生版本选择收据；H/027r3哈希、512KiB读写、352份源码语法及实际HTTP资源取回通过。见runtime/migration/code_inventory_recheck.json和workspace_checks_G1_027r3.json。未修改场景；桥头灯具/旗帜的源资料探针还在H工作区，尚未形成新施工验收。

旧G1_012历史文件曾在NTFS压缩后因满盘未完成后置哈希核验，本轮未扩大压缩或删除它；012不是当前链接库，保留该待查事项。F仍仅约636MiB余量，新生成工作全部走H。

接着修复桥头表面、真实构造及邻近摄影伪影，完成对应实时导出及自然使用。G1为Bellevue—Sechseläutenplatz—Stadelhofen约0.312km²连续范围（外接682×673米）：还须继续广场、首层、站内公共楼层/通道、其余街道和边界。范围见G1_SCOPE.md；不能缩为局部样片。不编排研究任务、不评分、不接入具身Agent、不调用外部写码API，香港只读。必要资料足够后以物体、构造、材料和表面修复为重点。
