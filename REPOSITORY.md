# 代码仓库与本机资产

仓库：https://github.com/Shuo-Liang-0111/sulishi_world 。同步场景构建与检查代码、Three.js查看器、计划、数据来源和必要记录。推送代码不代表G1已验收。

2026-09-25起，H:/MyWorld/ZurichWorld是唯一活动代码仓库；后续新原生、导出、渲染与缓存均写H。F:/MyWorld/ZurichWorld保留历史原生、链接库、纹理、源数据及旧代码快照，作为依赖读取，不再同步为活动工作树。本次只迁移源码，没有进行127GiB整库迁移，也没有删除F原件。

## 配置与启动

本机使用被Git忽略的workspace.local.json，示例为workspace.example.json。配置实际的历史资产根目录、Blender/Python/MCP安装和当前原生路径。代码不包含大型资产，不能只克隆仓库就打开完整城市。资产许可见DATA_SOURCES.md。

```powershell
Set-Location H:/MyWorld/ZurichWorld
./tools/python.ps1 tools/verify_workspace.py
./tools/start_blender.ps1 -CheckOnly
./tools/start_blender.ps1
./tools/python.ps1 tools/serve_review.py
```

只运行一个Blender。网页代码来自H，历史资源按文件从F回读；网页目前仍为旧实时版本，不能把它称为027r2同版导出。工作原生选择以workspace.local.json为准，不从旧实时指针推断最新建模稿。

当前原生渲染入口（先确认作者实例已退出）：

```powershell
./tools/start_blender.ps1 -Background -Script tools/render_native_views.py -ScriptArgs QB_QA_SOUTH
```

启动命令返回作业PID及独立日志路径；返回starting不等于渲染完成。检查进程结束、日志、PNG完整解码及画面之后才报告结果。原生、链接库、纹理和前置数据目前必须保持F盘可读；新版本保存到H/native的新名称并核对跨盘链接，禁止覆盖F旧稿。

## 依赖

- Blender4.5.13LTS，现有可执行文件暂从F读取，独立配置及临时目录在H。
- Python3.12，依赖锁定见runtime/requirements-lock.txt；通过tools/python.ps1复用F安装，工作目录与缓存切H。
- Three.js0.180.0，web/package.json及锁文件；现有node_modules可只读回用F。
- MCP服务mcp-for-blender==2.0.3。插件源为ahujasid/mcp-for-blender提交7cc602252386b92829bc7364e3a897253610be38，addon.py的SHA256为4900048de7b7a61cc6aeaccadeacdd1afec364410e651574416bdf0a1ecdad58，MIT许可证。小型vendor源码及许可证已本机复制到H，未重新纳入Git；克隆到新机器时须从匹配来源恢复它。

## 开发和核验边界

新脚本使用tools/workspace_paths.py：read_path逐文件读取本地或历史输入，write_path只写活动工作区。当前启动、027r2几何核验、原生渲染和网页链路已适配。历史制作脚本保留原版和明确的前置版本，有固定F写路径的文件须逐项移植后运行；本仓库尚不是一键从零重建全城的工具。

tools/legacy_runtime额外归档原runtime中未被Git跟踪的局部诊断源码。tools/verify_code_mirror.py是旧的双工作树镜像核验器，本次改为H主工作区后不再用于F/H验收，不能用它覆盖新稿。

每个稳定批次在H审查差异、凭据与大文件后提交推送。大模型、地图、贴图、导出、渲染、环境与本机凭据均不入Git；LOCAL_ASSET_INVENTORY.json是旧资产规模/指纹记录，不是资产备份。迁移实测与限制见planning/H_WORKSPACE_MIGRATION_CN.md。
