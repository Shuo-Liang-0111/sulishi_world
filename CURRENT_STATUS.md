# 当前施工状态

G1未完成。2026-09-25用户指定H:/MyWorld/ZurichWorld为活动工作目录；代码、后续新原生/导出/证据及缓存均写H。历史资产从F:/MyWorld/ZurichWorld读取，必须保持F连接。Goal服务仍保留此前存储中断的blocked状态，本次不标complete、不创建替代Goal；地域和验收边界不变。

## 当前原生与验收差距

最新施工原生为F:/MyWorld/ZurichWorld/native/G1_027r2_bridge_surface_refinement_working.blend，95,722,070字节，16,453对象；SHA256为7224b963c16a9daad6269c3c713a907f1532e81e88d102f44842f73cdfccf951。H的workspace.local.json已经指向此稿。固定库020r2、021r2、025r1及原图必须保留，不覆盖或删除。

本次已从H启动Blender实际重开，MCP1.7/协议9正常、遥测false；12项既有场所检查从H执行通过，三固定库、24共享网格、322新网格重新核验，原生文件未重存。结果在H/runtime/migration/native_reopen.json和H/evidence/G1_027r2；已查看实体视口。本次没有改变场景几何、材质或质量标准，也没有新增视觉/自然使用验收结论。

027r2先前已查看BD_QA_JUNCTION、BD_QA_EAST两张有效实图；QB_QA_SOUTH因F满写成零字节，尚需补渲染。白线已连续，细暗缝、浅起伏、单调铺面及邻近摄影楼面/旗帜失真仍存在。8849接缝探针最大差12.058毫米，3953标线面心不再埋入铺面；窄面仍有24.61%坡面，不能称无障碍或完整碰撞已验收。

实时默认007r5、候选018r3，尚无027r2匹配实时导出或自然使用验收。F/runtime/station_road_working.json可能仍指027r1，是旧记录，不能覆盖H当前选择。详细027r2事实见planning/BRIDGE_SURFACE_REFINEMENT_CN.md；迁移前状态保留在planning/STATUS_BEFORE_H_WORKSPACE_CN.md。

## 工作目录和接续

迁移详情见planning/H_WORKSPACE_MIGRATION_CN.md。当前启动、检查和渲染链路已适配H，历史脚本不应无序执行；含固定F写根的旧脚本复用前逐项移植。Blender/Python/Three.js安装暂留F只读使用，H不是独立资产备份。代码迁移不会释放F的大型占用，但新增工作不应再写F。

作者和完整渲染须串行。当前作者进程31540由H入口启动；每次操作前重新检查其存活，不把本文PID视为永久值。先关闭作者再补渲染南侧对照，保留同一作业句柄；MCP长调用若回包超时，先查最终文件和进程，不重复提交。

旧G1_012历史文件曾在NTFS压缩后因满盘未完成后置哈希核验，本轮未扩大压缩或删除它；012不是当前链接库，保留该待查事项。F仍仅约636MiB余量，新生成工作全部走H。

接着修复桥头表面、真实构造及邻近摄影伪影，完成对应实时导出及自然使用。G1为Bellevue—Sechseläutenplatz—Stadelhofen约0.312km²连续范围（外接682×673米）：还须继续广场、首层、站内公共楼层/通道、其余街道和边界。范围见G1_SCOPE.md；不能缩为局部样片。不编排研究任务、不评分、不接入具身Agent、不调用外部写码API，香港只读。必要资料足够后以物体、构造、材料和表面修复为重点。
