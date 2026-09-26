# Stadelhofen 中央入口独立施工包

活动目录为 `H:/MyWorld/ZurichWorld/parallel/stadelhofen_01`。本包由第二施工线维护，主线负责独立验收、整合及 Git 同步。当前候选为v07，质量结论以 `STATUS.md`、`handoff.json`、`DELIVERY_CN.md` 及对应版本的 `evidence` 为准；v01至v06均保留为整改记录，不能据旧版数值检查推断新版视觉或主线验收通过。

## 对象与文件

- 基底固定为 `H:/MyWorld/ZurichWorld/native/G1_027r8_sternen_entrance_joinery.blend`，SHA256 `beeec6979340d5edcdfd51b8fae27c3e19f857e96cb7e11b506c4c46f2f5290a`。不覆盖基底。
- `native/SF1_baseline_local.blend` 只含53块相关摄影上下文及局部审查灯光/相机，供本包重放。不是另一份全城。
- `native/SF1_v01_stadelhofen_entry.blend` 和 `native/SF1_v01_author_increment.blend` 保留首版及观察到的缺陷。v01源码与构造输入在 `archive/v01`。
- 当前构造输入为 `derived/build_input.json`；当前候选为 `native/SF1_v07_stadelhofen_entry.blend` 与 `native/SF1_v07_author_increment.blend`。v02修底板落脚及CONTEXT机位，v03/v04修侧墙与台座支持，v05/v06暴露左墙脚扫描假地面及窄缝；v07延续墙脚到原回接墙下。保存守卫禁止覆盖已有版本。
- `SF1_AUTHOR_ENTRANCE` 是唯一应合入的新增作者集合，内含实体、材质、文字和门控制。`SF1_REFERENCE_CONTEXT_DO_NOT_MERGE`、`SF1_QA_LIGHTS_DO_NOT_MERGE` 和审查相机不合入全城。
- `derived/crop_manifest.json` 给出逐对象原面编号、保留/删除/裁切数量、保留UV断言、前后指纹及实际裁切盒。v01旧清单已保存在 `archive/v01/crop_manifest.json`。
- 每版 `evidence/<版本>/construction.json` 记录基底、作者对象、源码和增量哈希；`fresh_geometry_checks.json`、`actual_boundary_probe.json`、各视图settings、`fresh_render_batch.json`、`visual_review.json`与实际退出收据共同构成审查证据。

## 本线运行

工作目录必须为H根。只在主线明确交回使用权后运行；`run_blender.ps1` 同时检查租约归属、本线启动许可和实际无存活Blender进程。启动窗口隐藏，用户配置、日志和临时文件写本包。实际进程结束后写 `.process.json` 收据。

```powershell
Set-Location -LiteralPath 'H:/MyWorld/ZurichWorld'
& './parallel/stadelhofen_01/run_blender.ps1' -Script 'check_v01_known_failures.py' -Native 'native/SF1_v01_stadelhofen_entry.blend'
& './parallel/stadelhofen_01/run_blender.ps1' -Script 'build_scene.py' -Native 'native/SF1_baseline_local.blend'
& './parallel/stadelhofen_01/run_blender.ps1' -Script 'render_review.py' -Native 'native/SF1_v07_stadelhofen_entry.blend'
& './parallel/stadelhofen_01/run_blender.ps1' -Script 'verify_replay.py' -Native 'native/SF1_baseline_local.blend'
```

`render_review.py` 先对独立打开的保存原生做几何检查；失败会留下收据并停止渲染。通过后渲染ENTRY、REVERSE、APPROACH、CONTEXT、DOOR_DETAIL、DOOR_OPEN。渲染并不等于视觉通过，PNG还需完整解码并实际查看。其关闭门控且不保存原生；实际原生哈希保持不变。

本地软件只从F读取：Blender 4.5.13 LTS 为 `F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe`；资料/轻量几何 Python 为 `F:/MyWorld/ZurichWorld/.venv/Scripts/python.exe`。PDF参考缓存使用Codex捆绑Python的 `pypdfium2` 和 `pypdf`，不需要安装软件。照片只作参考，不贴到实体表面。

从缓存资料重建输入时，顺序为 `prepare_sources.py`、已提供的站区选择数据、`prepare_geometry.py`、`prepare_construction.py`、`prepare_seam_repair.py`、`prepare_support_revision.py`、`prepare_return_revision.py`、`prepare_foundation_revision.py`、`prepare_left_interface_revision.py`、`prepare_wall_foot_join_revision.py`，最后 `prepare_parts.py`。注意重建准备会覆盖当前派生规格，不能对交付包无记录重跑；先选新版本并冻结归档输入。`prepare_construction.py` 会重置原始规格，必须顺序执行后续修订，保存守卫不会覆盖已有原生。

## 主线增量整合

主线选择自己的新工作版本后，可导入 `apply_increment.py` 并调用 `apply_to_current()`。本函数不会选择、覆盖或保存主线原生，也不改变工作指针。它先验证增量/构造输入哈希与四个当前旧对象的变换、网格指纹，再导入唯一作者集合，对当前旧对象实施有界裁切。不会从r8恢复旧摄影网格。

```python
import sys
sys.path.insert(0, 'H:/MyWorld/ZurichWorld/parallel/stadelhofen_01')
from apply_increment import apply_to_current
receipt = apply_to_current()
```

默认拒绝与r8指纹不同的目标块。如主线先前已修改同一块，应先核验空间/面范围冲突并重订裁切，不应把 `allow_changed_target_meshes=True` 当作日常绕过方式。`verify_replay.py` 只在独立局部baseline内验证上述流程，将每块新裁切结果与本地施工版指纹比较，验证其余上下文和门控制；它不接触主线工作稿，也不能替代主线全场景复核。

v07沿用v06新增的左墙脚低位裁切：比v05增加5.192m²、仅到411.40m LN02，合计161.301m²。需使用v07的 `crop_manifest.json` 和规格SHA；不能沿用v05的156.109m²裁切清单。当前四块目标仍相同，49块其他上下文应完全保留。

## 明确未完成

资料年份和推断详见 `SCOPE_AND_SOURCES_CN.md`。平台标高约±0.15m不确定；门扇制造、铰链外开机制、材料参数及隐藏构造为推断。门后仅浅景闭合空间，不是站内公共通路。目录板具体内容未复原。门的局部射线与扶手分离证明不等于人体、无障碍或实时自然使用验收。

旧站房上层、两翼、站台与地道联系、整个Stadelhofen区域和G1均未由本块宣告完成。完整质量结论由主线独立重开、看多角度原图、检查资料和接缝后作出。

变换守卫依据 `derived/verified_source_transforms.json`：这是从固定r8重新仅导入53个上下文对象、完成依赖更新后的真实世界变换。初次 `native_context_inventory.json` 的网格指纹有效，但matrix_world记录发生在求值之前，保留原记录以供追溯，不再用其中的单位矩阵作裁切守卫。新提取脚本已增加求值更新。主线整合仍严格核对当前目标对象变换，不绕过守卫。
