# ZurichWorld · 苏黎世场景工程

目标：真实性优先的苏黎世城市世界，可由人实际游览和交互，供后续持续、长程具身研究使用。

本轮只做场景构建与运行体验，验收到真实世界基底及其自然交互可用为止。下一阶段再按研究需求设定任务空间、道具、事件和目标；本轮也不接入后续具身Agent。Astra/Codex负责施工，优先保证真实地理、建筑与人眼近景，使相应空间和日常设施真正可用。区域、线路、建模方案和制作节奏由施工者自主决定。

2026-09-21 已按用户批准的分阶段方案启动 G1，范围为 Bellevue—Sechseläutenplatz—Stadelhofen 连续街区，约0.312 km²。工程尚未完成；不要重复创建已存在的 Goal。最新状态以 [CURRENT_STATUS.md](CURRENT_STATUS.md)、[G1_SCOPE.md](G1_SCOPE.md) 和 [CONSTRUCTION_LOG.md](CONSTRUCTION_LOG.md) 为准。

GitHub：<https://github.com/Shuo-Liang-0111/sulishi_world>。仅同步构建代码、配置和必要说明。**2026-09-25 起，H:/MyWorld/ZurichWorld 为主工作目录，后续代码与新产物都写 H。** 历史模型、贴图、原始数据和已有软件依赖仍从 F 盘读取，未进行127GiB整库复制，也未删除原资产；详见 [REPOSITORY.md](REPOSITORY.md) 和 [迁移记录](planning/H_WORKSPACE_MIGRATION_CN.md)。

`native` 保留可编辑 Blender 新版本，`sources` 保留来源，`derived` 保留转换结果，`evidence` 保留实际检查记录。旧文件可从配置的 F 盘来源读取。当前建模基底由本机 `workspace.local.json` 中的 `working_native` 指定，为027r2；旧 F 盘实时默认007r5、候选018r3不是最新建模稿。运行入口地址记录在 H 盘 `runtime/review_server.json`。

| 文件 | 用途 |
|---|---|
| PROJECT_CONTEXT.md | 研究意图、用户要求，以及交给Astra自主决定的空间 |
| DATA_SOURCES.md | 最新城市选择依据、公开数据入口、实际验证情况与缺口 |
| GOAL.md | 本轮目标和应交付的结果，不规定固定施工步骤 |
| WORKING_NOTES.md | 香港经验、本机资源及已发现的转换问题 |
| START_PROMPT.txt | 在新对话接续既有G1和H盘工作目录 |

继续工作时使用 `H:/MyWorld/ZurichWorld`，先读 `AGENTS.md` 和当前状态，再检查既有 Goal 并接续施工，不重复创建。当前G1边界及阶段拆分见 `G1_SCOPE.md`、`PHASED_GOALS_PROPOSAL_CN.md`；迁移不会改变地域、几何或验收范围，不能把一个局部样片当作整个阶段完成。

```powershell
Set-Location H:/MyWorld/ZurichWorld
./tools/start_blender.ps1 -CheckOnly
./tools/start_blender.ps1
./tools/python.ps1 tools/serve_review.py
```

先确认没有旧 Blender 进程，再启动；最后一条命令前台运行网页服务。仓库其他机器克隆后须先配置 `workspace.local.json` 并恢复对应资产，不能只凭代码打开城市。

施工开始后，可以按实际需要在这里建立源程序、场景、资产、运行入口和记录；本包不预设繁重的工程目录。原香港工程保持只读。
