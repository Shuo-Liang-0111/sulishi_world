# GitHub 同步范围与恢复说明

仓库：<https://github.com/Shuo-Liang-0111/sulishi_world>。

这里同步场景制作与核验代码、Three.js 查看器、阶段计划、数据来源和施工记录。当前工程仍在施工；代码执行成功、局部渲染或仓库推送均不表示 G1 已完成。当前版本和限制见 `CURRENT_STATUS.md`。

大型 Blender 检查点、城市源数据、贴图、导出、历史证据和运行缓存由本地完整项目保存，未上传 GitHub。仓库不是这些大型资产的异地备份，也不是克隆后立即可运行的完整场景。`LOCAL_ASSET_INVENTORY.json` 记录本次迁移前的目录规模与关键检查点指纹。

## 本机迁移状态

原位置 `F:/MyWorld/ZurichWorld`，计划新位置 `H:/MyWorld/ZurichWorld`。只有完整复制、逐文件核验、路径修订及从新位置重开工程通过后，才切换工作根目录并释放旧副本。目前 H 盘的小样读写校验通过，但持续写入较慢，完整迁移尚未通过。不得把 H 盘的部分副本当作唯一工程。

## 开发依赖

- Blender 4.5.13 LTS，Windows 当前使用独立安装与独立用户配置。
- Python 3.12，本机版本记录见 `runtime/requirements-lock.txt`。
- Three.js 0.180.0，依赖见 `web/package.json`；在 `web` 中安装依赖。
- MCP 服务 `mcp-for-blender==2.0.3`。当前插件来自 `ahujasid/mcp-for-blender` 提交 `7cc602252386b92829bc7364e3a897253610be38` 的 `addon.py`，SHA256 `4900048de7b7a61cc6aeaccadeacdd1afec364410e651574416bdf0a1ecdad58`；源许可证为 MIT。本机插件路径 `tools/vendor/mcp-for-blender/addon.py`，上游代码未重复纳入本仓库。

必须先恢复匹配的本地资产及版本指针，再运行 `tools/start_blender.ps1` 或 `tools/serve_review.py`。部分历史制作脚本依赖明确的前置版本且含本机路径，不能无序执行来重建整个工程；本项目尚无经过全流程验证的一键重建命令。

后续每个稳定施工批次提交代码和记录；先检查暂存内容、凭据与大文件，再推送。场景资产许可沿用各自来源，详见 `DATA_SOURCES.md`，不统一改写第三方许可。
