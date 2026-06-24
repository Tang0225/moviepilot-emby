# MoviePilot Emby Series Badge

一个面向 MoviePilot V2 的 Emby 状态角标插件项目。

它会自动连接已配置的 Emby，读取电视剧媒体库，判断每个剧集当前是“完结”还是“追更”，然后把状态写回 Emby。
你可以选择两种展示方式：

1. 写入标签：给剧集打上 `完结` / `追更` 标签。
2. 覆盖海报：直接把“完结”或“追更”绘制到海报右上角。

## 功能特性

1. 自动复用 MoviePilot 中现有的 Emby 配置。
2. 自动扫描 Emby 电视剧媒体库。
3. 支持状态判定：完结 / 追更。
4. 支持写入 Emby 标签。
5. 支持覆盖海报角标。
6. 支持手动命令触发。
7. 支持 API 触发。
8. 支持定时扫描。
9. 支持“已有标签时跳过”和“强制重建角标”。

## 适用场景

1. 想在 Emby 中快速区分已经完结和仍在更新的剧。
2. 想让家人或共享用户一眼看出这部剧是否还在追更。
3. 想结合 MoviePilot 自动化周期性维护剧集状态。

## 目录结构

```text
moviepilot-emby-series-badge/
├── CHANGELOG.md
├── LICENSE
├── README.md
├── RELEASE.md
├── package.v2.json
├── plugin/
├── dist/
├── release/
├── scripts/
└── standalone/
```

## 标准发布包

可直接分发的标准 MoviePilot V2 发布包会生成在：

1. `release/moviepilot-v2-seriesstatusbadge/`
2. `release/moviepilot-v2-seriesstatusbadge.zip`

发布包结构如下：

```text
moviepilot-v2-seriesstatusbadge/
├── INSTALL.md
├── package.v2.json
└── plugins.v2/
    └── seriesstatusbadge/
        ├── __init__.py
        ├── README.md
        └── requirements.txt
```

## 安装方式

### 方式 1：接入你自己的 MoviePilot 插件仓库

1. 将 `plugins.v2/seriesstatusbadge` 放入你的插件仓库。
2. 将 `package.v2.json` 中 `SeriesStatusBadge` 条目合并到总索引。
3. 重载或重启 MoviePilot。
4. 在插件管理中启用“媒体库完结/追更角标”。

### 方式 2：直接使用发布包

1. 解压 `moviepilot-v2-seriesstatusbadge.zip`。
2. 把其中 `plugins.v2/seriesstatusbadge` 放进插件仓库。
3. 合并 `package.v2.json`。
4. 重启或重载 MoviePilot。

## 配置说明

1. `启用插件`：开启后才会真正执行扫描。
2. `写入标签`：写入 `完结` / `追更` 标签。
3. `覆盖海报角标`：直接改写海报图显示文字角标。
4. `完结标签`：默认 `完结`。
5. `追更标签`：默认 `追更`。
6. `已有状态标签时跳过`：避免重复改写已有结果。
7. `每次重建海报角标`：适合改了样式后重新刷图。
8. `定时 CRON`：周期性自动扫描。

## 判定规则

当前版本主要基于 Emby 中已有元数据进行判断：

1. `Status = Ended / Cancelled` 判定为完结。
2. `Status = Continuing / Returning Series / Planned / Pilot / In Production` 判定为追更。
3. 存在 `EndDate` 判定为完结。
4. `AirsDays` 为空且已有剧集数据，倾向判定为完结。
5. 其他情况默认判定为追更。

## 重要说明

Emby 原生通常不能只靠一个自定义字段就在封面角落显示文字角标。
所以如果你要的是“封面上直接显示完结 / 追更”，本项目采用的是“覆盖海报图再回传 Emby”的方式。

这意味着：

1. 标签模式最稳妥。
2. 海报模式视觉效果最好。
3. 海报模式会修改 Primary 海报。

## 手动触发与接口

1. 命令：`/series_status_badge_run`
2. API：`POST /api/v1/plugin/SeriesStatusBadge/run`
3. 摘要：`GET /api/v1/plugin/SeriesStatusBadge/summary`

## 本地打包

在项目根目录执行：

```powershell
python moviepilot-emby-series-badge\scripts\build_release.py
```

生成结果：

1. `dist/`：同步后的分发目录。
2. `release/moviepilot-v2-seriesstatusbadge/`：标准发布包目录。
3. `release/moviepilot-v2-seriesstatusbadge.zip`：标准发布包压缩包。

## 后续可扩展方向

1. 接入 TMDB 二次校验，提高“完结 / 追更”准确率。
2. 增加仅处理指定媒体库、路径、标签的规则。
3. 增加更丰富的角标样式，比如斜角贴纸、圆角胶囊、颜色主题。
4. 增加电影、动漫等其他媒体类型支持。

## License

MIT
