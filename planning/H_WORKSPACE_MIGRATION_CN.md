# H盘主工作目录迁移（2026-09-25）

用户要求将全部苏黎世构建代码迁往H，之后从H继续施工。以H已有的3897d7f提交为基底核对F：没有遗漏F的跟踪文件；H的WORKING_NOTES比F新，保留新稿。另复制并逐文件SHA256核验47份本地辅助源码/插件文件，共1,131,631字节；其中包含原先runtime中的10个构建诊断脚本，另归档至tools/legacy_runtime纳入代码仓库。上游插件保留MIT许可证，仍不重复上传其vendor目录。没有复制大型资产，没有删除F原件。

## 目录职责

| 用途 | 当前位置 |
|---|---|
| 活动代码、Git提交、计划与状态 | H:/MyWorld/ZurichWorld |
| 后续新原生、导出、渲染、核验与临时缓存 | H项目内native、web/assets、evidence、runtime等目录 |
| 历史原生、三份固定链接库、纹理、源数据 | F:/MyWorld/ZurichWorld，只读输入 |
| 已有Blender、Python及Three.js安装 | 暂留F，通过本机配置引用 |
| GitHub | sulishi_world，仅代码与必要记录 |

代码迁移不会显著释放F盘已有占用；作用是让新增工作写入H。H仍依赖连接中的F资产，不是可脱离F运行的完整备份。没有把历史目录联接到H，也没有把所有F路径盲目替换成不存在的H资源。

## 运行路径

`workspace.local.json`记录旧资产根目录、运行环境和当前027r3原生（位于H）。`workspace_paths.read_path`逐文件先查活动目录，缺少时读取旧资产；已有的绝对历史输入路径保留其身份。`write_path`只允许向活动H工程写入，并阻止目录越界。

当前Blender启动、MCP客户端、12项027r2检查、当前原生渲染和网页服务已适配。网页在H提供代码，只对assets和node_modules目录回读F，不开放整个项目。历史制作脚本保留其原始版本和前置依赖；需要重用时逐项移植，不允许无序运行或直接写回F。新的模型保存应使用H/native新版本名，并重新核验跨盘链接与纹理，不覆盖F旧稿。

Codex本机配置只调整blender_zurich的cwd及缓存环境，其余配置经TOML等值比较保持不变，私有备份保留在本机Codex配置目录。命令仍使用F已安装的MCP可执行文件；桌面可能需要重新加载该服务才能采用新环境。项目内MCP客户端可直接使用H配置。[官方MCP配置说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

## 已实测

- H 512KiB写入、flush/fsync、重新读取比对通过；测试文件随后删除。验证时H约1.90TiB可用，F约636MiB。
- 347个顶层Python源码语法通过；本地源文件迁移清单见runtime/code_migration_manifest.json。历史脚本的语法通过不代表已适配新目录或可无序重跑。
- H启动入口实际重开027r2，16,453对象，Blender4.5.13LTS、插件1.7、协议9、遥测false。原生SHA256仍为7224b963c16a9daad6269c3c713a907f1532e81e88d102f44842f73cdfccf951。
- 从H执行原有12项场所检查，重新校验三份链接库、24共享网格、322修订网格及场所几何；证据写H。耗时234.6秒，MCP等待期间出现“No data received”，未重复执行；之后读取最终收据确认12项完成，并再次确认插件可正常响应。记录见runtime/migration/native_reopen.json。
- 真实HTTP请求核对H首页/查看器、F的Three.js及资源JSON字节一致；越界和目录列表请求被拒绝。仅验证服务与资源读取，没有声称浏览器已展示最新027r2实时版本。
- 独立新启动的stdio MCP客户端也已从H连通，报告保存在runtime/migration/fresh_mcp_client.json；后续无需依赖桌面已缓存进程的旧工作目录。
- 已实际查看重开后的Blender实体视口；原生未重存，迁移没有改动城市几何或材质。此次未重跑完整城市渲染，没有新增视觉/自然使用验收结论。

## 接续事项

G1未完成，后续恢复为active；不能因迁移而标complete或创建替代Goal。既有目标中的旧F目录由本次用户指定的H工作目录取代。027r2南侧第三张图已在H补齐并实看；旧012历史文件的压缩后完整性问题单独保留，012不是当前链接依赖。

随后已在H保存首份新工作原生027r3，独立重开、三库哈希及缺图检查通过；修复跨盘情况下检查器遗漏image.library的路径误判。两张原机位实图已查看，局部桥缘残片修复保留，working_native更新为H路径。见BRIDGE_EDGE_CLEANUP_CN.md。仍须完成全G1范围、等价实时导出与自然交互检查，质量标准不变。

## 用户再次确认迁移后的复核（2026-09-25）

重新比对F的Git跟踪文件及tools/web/runtime中的辅助源码，共453个候选文件。其中443份有效源码/文档在H均有对应文件：414份内容相同（允许换行差异），29份为H迁移适配与后续修改，保留H新稿。余下10份是插件build/lib的生成副本，与H中src目录的正式源码逐字节相同；不重复复制构建产物。没有发现遗漏源码。详细记录为runtime/migration/code_inventory_recheck.json。

修复verify_workspace.py固定读取旧027r2收据的问题，改为根据配置中的原生版本查找对应收据并严格核对版本、路径、字节数和SHA256。已用当前H/027r3运行通过：352份顶层Python语法、512KiB写入与回读、当前原生哈希、H网页代码及F只读资源HTTP取回均通过；启动配置和正在运行的MCP连接也正常。新收据为runtime/migration/workspace_checks_G1_027r3.json，旧收据保留。本次没有改变或重存场景，没有新视觉验收结论。

H约1.90TiB可用，F仍约636MiB；代码迁移已完成，但历史资产和安装依赖未迁移，不能断开或清空F。后续新增施工、证据和缓存继续写H。

2026-09-26再次实测H写入/flush/回读512KiB、365份顶层Python语法、当前027r4原生哈希及H网页代码/F只读资源HTTP读取通过，收据runtime/migration/workspace_checks_G1_027r4.json。随后027r5、027r6新原生和独立渲染均从H路径运行；这些是继续施工候选，是否提升由独立重开和实际图像决定。没有再次从F覆盖H，没有复制大型历史资产，也没有删除F原件。

027r6完成独立重开与四图实看后，H工作入口已更新。再次运行verify_workspace.py通过：366份Python语法、新原生SHA256与大小匹配、H写入回读和HTTP资源检查；收据runtime/migration/workspace_checks_G1_027r6.json。此为可继续施工的局部改善稿，整段视觉与自然使用仍未验收，具体遗留问题见CURRENT_STATUS.md。

027r7也已在H保存、独立重开并完成四图实看，渲染实际退出0后提升施工入口。verify_workspace.py再次通过372份顶层Python语法、原生大小/SHA256、H写入/flush/回读及真实HTTP检查，收据runtime/migration/workspace_checks_G1_027r7.json。只读F资源回退仍正常；不是整库资产搬迁，没有释放F的模型占用。后续导出与记录继续写H，新稿不能被F旧代码覆盖。

收尾按最新逐文件清单再次核对451份来源代码/文档：H无遗漏、F来源哈希均未改变，保留H后续修改，不重复复制。收据runtime/migration/code_inventory_verified_027r7.json。H网页还完成了实际浏览器核验：旧007r5/1421作者对象能打开，摄影与实体切换/恢复正常，浏览器错误和警告为空；明确不是027r7完整实时验收。临时核验服务已关闭，后续需要查看时重新从H启动并读取新端口。
