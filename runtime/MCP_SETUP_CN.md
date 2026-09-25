# Blender MCP 配置与验证

## 当前入口：H盘（2026-09-25）

活动代码目录已改为 `H:/MyWorld/ZurichWorld`。从该目录运行 `tools/start_blender.ps1`，默认读取配置中的027r2原生；Blender的工作目录、用户配置、日志与临时目录均在H。Blender和Python可执行文件暂保留F安装，F模型、三份链接库与纹理仍是读取依赖。

本机Codex配置中仅修改blender_zurich的cwd及路径环境，其余配置和推理设置保持。已经实测Blender4.5.13、插件1.7/协议9、遥测false及完整027r2重开。修改配置不保证已缓存的桌面MCP子进程自动重启；可使用下面的H入口启动新的stdio客户端：

```powershell
Set-Location H:/MyWorld/ZurichWorld
./tools/python.ps1 tools/blender_mcp_client.py --list --report runtime/mcp_tools.json
# 执行源码时另加 --code tools/具体脚本.py --user-prompt '用户的完整原话'
```

当前核验脚本耗时可能超过MCP回包等待；先查H输出与进程，不能重复提交。迁移实测见 `planning/H_WORKSPACE_MIGRATION_CN.md`。

## 初次配置的历史记录（以下F盘入口已被上面的H入口替代）

2026-09-21 已配置并实测。此处只记录工具联通，不代表城市建成。

- MCP 名称：`blender_zurich`，Codex 配置位于 `C:/Users/34384/.codex/config.toml`。其余配置经 TOML 等值比较保持不变，未更改用户的 `max` 推理设置。
- 已安装的旧 Codex CLI 不认识现有 `max` 设置，CLI 添加失败后改用保留原内容的 TOML 追加方式；配置已通过解析。备份保留在同一私有配置目录。
- MCP 服务：PyPI 正式发布的 `mcp-for-blender==2.0.3`，项目 `.venv`。初次从 Git 源码安装缺少未提交的 telemetry config，已改装正式 wheel；没有自行添加遥测密钥或接口。
- Blender：`F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe`。
- 插件来源：`ahujasid/mcp-for-blender`，提交 `7cc602252386b92829bc7364e3a897253610be38`，`addon.py` SHA256 `4900048de7b7a61cc6aeaccadeacdd1afec364410e651574416bdf0a1ecdad58`。插件报告版本 1.7 / 协议 9，与服务端期望协议一致，实际工具验证通过。Git 插件与发行 wheel 内插件字节不完全相同，未混称同一文件。
- 插件、用户配置、临时文件和 MCP 独立配置均放在此项目 F 盘 `runtime` 中；连接只监听 `127.0.0.1:19876`。
- 遥测环境关闭，Blender 侧遥测同意为 false；未启用任何收费模型生成集成。

启动：PowerShell 执行 `F:/MyWorld/ZurichWorld/tools/start_blender.ps1`。它以隐藏窗口启动专用 Blender，已有对应监听时复用，不打开香港工程。

当前会话的标准 MCP 客户端：

```powershell
& 'F:/MyWorld/ZurichWorld/.venv/Scripts/python.exe' -X utf8 'F:/MyWorld/ZurichWorld/tools/blender_mcp_client.py' --code 'F:/MyWorld/ZurichWorld/tools/某个制作脚本.py' --report 'F:/MyWorld/ZurichWorld/runtime/某次调用.json'
```

这是 MCP SDK 经 stdio 调用上游服务，再进入 Blender 插件执行，未用外部 LLM API。桌面当前工具清单未热刷新时可继续使用此入口；桌面重新加载 MCP 配置后，原生工具清单会读取已注册项。

验证记录：`mcp_smoke/verification.json`。实际完成 addon 协议检查、空场景查询、对象与材质创建、保存、GPU Cycles 渲染、重新打开、对象标记与尺寸检查、MCP 视口截图。`mcp_smoke/render.png` 与 `verification-5-0.png` 已实际查看。测试场景与正式城市工程分离。

官方配置依据：https://learn.chatgpt.com/docs/extend/mcp
上游：https://github.com/ahujasid/mcp-for-blender

G1_005：实际尝试材质检索时发现免费Poly Haven集成原来处于关闭状态，已单独启用；搜索、预览与4K沥青材质下载均经MCP调用成功。收费生成集成继续关闭。启动脚本已同步这一设置。

2026-09-22：当前任务已能直接调用`mcp__blender_zurich__get_addon_status`、场景读取、执行、视口截图和Poly Haven检索，不必再等待工具清单刷新。原生007r5重开后再次验证协议9、插件1.7、Blender4.5.13与遥测false；1426个施工集合对象（含5灯，导出1421身份）、2039原始摄影分块、缺图0。中途进程30396的日志显示正常注销并写quit.blend后退出，未找到新的崩溃证据；已保留日志，从正式已保存007r5恢复，未采用退出恢复文件。监听中断时先查进程/端口，再恢复，不能重复启动冲突实例。
