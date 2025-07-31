这是一个用于媒体管理的实用工具集，包含两个 Python 脚本：

1. `tmdb_export.py`：用于导出 TMDB 元数据（支持剧集整合与多集导出）；
2. `compare_media.py`：用于比对目录中视频文件的差异。

---
# 📁 脚本一：tmdb_export.py

## 🧩 功能介绍

### 1️⃣ tmdb_export.py：TMDB 元数据导出工具

支持以下功能：

- 基于 TMDB API 获取剧集、电影的元数据；
- 支持多季合并为一个季（如第 1~3 季合并为“第 1 季”）；
- 每集单独导出为 JSON 文件；
- 文件命名规则明确，便于媒体库导入；
- 输出字段包含中文注释（zh-CN）；
- 可选择输出哪些季、哪些集。

#### ✅ 使用示例

```bash
python tmdb_export.py <tmdbid> <apikey> <output> [选项]
```

### 必需参数

| 参数     | 说明               | 示例           |
|----------|--------------------|----------------|
| tmdbid   | TMDB ID（数字）    | `4013`         |
| apikey   | TMDB API密钥       | `your_api_key` |
| output   | 输出目录路径       | `./output`     |

### 可选参数

| 选项              | 说明                                  | 默认值 | 示例                                 |
|-------------------|---------------------------------------|--------|--------------------------------------|
| `--type`          | 内容类型：`auto` / `movie` / `tv` / `collection` | auto   | `--type tv`                          |
| `--apiversion`    | API版本：`v3` / `v4`                   | v3     | `--apiversion v4`                    |
| `--combine-seasons` | 将所有季合并为一季（仅剧集有效）     | 关闭   | `--combine-seasons`                  |
| `--season-mapping` | 季号映射（格式：原季号=新季号）      | 无     | `--season-mapping "1=2"`             |

---

## 获取 API 密钥

