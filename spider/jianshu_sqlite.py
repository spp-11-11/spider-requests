# -*- coding: utf-8 -*-
"""简书热门文章 → SQLite

原版问题：只有数据库类，没有爬取逻辑；insert 写的是 kugou 表；还导入了 turtledemo
（这行会启动海龟演示程序，把脚本卡死）。这里整体重写。

数据来源用简书自己的 JSON 接口 /asimov/trending/now，比解析 HTML 稳定得多。
"""
import json
import os
import sqlite3
import sys
import time

import requests

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "sqlite", "jianshu.db")

API = "https://www.jianshu.com/asimov/trending/now"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
    "Accept": "application/json",
}
TIMEOUT = 15
PAGES = 5
PER_PAGE = 20
PAGE_SLEEP = 1


class JianshuDB:
    """简书文章的 SQLite 封装"""

    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id       INTEGER PRIMARY KEY,
                title    VARCHAR(200),
                author   VARCHAR(50),
                likes    INTEGER,
                comments INTEGER,
                summary  TEXT,
                url      VARCHAR(100)
            )
        """)
        self.conn.commit()

    def insert(self, item):
        """item = (id, title, author, likes, comments, summary, url)"""
        try:
            self.cur.execute(
                "INSERT OR REPLACE INTO articles VALUES(?,?,?,?,?,?,?)", item)
        except sqlite3.Error as e:
            print("  写入失败：%s" % e)

    def count(self):
        self.cur.execute("SELECT COUNT(*) FROM articles")
        return self.cur.fetchone()[0]

    def close(self):
        self.conn.commit()
        self.cur.close()
        self.conn.close()


def parse(items_json):
    """把接口返回的 JSON 转成入库元组列表"""
    rows = []
    for wrap in items_json:
        if not isinstance(wrap, dict):
            continue
        data = wrap.get("object", {}).get("data") or wrap.get("data") or {}
        if not data:
            continue
        slug = data.get("slug") or ""
        rows.append((
            data.get("id"),
            (data.get("title") or "").strip(),
            (data.get("user") or {}).get("nickname", ""),
            data.get("likes_count") or 0,
            data.get("public_comments_count") or 0,
            (data.get("public_abbr") or "").strip(),
            ("https://www.jianshu.com/p/%s" % slug) if slug else "",
        ))
    return rows


def main():
    db = JianshuDB()
    total = 0

    for page in range(1, PAGES + 1):
        url = "%s?page=%d&count=%d" % (API, page, PER_PAGE)
        print("=" * 60)
        print("第 %d 页：%s" % (page, url))
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            res.encoding = "utf-8"
            if res.status_code != 200:
                print("  状态码异常：%s" % res.status_code)
                continue
            items = parse(res.json())
            if not items:
                print("  未解析到数据")
            for it in items:
                print("  %s | 作者: %s | 赞 %s | 评 %s"
                      % (it[1][:30], it[2], it[3], it[4]))
                db.insert(it)
            total += len(items)
            print("  本页 %d 条，累计 %d 条" % (len(items), total))
        except requests.RequestException as e:
            print("  请求失败：%s %s" % (type(e).__name__, str(e)[:120]))
        except ValueError as e:
            print("  JSON 解析失败：%s" % str(e)[:120])
        except Exception as e:
            print("  异常：%s %s" % (type(e).__name__, str(e)[:120]))
        time.sleep(PAGE_SLEEP)

    print("\n完成：共采集 %d 篇，数据库当前 %d 行" % (total, db.count()))
    db.close()
    print("数据库：%s" % os.path.abspath(DB_PATH))


if __name__ == "__main__":
    main()
