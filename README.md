# ZurichWorld · 苏黎世场景工程

目标：真实性优先的苏黎世城市世界，可由人实际游览和交互，供后续持续、长程具身研究使用。

本轮只做场景构建与运行体验，验收到真实世界基底及其自然交互可用为止。下一阶段再按研究需求设定任务空间、道具、事件和目标；本轮也不接入后续具身Agent。Astra/Codex负责施工，优先保证真实地理、建筑与人眼近景，使相应空间和日常设施真正可用。区域、线路、建模方案和制作节奏由施工者自主决定。

2026-09-21 已按用户批准的分阶段方案启动 G1，范围为 Bellevue—Sechseläutenplatz—Stadelhofen 连续街区，约0.312 km²。工程尚未完成；不要重复创建已存在的 Goal。最新状态以 [CURRENT_STATUS.md](CURRENT_STATUS.md)、[G1_SCOPE.md](G1_SCOPE.md) 和 [CONSTRUCTION_LOG.md](CONSTRUCTION_LOG.md) 为准。

GitHub：<https://github.com/Shuo-Liang-0111/sulishi_world>。仅同步本项目构建代码、配置和必要说明；大型资产保存在 F 盘完整工程中，范围及恢复限制见 [REPOSITORY.md](REPOSITORY.md)。2026-09-23 用户取消完整资产迁移，H 盘仅保留轻量代码仓库副本。

`native` 保留可编辑 Blender 版本，`sources` 保留来源，`derived` 保留转换结果，`evidence` 保留实际检查记录。`runtime/current_scene.json` 为已同步的默认工作版本；旧亭体室内候选见 `runtime/bellevue_working.json`，最新站区与相邻街面施工见 `runtime/station_road_working.json`。运行入口地址记录在 `runtime/review_server.json`。

| 文件 | 用途 |
|---|---|
| PROJECT_CONTEXT.md | 研究意图、用户要求，以及交给Astra自主决定的空间 |
| DATA_SOURCES.md | 最新城市选择依据、公开数据入口、实际验证情况与缺口 |
| GOAL.md | 本轮目标和应交付的结果，不规定固定施工步骤 |
| WORKING_NOTES.md | 香港经验、本机资源及已发现的转换问题 |
| START_PROMPT.txt | 在新对话粘贴即可要求设定Goal并开始施工 |

继续工作时使用 `F:/MyWorld/ZurichWorld`，先读取上述状态与启动文件，再检查当前 Goal 并接续施工。`START_PROMPT.txt` 和原始 `GOAL.md` 保留项目初始综合目标；当前G1边界及阶段拆分见 `PHASED_GOALS_PROPOSAL_CN.md`，不能把一个局部样片当作整个阶段完成。

施工开始后，可以按实际需要在这里建立源程序、场景、资产、运行入口和记录；本包不预设繁重的工程目录。原香港工程保持只读。