1. 访问 [TMDB官网](https://www.themoviedb.org/)
2. 创建账户并登录
3. 进入 API 设置页面
4. 申请 API 密钥（v3 或 v4）

---


### 1. 自动检测类型导出

```bash
python tmdb_export.py 123456789 your_api_key ./output
```

### 2. 导出电影

```bash
python tmdb_export.py 123456789 your_api_key ./output --type movie
```

### 3. 导出剧集（保持原季结构）

```bash
python tmdb_export.py 123456789 your_api_key ./output --type tv
```

### 4. 导出剧集并合并所有季

```bash
python tmdb_export.py 3427 your_api_key ./output --type tv --combine-seasons
```

### 5. 导出剧集并重新映射季号

```bash
# 将第1季导出为第2季
python tmdb_export.py 4013 your_api_key ./output --type tv --season-mapping "1=2"

# 多季映射：第1季→第2季，第2季→第3季
python tmdb_export.py 12345 your_api_key ./output --type tv --season-mapping "1=2,2=3"
```

### 6. 合并所有季并重新映射季号

```bash
# 将所有季合并为第2季
python tmdb_export.py 3427 your_api_key ./output --type tv --combine-seasons --season-mapping "1=2"
```

### 7. 导出合集

```bash
python tmdb_export.py 123456789 your_api_key ./output --type collection
```

---

## 输出文件结构

### 电影类型

```
{output}/
  {tmdbid}/
    movie/
      all.json             # 电影元数据
```

### 剧集类型

```
{output}/
  {tmdbid}/
    series/
      series.json              # 剧集元数据
      season-1.json            # 季元数据
      season-1-episode-1.json  # 集元数据
      ...
```

### 合集类型

```
{output}/
  {tmdbid}/
    collection/
      all.json             # 合集元数据
```

---

## 高级功能说明

### 季合并（`--combine-seasons`）

- 将所有季合并为一季（命名为“全集”）
- 集文件按顺序重新编号

例如：三季剧集合并后，集文件如下：

```
season-1-episode-1.json （原S1E1）
season-1-episode-2.json （原S1E2）
...
season-1-episode-N.json （原S3最后一集）
```

---

### 季号映射（`--season-mapping`）

- 格式：原季号=新季号
- 支持多季映射：`1=2,2=3`
- 同时改变文件名和元数据中的季号引用

示例：

```bash
--season-mapping "1=2"
```

- 季文件：`season-2.json`
- 集文件：`season-2-episode-1.json` 等

---

### 组合使用

可以同时使用季合并与季号映射：

```bash
python tmdb_export.py 3427 your_api_key ./output --type tv --combine-seasons --season-mapping "1=2"
```

---

## 注意事项

### API调用限制

- TMDB API 有速率限制（约 40 请求 / 10 秒）
- 大型剧集导出可能耗时较长
- 已内置指数退避机制（间隔：1s, 2s, 4s...，最多5次重试）

### 数据完整性

- 单集失败不会中断整个导出过程
- 会输出详细错误日志

### 特殊季处理

- 第0季（特辑季）默认跳过
- 仅处理季号大于0的正季

### 语言支持

- 优先返回简体中文
- 中文缺失时自动回退英文
- 部分字段可能无翻译

### 文件覆盖

- 每次运行会覆盖已有同名文件
- 建议使用新的输出目录以避免冲突

---

## 输出 JSON 模板示例

### 🎬 电影 `all.json`
```json
{
  "id": 123456789,
  "imdb_id": "",
  "title": "test movie",
  "original_title": "",
  "overview": "test movie overview",
  "tagline": "",
  "release_date": "",
  "vote_average": 0.0,
  "production_countries": [],
  "production_companies": [],
  "genres": [],
  "casts": {
    "cast": [],
    "crew": []
  },
  "releases": {
    "countries": []
  },
  "belongs_to_collection": null,
  "trailers": {
    "youtube": []
  }
}
```

### 📺 节目 `series.json`
```json
{
  "id": 123456789,
  "name": "test series",
  "original_name": "",
  "overview": "test series overview",
  "vote_average": 0.0,
  "episode_run_time": [],
  "first_air_date": "1970-01-01T00:00:00.000Z",
  "last_air_date": "1970-01-01T00:00:00.000Z",
  "status": "",
  "networks": [],
  "genres": [],
  "external_ids": {
    "imdb_id": "",
    "tvrage_id": null,
    "tvdb_id": null
  },
  "videos": {
    "results": []
  },
  "content_ratings": {
    "results": []
  },
  "credits": {
    "cast": []
  }
}
```

### 📦 季 `season-1.json`
```json
{
  "name": "test season 1",
  "overview": "test season 1 overview",
  "air_date": "1970-01-01T00:00:00.000Z",
  "external_ids": {
    "tvdb_id": null
  },
  "credits": {
    "cast": [],
    "crew": []
  }
}
```

### 🎞️ 集 `season-1-episode-1.json`
```json
{
  "name": "test episode 1",
  "overview": "test episode 1 overview",
  "videos": {
    "results": []
  },
  "external_ids": {
    "tvdb_id": null,
    "tvrage_id": null,
    "imdb_id": ""
  },
  "air_date": "1970-01-01T00:00:00.000Z",
  "vote_average": 0.0,
  "credits": {
    "cast": [],
    "guest_stars": [],
    "crew": []
  }
}
```

### 📚 合集 `all.json`
```json
{
  "id": 123456789,
  "name": "test collection",
  "overview": ""
}
```
# 📁 脚本二：compare_media.py

一个用于支持比对两个目录中的视频文件差异的命令行工具。

## 🧰 功能介绍

- 支持两种比较模式：
  - 📺 **剧集模式**（支持识别 SxxExx 格式的集数信息）
  - 🎬 **电影模式**（根据目录结构进行比对）
- 自动提取视频文件的分辨率（如 1080p、2160p）
- 支持以下视频格式：`.mkv`、`.mp4`、`.avi`、`.mov`、`.flv`、`.wmv`
- 生成对比差异报告（包括缺失、大小不同、分辨率差异等）
- 友好的终端进度指示（带旋转图标）
- 输出日志保存为 `.log` 文件，可选目录

## 📂 使用示例

1. 运行脚本：

```bash
python media_compare.py
```

2. 选择模式：

```
请输入选择 (1/2):
  1. 剧集模式 (TV Shows)
  2. 电影模式 (Movies)
```

3. 输入比较路径：

```
整理包路径: /path/to/source_folder
媒体库包路径: /path/to/library_folder
日志输出目录 (留空为当前目录): /path/to/output
```

4. 脚本将自动扫描文件结构，提取分辨率与大小，生成 `.log` 日志报告。

---

## 📋 输出示例

电影模式下：

```
[电影] MovieA（整理包有，媒体库包无）
  整理包文件列表:
    ├─ MovieA.1080p.mp4 (1080P, 2.36GB)
```

剧集模式下：

```
[目录] Season 1（整理包有，媒体库包有）
  ├─ [集] S01E01（大小不同）
  │   ├─ 整理包: E01.1080p.mkv (2.1GB)
  │   └─ 媒体库包: E01.1080p.mkv (1.9GB)
```

---

## 🛠 支持的格式

- 视频扩展名：`.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`, `.wmv`
- 分辨率识别：支持如 `720p`, `1080p`, `2160p` 等
- 剧集识别格式：如 `S01E02`, `s02e03` 等

---

## 🧩 依赖环境

标准 Python 3 环境，无额外第三方依赖。

---

## 📄 日志文件命名规则

日志文件默认命名为：

```
YYYYMMDD_HHMMSS_电影比较报告.log
或
YYYYMMDD_HHMMSS_剧集比较报告.log
```

---
