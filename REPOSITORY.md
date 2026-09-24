# GitHub 同步范围与恢复说明

仓库：<https://github.com/Shuo-Liang-0111/sulishi_world>。

这里同步场景制作与核验代码、Three.js 查看器、阶段计划、数据来源和施工记录。当前工程仍在施工；代码执行成功、局部渲染或仓库推送均不表示 G1 已完成。当前版本和限制见 `CURRENT_STATUS.md`。

大型 Blender 检查点、城市源数据、贴图、导出、历史证据和运行缓存由本地完整项目保存，未上传 GitHub。仓库不是这些大型资产的异地备份，也不是克隆后立即可运行的完整场景。`LOCAL_ASSET_INVENTORY.json` 记录本次迁移前的目录规模与关键检查点指纹。

## 本机代码副本与场景资产

2026-09-23用户改为仅复制和上传构建代码，完整资产迁移已取消。完整场景继续位于 `F:/MyWorld/ZurichWorld`；`H:/MyWorld/ZurichWorld` 用作轻量代码仓库副本，与 GitHub 同步。H盘副本只包含代码、配置和必要记录，不包含场景、原始地图、贴图、渲染、Python环境或历史缓存，不能独立打开完整场景。

现有 Blender MCP 和模型资产引用继续使用 F 盘，不把路径批量改到缺少资产的 H 盘。只复制代码并不会释放 F 盘的大型场景占用。后续构建仍须先确保资产工作盘有足够空间；F盘原件未因本次复制而删除。

## 开发依赖

- Blender 4.5.13 LTS，Windows 当前使用独立安装与独立用户配置。
- Python 3.12，本机版本记录见 `runtime/requirements-lock.txt`。
- Three.js 0.180.0，依赖见 `web/package.json`；在 `web` 中安装依赖。
- MCP 服务 `mcp-for-blender==2.0.3`。当前插件来自 `ahujasid/mcp-for-blender` 提交 `7cc602252386b92829bc7364e3a897253610be38` 的 `addon.py`，SHA256 `4900048de7b7a61cc6aeaccadeacdd1afec364410e651574416bdf0a1ecdad58`；源许可证为 MIT。本机插件路径 `tools/vendor/mcp-for-blender/addon.py`，上游代码未重复纳入本仓库。

运行场景时继续从 F 盘完整工程启动。仅有 H 盘或 GitHub 代码时，必须先恢复匹配的本地资产及版本指针，再运行 `tools/start_blender.ps1` 或 `tools/serve_review.py`。部分历史制作脚本依赖明确的前置版本且含本机路径，不能无序执行来重建整个工程；本项目尚无经过全流程验证的一键重建命令。

后续每个稳定施工批次提交代码和记录；先检查暂存内容、凭据与大文件，再推送。场景资产许可沿用各自来源，详见 `DATA_SOURCES.md`，不统一改写第三方许可。

## 轻量副本核验

H 盘仓库只做快进同步，不覆盖其中未提交的修改。F/H 同一提交且工作区干净后，在 F 盘工程运行：

```powershell
.venv/Scripts/python.exe tools/verify_code_mirror.py --mirror H:/MyWorld/ZurichWorld --receipt evidence/storage/code_only_sync_025r1.json
```

核验逐个读取跟踪文件，检查 UTF-8 文本、大小及资产扩展名，比较内容和 SHA256；仅允许 Windows 换行差异并单独列出。另检查 H 盘有无跟踪列表之外的文件及 Git 对象完整性。收据只保存在 F 盘，不复制场景资产。GitHub 推送结果及远端提交仍需另行核对；本命令不声称已联网确认远端。
