# Stadelhofen 01 — v07已冻结交付，Blender已归还，待主线验收

当前原生：H:\MyWorld\ZurichWorld\parallel\stadelhofen_01\native\SF1_v07_stadelhofen_entry.blend

SHA256：90311677bd16012211931180e883de3e37bc1677f6fa1b11a8fbda4cc0b11db5

当前增量：H:\MyWorld\ZurichWorld\parallel\stadelhofen_01\native\SF1_v07_author_increment.blend

SHA256：97b600da998b81e474f35941712894ba83110cc0c518b32fa66aefd4d916efbb

六张1400×960原PNG已完整解码并实际查看。最后的左端假坡、白色斜三角及77mm墙脚窄缝已在原APPROACH机位修正；ENTRY/REVERSE保留v01参数，全部六机位保留v05参数。271基础网格、209外接缝、8柱/40底板支持、42侧墙、824台座、460侧地面与净空、45墙脚接续、20端部射线通过。外接缝最大11.659mm；实际所选保留地面均小于15°。

PID31548构建、PID32652独立重开及六图、PID2348本版增量重放均实际退出0，stderr为空。280作者对象和四块裁切重放一致，其余49网格、全部53变换保留，r8及baseline未保存改写，107条链接依赖存在。

左墙脚低位裁切比v05增加5.192m²、仅到411.40m LN02，总平面161.301m²；v07没有再次扩大。务必使用当前规格、增量与crop_manifest，不沿用旧清单。详见DELIVERY_CN.md及evidence/v07/visual_review.json。

Blender于2026-09-26T15:08:01.1290638Z归还主线01a08947-06f2-7123-b7c7-c955cfa6c809，归还时实际无Blender。主线可启动，本线许可关闭并停止；当前实时状态以共享租约为准。尚未分派下一块。

accepted=false，等待主线独立合入/重开/看图；本线没有宣告主线接收。上层、两翼、周围扫描失真、真实公共室内、同版实时与完整G1仍未完成。历史失败仅放在handoff.version_history及对应旧版证据中。
