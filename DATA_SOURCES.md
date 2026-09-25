# 城市选择与可用数据

核查日期：2026-09-21。**本项目选择苏黎世。** 推荐基于较新的城市摄影底座、可用于步行与桥路连接的专项数据，以及完整市内公共交通的组合潜力；没有证据证明任何一城的原始网格已经满足成品近景质量。

卢森堡仍是强备选：2023独立带纹理建筑、2024 LiDAR、2025正射、全国连续覆盖与逐产品CC0声明比较齐全。但其已核实的连续摄影网格采集于2020年，当前电车延伸与部分街面变化需要跨年代融合。苏黎世的2025照片网格减少了这一时相差距；这是事实与工程判断，不等于“年份新所以所有地方更清晰”。

## 公开数据入口

| 数据 | 正式入口 | 可用于什么；需要注意什么 |
|---|---|---|
| 2025摄影网格 | [产品17549](https://www.stadt-zuerich.ch/geodaten/stzh3d/17549)；[官方viewer](https://3d.stzh.ch/appl/3d/zuerichvirtuell/) | 2025-05-19数据状态；倾斜摄影与LiDAR生成，实际公开I3S+JPEG已取得。官方标PoC，有完整性/几何/视觉限制。适合真实城市基底，近景仍需修补。 |
| 建筑屋顶与外壳 | [Dachmodell](https://data.stadt-zuerich.ch/dataset/geo_bauten___dachmodell)；[现状组合建筑](https://data.stadt-zuerich.ch/dataset/geo_bauten___kombinierte_darstellung_heute) | CC0，单独建筑有助于编辑和替换。不是2025照片mesh，也不提供完整室内；新楼可能仅体块。 |
| 地形 | [Digitales Terrainmodell TIN](https://data.stadt-zuerich.ch/dataset/geo_digitales_terrainmodell__tin_) | CC0；2024产品基于2021–2022 LiDAR，并引入道路、桥区约束及水面修正。不能把其约30–40cm平均高程误差当作门槛或站台精度。 |
| 步行与自行车网 | [Fuss- und Velowegnetz](https://data.stadt-zuerich.ch/dataset/geo_fuss__und_velowegnetz) | CC0；包含人行道、横道、人行桥的位置关系，帮助恢复真实步行连接。WFS已可达，不代表选区拓扑已经全部验证。 |
| 桥梁、下穿等结构 | [Kunstbauteninventar](https://data.stadt-zuerich.ch/dataset/geo_kunstbauteninventar) | CC0；帮助区别桥上桥下、隧道和挡墙等。不是含完整构造与净空的BIM。 |
| 树木信息 | [Bauminventar](https://data.stadt-zuerich.ch/dataset/geo_bauminventar) | CC0；支持位置/高度与摄影树团的清理替换。标准树模型和树冠宽度不应冒充逐树实测。 |
| 电车与公交 | [ZVV Static GTFS](https://data.stadt-zuerich.ch/dataset/vbz_fahrplandaten_gtfs) | CC0；当前包确有shapes、trips、stops与stop_times。覆盖ZVV交通区域，不等于都在苏黎世市域mesh内，也不等于完整S-Bahn。 |
| VBZ 物理基础设施 | [VBZ-Infrastruktur OGD](https://data.stadt-zuerich.ch/dataset/geo_vbz_infrastruktur_ogd) | CC0；本轮取得22层，含实际钢轨、轨道轴线、道岔、接触网、导盲板、售票机、站牌、座椅、广告位等。都是有各自精度/年代限制的参考；很多设施仅为点位，不给出外形、尺寸或工作状态。官方特别提示接触网可靠性20%、质量50%，必须实景复核。 |
| 2025 TrueOrthofoto | [正式产品16710](https://www.stadt-zuerich.ch/geodaten/download/Orthofoto_2025_Stadt_Zuerich___Sommer___TrueOrthofoto___inkl._Infrarot) | 有8cm产品说明，但当前条目无直接下载且使用字段有限制，不能当作已到手资产。8cm是正射产品分辨率，不是mesh或立面分辨率。 |

这些入口是调查起点，不是限定资源清单。继续利用公开地图、资料和可用的真实摄影参考补全；原始倾斜照片整包及相机参数本轮未找到直接下载入口，不能假定它们已开放可取。

## 2025 mesh 的使用依据

已核查现行[市地理信息法规 StGeoIR](https://www.stadt-zuerich.ch/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/704/100/704.100-StGeoIR-2025_V3.pdf)：附件3第9页将三维城市模型列为可自由使用和再分发、须提供下载的数据。州政府[2025年官方材料](https://www.zh.ch/content/dam/zhweb/bilder-dokumente/themen/umwelt-tiere/umweltschutz/zuercher-umweltpraxis-zup/2025/112/zup112_2025_a2460_luftbilder-gis.pdf)及[市政府2025年报](https://www.stadt-zuerich.ch/content/dam/web/de/aktuell/publikationen/2026/geschaeftsbericht/geschaeftsbericht-2025.pdf)（PDF第149页）将新摄影mesh归入城市三维模型，提供了强适用依据。

据此可以继续离线取样、转换和本地施工，不因服务item的许可字段为空就认定禁止使用。产品17549尚无显式法定类别编号映射或独立CC0标记；资产清单引用法规和产品归属依据，**不要擅自标为CC0**。具体图层如有相反条件，针对该层处理；不要把正射产品16710的字段自动套到mesh。保留来源与修改关系，最终发布时如实说明依据。

这些数据在 `F:/MyWorld/research/city-reassessment-20260921` 与 `F:/MyWorld/research/goal-construction/zurich-source`。它们是研究输入，不是已建成的城市。最终施工资产可以由你采用缓存、分块、内容寻址或其他合适方式组织，避免无谓重复大下载。

I3S真实端点示例：

`https://3d.stzh.ch/3darcgis/rest/services/Hosted/local_GEOZ_3DMesh_2_1/SceneServer/layers/0`

这只是一个图层，不能覆盖所有选区。通过官方viewer配置中的WebScene及图层清单核对所有相交分块，走到真正叶节点检查源细节；旧目录已保存相关配置。

## 选区与交通的事实提醒

市内有较紧凑的完整电车线路候选，不必复制整个ZVV。但2026年主站附近施工导致改线：例如6/14属于同车联运，15的当前运行关系也与旧图不同；少数班次有延长或不同终点。不能用线路名或最常见shape替代完整运行关系。

自行选择运营日期和模拟时段，解析对应真实班次、站序及变体，并核对mesh覆盖。完整线路可以形成区域边界；换乘必须实际涉及不同车辆以及真实步行连接。不要为了满足任务而虚构本来无需发生的换乘。

源图、模型、地形、道路与班次可能属于不同年份，保留它们各自年代，优先修复施工范围内已知变化。较新的数据是减少修复负担的机会，不是跳过近景观察和实际通行验证的理由。

这些资料用于约束场景复原和真实交通运行。选择清楚的世界时间背景并处理影响实际空间的明显年代冲突；未知内部按建筑与使用逻辑补全并标注。数据调查服务于本轮场景构建；具体研究任务场景设定、后续Agent接口及训练/评测数据管线不在本轮范围。

## 新增通用材料（非现场扫描）

- [Poly Haven bark_platanus](https://polyhaven.com/a/bark_platanus)，Dimitrios Savva，CC0，4K、1.5×1.5m；用于悬铃木粗树皮，原图/hash见`sources/textures/polyhaven/bark_platanus/receipt.json`。不是Bellevue逐树扫描；较光滑斑驳的上枝仍待细化。
- [苏黎世2014 Bellevue改造说明](https://www.stadt-zuerich.ch/misc/de/mitteilungsarchiv/medienmitteilungen/2014/02/140207b.html)记录Rämistrasse站台三棵悬铃木移除两棵。当前69773保留源坐标及2022库存记录12m高度，不把早期树量直接补回场景。
- [Cal Poly SelecTree1099](https://selectree.calpoly.edu/tree-detail/1099)提供Platanus × hispanica形态及同物异名参考；枝叶是原创建模，没有挪用该站照片作为纹理。
- Frank Dietze的Bellevue摄影参考，来源[Modernism in Architecture](https://modernism-in-architecture.org/buildings/tram-shelter-bellevue/)，本地`Frank_Dietze_1000038375.jpg`和`8377.jpg`及receipt已实看。是主Rondell和周边的摄影参照，不证明西侧2015站棚全部细部，也不作为分发纹理。

- Poly Haven concrete_floor_01，Rob Tuytel，CC0，4K、2×2m真实纹理尺度；用于007r2推断的站台矿物质路缘。原始图、SHA256与出处存于 `sources/textures/polyhaven/concrete_floor_01/receipt.json`，通过已配置的MCP取得。仅材料类别和风化观感参考现场照片，不声称该贴图来自Bellevue现场。
- Poly Haven concrete_floor_worn_001，Dimitrios Savva、Rico Cilliers，CC0，4K、3×3m；用于007r4细骨料混凝土轨道铺面。原始图/hash存于`sources/textures/polyhaven/concrete_floor_worn_001/receipt.json`。是通用材质，现场实拍只约束材料类别；未把它冒充现场扫描。
- SWISSIMAGE Bellevue细部WMS请求：LV95 [2683500,1246765,2683650,1246910]，1800×1740，`sources/references/swissimage-bellevue-detail.jpg`及同名receipt。请求像素约8.33cm不等于原生分辨率；摄影采集日期未确认，2026是取回时间。用于铺装分区和可见黄线轮廓，与官方步行网交叉核查；不用影像里的车辆作为实体资产。

## 街角两棵悬铃木的011系列补充

树119962沿用已存Bauminventar：LV95 [2683523.69,1246862.008]、Platanus x hispanica、2022记录17m高度；69773保留原12m记录。冠形、根颈、分枝与表皮是推断建模，不是逐树扫描。未新增地点搜索。上部斑驳树皮及土壤为原创程序材质；粗树皮至剥落树皮的连续图集由原CC0 bark_platanus与原创纹理派生，4K、8位，明确属于新工作材质，原16位源文件保留。来源、参数与hash分别在 `derived/materials/platanus_flaking`、`plane_trunk`、`tree_soil` 的receipt.json。

011r1在实际射线定位后扩大69773树团的摄影替换范围，显式保留mast1800与infosystem1143/2584邻域；这些设备尚未重建，类型代码74/88尚未解读，不据点位编造确切设备型号。原始2039个摄影分块仍保留。

## Haus Bellevue 立面与屋面

Haus Bellevue 相邻街面使用已存的 AV13983/35946、EGID9011202 与地址记录，以及 VBZ mast1794 的位置/顶高；建筑师 [SPPA 复原项目](https://sppa.ch/projekt/revitalisierung-haus-bellevue-zuerich/)的外观照片和图纸已保存于 `sources/references/haus_bellevue`，只作建模参照，不用于分发贴图。已实看的外观图用于首层、四层上部立面及圆弧转角；公开平面为其他楼层，不当作首层实测图。商户身份参考[苏黎世旅游局 Café Felix](https://www.zuerich.com/en/visit/restaurants/cafe-felix)。立面竖向细部、用材、窗内浅景和陈列均标为推断/设计。通用矿物漆饰面来自 Poly Haven `beige_wall_001`，Dimitrios Savva、Rico Cilliers，CC0、4K、3×3m；receipt 与原图存于 `sources/textures/polyhaven/beige_wall_001`，不是现场扫描。

010系列沿用这些资料，没有再开展地点搜集。转角半径约4.252m由已有AV轮廓拟合；屋面来自已存EGID9011202官方面。三角化中89个修复/交点顶点采用面内插值，涉及源多边形最大非平面残差32.71mm，不能声称所有新顶点都是原测量点。010r2/r3根据同一外观照片补了三个椭圆屋窗，位置、尺寸、框型均为推断；保留屋面包络并在局部真实开孔。记录见 `derived/haus_bellevue/roof_triangulation_audit.json`、`roof_details_input.json`。

屋瓦采用 [Poly Haven roof_slates_03](https://polyhaven.com/a/roof_slates_03)，Rob Tuytel，CC0、4K，源纹理尺度3×3m；本建筑以2.25m重复尺度作视觉代理，非现场测量。原图及hash见 `sources/textures/polyhaven/roof_slates_03/receipt.json`。曲面采用连续周向UV，不同朝向坡面选择对应建筑轴向，避免逐三角形投影导致拼片和拉伸。

## 南侧公共空间013系列

沿用已缓存AV3573、道路/步行线、树木表及VBZ点位，未重复搜集地点资料。树17167/68441分别为20/16m悬铃木，源位置保留；两杆1799/4217保留顶高416.46/418.90m。地面、根冠形、具体设备制造细节明确为推断，见 `derived/bellevue/south_context`。中央建筑EGID302040350的160.966m²地籍孔与完整官方屋檐保护保留，尚未完成首层重建。

本批必要补查是[ANTA110L Haifisch产品](https://onlineshop.antaswiss.ch/de/artikel/AH-C110-00001)及其[制造商尺寸图](https://onlineshop.antaswiss.ch/daten/bilder/Technische_zeichnungen/Abfallhai%20110%20liter/AH-C110-00001%20Abfallhai%20110l.pdf)。已保存PDF、实际查看页与SHA256于 `sources/references/street_furniture`。图纸高1089mm、桶身直径450mm，投口261×110mm、底边898mm；网页标高1088mm，相差1mm，当前按图纸。点631源类型确为Haifisch，但110L、无烟灰盒具体版本未确证，不能称精确现场型号。模型有3mm壳体、实际侧孔、内胆、斜顶；檐口454mm为细部代理。厂家图只作结构依据，不作为分发纹理。

不锈钢微磨纹PBR为原创、1m尺度、2K，见 `derived/materials/ground_stainless/receipt.json`；没有伪称现场扫描或添加无依据的锈蚀。其余涂层、沥青、路缘、树皮与树叶沿用已有来源和推断说明。

## Bellevue西侧2015年站棚补充

EGID302063027官方屋面三要素及AV459、VBZ设施身份见planning/BELLEVUE_WEST_PLATFORM.md。承建方Andreas Meier / Scherrer Metec，Immobilia 2016-05第76页：https://www.svit.ch/sites/default/files/publications/Immobilia_2016_05.pdf ，本地PDF、渲染页和SHA256已保存在sources/references/bellevue_shelters；页面照片已实看，仅作为研究参照，不进入分发纹理。建筑师画廊仍403，另一广告摄影链接返回登录HTML而非图像，未作为视觉依据。

## 站台设施构造补充

012系列仅补读既有VBZ2016安装目录第5/6/7/13页，原页渲染为 `VBZ_INFO_PAGE_*.png`。NT/ST/NTK给出3.15m/2.10m级高度、约0.64m净宽和圆管/共杆节点，作为明确推断的构造依据；仍未找到数据库代码74/88与型号的可靠对应，不将参考尺寸冒充点位实测。mast1800/1793保留源XY与顶高420.5/420.2m；源底高分别比现有重建站台高约19.2cm/3.5cm，接地套管按实际场景地面补全，不把两种高程说成一致。

两处共点组1143+2584、2120+2585分别生成可编辑信息架。图面是用已有AV地物制作的原创周边地图，当前位置分别对应各自源点；不是现场告示的复制，不包含未经核实的班次或线路表。构造/地图/来源见 `derived/bellevue/corner_fixtures` 与 `west_end_fixtures`，原始摄影源保留。

012r5使用原创1m尺度缎面涂层PBR图（`derived/materials/satin_grey_coat/receipt.json`），仅模拟微表面和粗糙度差异，不声称现场磨损。四组路缘沿用已保存CC0 `concrete_floor_01`，从2m映射改为约0.667m的细骨料视觉代理；不是现场花岗岩扫描或矿物判定。原图不改，来源许可不变。

- [VBZ设施安装目录，2016 V2](https://www.stadt-zuerich.ch/content/dam/stzh/vbz/Deutsch/Ueber%20das%20Departement/Formulare%20und%20Merkblaetter/Infrastruktur/RLV230019_SMS_SR_Haltestellen_Montagekatalog_2016_V2.0_160614.pdf)：候车椅、售票机基础、信息屏立杆等。PDF及实际查看的17/22/23/24页在`sources/references/bellevue_shelters`。标准2m独立椅不自动等于此处Bank in WH lang；基础尺寸不等于设备外壳尺寸。
- [APG海报制作规范](https://www.apgsga.ch/en/templates-and-specifications)：本地APG_Poster_production_2021.pdf，F200与发光型尺寸不同；具体安装框型仍需实景复核。只作尺寸参考。
- [ZVV售票机2023官方照片](https://www.zvv.ch/de/ueber-uns/zuercher-verkehrsverbund/medien/medienmitteilungen/2023/22-05-2023-Echtzeitinformationen-neu-auf-ZVV-Ticketautomaten-verf-gbar.html)：本地ZVV_ticket_2023.jpg及receipt已保存并实看；是设备近照，不是Bellevue点位证明，不作为分发纹理。
- [Trapeze ZVV设备案例](https://www.trapezegroup.eu/wp-content/uploads/2021/11/Zurich-Transport-Authority-ZVV-case-study.pdf)：本地PDF，说明SmartInfo系列部署；不能据此断言Bellevue64点的确切机箱型号。
- GeoCat完整XML缓存`sources/catalogue/vbz_geocat.xml`，UUID 11c8cc0e-2305-46e8-8879-bdd5e26860a4。许可为CC0，但ORIENTIERUNG字段定义为空；本批以共线广告点验证角度解释，保留不确定性。


## Bellevueplatz2定向补充（G1_014）

- 保留既有官方EGID302040350六组BB04/EO13面、AV75249、地址和九项VBZ设施。源GroundSurface405.029m不是本次公共入口地坪。
- City Zürich《Masterplan ZüriWC 2015》，纸页80—81、本地PDF第41页。公开镜像：https://disco-legacy-data.s3.eu-central-1.amazonaws.com/public/upload/5/6/56987.pdf 。PDF和下载收据、完整页/平面/外观裁图保存在sources/references/south_service；实际查看平面与内外照片。SHA256：547027bf95db0bae8e431e1fcfd6a122888e0dee6b3ec05e1638bb292d595144。引用原出版者，但明确下载来自镜像。
- 市政府2002年重新开放公告：https://stored-data.stadt-zuerich.ch/mm/mm_allg/medien_dib_vbz_bellevue_eroeffnung.htm 。历史用途依据，不推断当前商户/价格/时刻。
- 2015官方规划批准：https://www.stadt-zuerich.ch/misc/de/mitteilungsarchiv/medienmitteilungen/2015/07/150708a1.html 。仅确认规划背景。
- 1938工程论文页面返回验证页，未取得可核看的图纸，不用它声称精确恢复细部。

详见planning/BELLEVUE_SERVICE_PAVILION.md。市政资料的再分发条件与本次原创细部应分开记录；研究成果发布前需要另核实原资料许可，不把公开可读等同于CC0。

Bellevue东侧59号大喷泉：沿用水务objectid466真实位置；补充[Stadt Zürich艺术目录173-00](https://kbsz.zetcom.net/de/collection/item/556/)的近似尺寸与作品身份，目的是明确物体构造。水务台账与艺术目录对金属/年代存在差异，未消除；basis.json分列。公开网页及图片链接存于sources/references/bellevue_fountain59，图片尚未实际查看，不作为已完成视觉依据。网页图片仅供建模参照，不打包成分发纹理。暂未启动该喷泉的几何制作。

### Fountain59 limited visual references

Official identity/approximate dimensions remain in `sources/references/bellevue_fountain59/basis.json`. The official art page's image URLs returned403; no access-control workaround attempted. Three public photographs by Roland Fischer (Roland zh), CC BY-SA3.0, were obtained from their actual Commons file links and inspected: [overall2010](https://commons.wikimedia.org/wiki/File:Z%C3%BCrich_-_Bellevue_IMG_4445.JPG), [casting2010](https://commons.wikimedia.org/wiki/File:Z%C3%BCrich_-_Bellevue_IMG_4446.JPG), [overflow2011](https://commons.wikimedia.org/wiki/File:Bellevue_(Z%C3%BCrich)_2011-03-23_15-11-00.JPG). Dates are historical, not a claim of synchronized present-day observation. Receipt/hashes are in `commons_receipt.json`; images are references only, never surface textures. Repeated research stops here unless a concrete modelling ambiguity needs it.

### 临河土面与南端亭体的定向补充

- [Poly Haven Forest Ground05](https://polyhaven.com/a/forest_ground_05)：Charlotte Baglioni，CC0，官方标注2米物理尺度。实看预览后取得官方4K Blender材质及五个文件，逐项核对发布方MD5/大小并记录SHA256。MCP下载两次TLS失败，随后从相同官方URL正常HTTPS下载，未关闭TLS校验。原始贴图与收据在`sources/textures/polyhaven/forest_ground_05`。这是通用泥土扫描代理，不能当作苏黎世当地采样。
- Utoquai2f：已缓存AV20161、地址39399、EGID302020548的官方101628屋面/107095墙/131378底面。八边形17.601514m²及屋面411.255m LN02固定；源底面405.322m不是入口地坪。补核[Imbiss Riviera运营方](https://imbiss-riviera.ch/)及[图库](https://imbiss-riviera.ch/gallery)；首页照片主要是食品和背景，不能支撑完整建筑构造。
- 实际查看[2025年3月21日Bluewin报道配图](https://www.bluewin.ch/de/news/schweiz/wir-kaempfen-bis-zum-schluss-stadt-zuerich-will-den-riviera-imbiss-am-seebecken-nach-42-jahren-weghaben-2616008.html)：金属框、浅色面板、外翻售卖窗盖、不锈钢台面和可见室内。照片拍摄日期未确认，只用于有限外观参照，不作当前经营状态证明，不用作材质或发布资产。缓存及指纹在`sources/references/utoquai_2f/exterior_receipt.json`。020已按这些有限依据建立亭体；门窗朝向、未见面和厨房配置明确为推断，不能冒充照片直接证据。

### 020r4已有表面资料的保留和派生

本批没有新增外部资料请求。已记录的Poly Haven `asphalt_03`、`oak_veneer_01`共8张内嵌图片原编码被保留到各自永久源目录；不是重新下载、重新压缩或重新估计尺寸。逐图SHA256、原路径、尺寸和色彩信息在`evidence/G1_020r4/permanent_surface_images.json`。原Blender检查点仍保留。

`derived/materials/plane_trunk_patch`继承已有CC0 `bark_platanus`粗皮与项目原创的`platanus_flaking`表皮，生成三张4096²、8位工作图，名义图集尺度2.5×4.5m；新旧源指纹和生成方法在该目录`receipt.json`。覆盖率与每树周向相位均是为修复实图问题作出的推断，不是当地21棵树的扫描。旧图集与所有源贴图均保留，未改变树木官方身份、位置和库存高度。

## Riviera主步道与滨河连接021

沿用缓存的AV145、35398与八处岸墙轮廓，以及`av_ei_linienelement`内117条主梯线片段。状态日期多为2022-05-31，XY记录没有提供可直接使用的阶梯高程。183个原摄影近水平支持单元用于稳健地面拟合，并沿共享边接前版网格；0.165m级高、墙体竖向和材料均为推断。AV28347表述为暗渠水体，不能误作露天水面。完整依据及来源差异见`planning/RIVIERA_QUAY_CONSTRUCTION_CN.md`。

- 市政府2020年阶梯更新公告：https://www.stadt-zuerich.ch/de/aktuell/medienmitteilungen/2020/12/201214a.html 。用于理解维护背景，不能当作今日完工测量。
- Jakob Schilling原建筑师项目：https://www.jschilling.ch/projekte-forschung-oeffentliche-bauten-schweiz-ausland-work/uferpromenade-bellevue-zuerich 。历史照片和平面解释滨河通道与Quaibrücke下穿关系，不能冒充当前全部细部。缓存URL、图片与哈希在`sources/references/riviera_quay`，版权保留，只用于研究参照，不作分发贴图。
- 局部SWISSIMAGE WMS确认铺装、阶梯分段和泊位大体关系。请求日期与请求像素间距不等于拍摄日期或原始分辨率。原图及收据同上。

原始2039摄影块及20条选定地籍要素保留。已有CC0沥青、混凝土仅为材质代理；新结构没有声称采用当地实测材料扫描。

## Riviera河侧第二排树木021r1/r2

使用同一份已缓存2022树木表，AV145内的23522、37402、62437、79383、84969、88495、101985、106877、114015共9棵均记录为Sophora japonica（部分Regent），库存高度7–14m；位置、树种和高度直接保留。胸径、树冠、根颈、复叶分布和18.956407m²树池总开口为明确推断，不是新增实测。土面沿用Poly Haven forest_ground_05，树皮沿用bark_brown_02，两者为CC0通用扫描代理；未再采集同类贴图或重复搜索地点。

源文件指纹、逐树参数与实际孔洞在`derived/bellevue/riviera_quay/tree_build_input.json`；两版摄影替换范围分别记录于`tree_cut_basis.json`和`tree_continuous_cut_basis.json`。后者依据021r1真实像素射线，仅连接两个已重建的铺面，保留源树相邻分界以及建筑、墙、台阶、泊位保护。所保留的锥形摄影残片尚无可靠身份判断，不记作已经确认的树、设备或障碍。

## Quaibrücke公共下穿023

继续使用已缓存AV39461、KUBA477/502/552及南侧AV6191钢梯、AV15891岸墙；南梯13条踏步线为4535—4547。不能将Hohlraum Bellevue结构空腔称为开放室内，也不能把暗渠水面图层当作露天水面。完整源身份、差异及推断见`planning/QUAIBRUECKE_PUBLIC_CONNECTION_CN.md`。

- [1985年桥梁工程文章，Heierli等](https://espazium.s3.eu-central-1.amazonaws.com/files/2024-03/sbz-1985_Quaibruecke-Zuerich.pdf)：实际查看纵断面、横断面及桥底照片；这不是未能取得PDF的Marth/Schilling下穿专文。以历史构造关系为依据，不直接覆盖后续改造后的平面。
- [WALO改造项目](https://www.walo.ch/de-ch/projekte/instandsetzung-quaibruecke-zuerich)确认2015—2016工程涉及桥梁及Bellevue侧结构空腔；其说明不能提供公共下穿的精确地坪。
- [步行记录及第18张现场照片](https://www.alpine-wandergruppe.de/kurztrips/zuerichhorn_dolder/zuerichhorn_dolder.htm)实际看到了桥下弧形钢梁、加劲板、槽墙、深色步行面；拍摄日期未确定。
- [摄影者2013年天气记录](https://blog.thinkpunk.ch/category/fotos/)只作为历史墙面与孔洞参照，不把漏水事件带入日常场景。两张照片已记录URL及SHA256于`sources/references/quaibruecke/photo_receipt.json`，仅研究参照，不作为分发贴图。

三个旧摄影低面点经原图集检查不能可靠归为地坪，全部排除。桥面257个空间支持单元用于独立稳健拟合；隐蔽槽底405.45m LN02、详细坡度、板/梁厚度、吊杆、涂层、座椅细分和排水为明确推断。新表面沿用已许可CC0沥青、混凝土、木材及原创程序化涂层，没有声称使用现场材料扫描。


## Quaibrücke桥梁与水体024

沿用AV33090桥梁、16660/21372河湖和39381桥下河道；岸侧28347/28358/12074仍视为暗渠，不渲染为露天水面。桥下39381的实际空间性质同时由已查看1985剖面和桥底照片约束，不能只凭图层名称推定。

为补齐西侧桥墩33079，对[市政府2025年末地籍WFS](https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Amtliche_Vermessungsdaten_Stadt_Zuerich_Jahresendstand_2025)作一次小范围请求，取得16条、143,320字节；与原有三墩重叠的几何一致。请求时间2026-09-23T21:56:03Z，文件与收据在sources/features/quaibruecke/av_ei_context_extension*，SHA256为6491bb6db71acc8c6eef3cf8440d32b7fe9091b4705bb5757e1c5a2bccf19850。数据状态日期与请求日期分开，不称为现场测量。

1985文章纵断面的406.00m LN02均水位仅为历史依据；当前潮位/水位未经验证。水底395m是封闭渲染体积代理，不是水深数据。波纹、吸收、桥墩湿痕、支座、钢构细部和管线回路均明确推断。继续使用已有许可材料，不新增现场扫描声明。完整源身份、范围和限制见planning/QUAIBRUECKE_WATER_CONTEXT_CN.md。

## Quaibrücke南侧上层步道025

使用缓存AV36232人行面、13条与之相交的构造记录和2022树木库存。范围内12棵Platanus x hispanica保留源位、树种和18–26m记录高度；邻接两棵Aesculus仍未替换。源面1,417.323700m²，地下暗渠不作为露天水体。`prepare_bridgehead_bank_context.py`已重新从缓存层提取并与既有上下文逐项一致，源文件指纹记录于`derived/bellevue/bridgehead_bank/context_provenance.json`，未增加网络请求。

地面读取已有SURVEY_TERRAIN；桥角的跨层错误另用023独立摄影桥面拟合约束，保留真实XY。树冠、胸径、每根枝条、树池、压顶、栏杆制造细部、隐蔽基础和材料磨损为推断。沿用已有CC0沥青、forest_ground_05土面、通用树皮和原创斑驳图集；没有新增现场扫描声明。此前已缓存并实际查看的建筑师历史河岸照片支持上下层、座椅与竖向栏杆关系，不能当作当前施工图。详细界限和重放顺序见`planning/BRIDGEHEAD_UPPER_BANK_CN.md`。

## 桥上照明与旗杆027r4（2026-09-25取得，26日施工）

[城市公共照明](https://www.stadt-zuerich.ch/geodaten/download/Oeffentliche_Beleuchtung_der_Stadt_Zuerich?format=10008)WFS图层ewz_brennstelle_p，本次EPSG:2056范围2683300,1246400,2684200,1247250取得1190条；13条在已有12根桥杆0.4米内。官方页列无使用限制、数据日期2026-09-13、每周更新。文件和带请求URL/SHA256收据在sources/features/bridge_fittings；点位只有XY与属性，未提供灯型或高度。37745待查，其余12套灯具外形/连接为源摄影约束下的推断，原始orientierung不擅自解释单位。

[市政府旗帜设置规定](https://www.stadt-zuerich.ch/content/dam/web/de/stadtleben/stadtportraet/dokumente/beflaggung_stadt_zuerich_ausfuehrungsbestimmungen_und_hinweise.pdf)约2016/2017年文件，印刷页9/2、PDF第31页，已实际查看图示。给出Quaibrücke每角3面、每面4×4米和相应挂旗场合；不提供精确旗杆坐标与高度。本次只复原源扫描中东南角挂旗外观，杆锚/细部/布料姿态标为推断。PDF及收据、页图在sources/references/bridge_fittings。不能把这一外观当作当前日期的实际挂旗日历。细节见planning/BRIDGE_FITTINGS_CN.md。
