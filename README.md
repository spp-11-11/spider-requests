# 多源网页数据采集

基于 **requests + BeautifulSoup + 正则 / XPath** 的四个实战爬虫，覆盖 HTML 正则解析、DOM 选择器、官方 JSON 接口三条技术路线，数据分别落 CSV 与 SQLite。

已完成实测：豆瓣 250 本、酷狗 500 首、天气 7 天、简书 63 篇，全部成功入库。

## 项目概览

| 脚本 | 目标站点 | 抓取方式 | 输出 |
|---|---|---|---|
| `spider/douban_book_top250_re.py` | 豆瓣读书 Top250 | requests + 正则 | CSV，250 本 |
| `spider/kugou_music.py` | 酷狗音乐排行榜 | requests + BeautifulSoup | CSV，500 首 |
| `spider/kugou_music_top500_sqlite.py` | 酷狗音乐排行榜 | 同上 | SQLite，500 行 |
| `spider/weather_sz_re.py` | 深圳 7 天天气 | requests + 正则 | 控制台表格 |
| `spider/weather_sz_sqlite.py` | 深圳 7 天天气 | requests + lxml XPath | SQLite，7 行 |
| `spider/jianshu_sqlite.py` | 简书热门文章 | requests + 官方 JSON 接口 | SQLite，63 篇 |

## 技术栈

- **HTTP**：requests（统一设置 UA / Referer，`timeout=15`）
- **HTML 解析**：BeautifulSoup + lxml（CSS 选择器）、正则、lxml XPath
- **结构化接口**：简书 `/asimov/trending/now` 返回 JSON，直接 `res.json()`
- **存储**：CSV（`utf-8-sig` 防 Excel 乱码）、SQLite

## 目录结构

```
spider-requests/
├─ spider/                       # 爬虫脚本
│   ├─ douban_book_top250_re.py
│   ├─ kugou_music.py
│   ├─ kugou_music_top500_sqlite.py
│   ├─ weather_sz_re.py
│   ├─ weather_sz_sqlite.py
│   ├─ jianshu_sqlite.py
│   ├─ douban_book_top250.csv    # 运行产物
│   └─ kugou_music.csv
├─ sqlite/                       # 数据库与 sqlite3 命令行工具
│   ├─ music.db                  # kugou 表，500 行
│   ├─ weather.db                # tt 表
│   └─ jianshu.db                # articles 表
└─ requirements.txt
```

## 运行方式

1. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

2. 运行任意脚本（输出路径按脚本所在目录自动定位）

   ```bash
   python spider/douban_book_top250_re.py
   python spider/kugou_music_top500_sqlite.py
   python spider/weather_sz_sqlite.py
   python spider/jianshu_sqlite.py
   ```

3. 查看数据库

   ```bash
   python -c "import sqlite3; c=sqlite3.connect('sqlite/music.db'); print(c.execute('select count(*) from kugou').fetchone())"
   ```

## 数据库表结构

```sql
-- 酷狗榜单
CREATE TABLE kugou (
    num      VARCHAR(10),   -- 排名
    song     VARCHAR(50),   -- 歌曲
    singer   VARCHAR(50),   -- 歌手
    duration VARCHAR(20)    -- 时长
);

-- 深圳天气
CREATE TABLE tt (
    date  varchar(20),      -- 日期，如「8日（今天）」
    tq    varchar(30),      -- 天气
    temp  varchar(30),      -- 温度，如「23℃/16℃」
    wind  varchar(30)       -- 风力
);

-- 简书文章
CREATE TABLE articles (
    id       INTEGER PRIMARY KEY,
    title    VARCHAR(200),
    author   VARCHAR(50),
    likes    INTEGER,
    comments INTEGER,
    summary  TEXT,
    url      VARCHAR(100)
);
```

## 设计要点

**反爬应对**
- 统一携带 `User-Agent`，豆瓣额外带 `Referer`
- 分页之间 `time.sleep()` 限速（豆瓣 2 秒 / 酷狗、简书 1 秒）

**健壮性**
- 所有请求加 `timeout=15`，网络异常不会无限挂起
- 单页 `try/except`，某一页失败不影响其余页面
- 解析层做空值保护：正则用 `safe_search` 兜底，XPath 取不到返回空串，缺字段的条目跳过而非抛 `IndexError`

**数据落库**
- 每个脚本自带 `CREATE TABLE IF NOT EXISTS`，换机器不用手工建表
- 酷狗整轮先清空再写入，避免重复运行产生重复行
- 天气按日期先删后插，同一天多次运行只保留最新
- 简书用 `INSERT OR REPLACE` + 主键去重

## 注意事项

- 抓取频率已控制在秒级，请勿进一步缩短间隔
- 数据仅用于学习交流，请遵守各站点的 robots.txt 与服务条款
- 站点结构变化时需同步调整选择器 / 正则，脚本已尽量把解析逻辑独立成函数便于修改
